# app/routes/user_routes.py

from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import EmailStr
from typing import Generator, Optional
from app.database import SessionLocal
from app import crud, schemas
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ——— DB SESSION DEPENDENCY ———
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ——— WEB (TEMPLATE) ROUTES ———

@router.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # e‑posta kontrolü
    if crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Bu e‑posta zaten kayıtlı."}
        )

    # kullanıcıyı oluştur
    hashed_pw = hash_password(password)
    user_in = schemas.UserCreate(username=username, email=email, password=hashed_pw)
    user = crud.create_user(db, user_in)
    if not user:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Kayıt sırasında hata oluştu."}
        )

    # kayıt başarılı → login sayfasına yönlendir
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Geçersiz kullanıcı adı veya şifre."}
        )

    token = create_access_token({"sub": user.email})
    response = RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)
    # Token'ı çerezde saklıyoruz (HTTP‑only)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response


def get_current_user(request: Request, db: Session) -> Optional[schemas.UserResponse]:
    """
    Çerezdeki access_token'ı alıp decode eder.
    """
    raw = request.cookies.get("access_token")
    if not raw or not raw.startswith("Bearer "):
        return None
    token = raw.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    return crud.get_user_by_email(db, email)


@router.get("/profile")
async def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    # profile.html içinde user bilgilerini gösterebilirsin
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": user}
    )


# ——— JSON API ROUTES ———

@router.post("/api/register", response_model=schemas.UserResponse)
def api_register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email):
        raise JSONResponse(status_code=400, content={"detail": "Email already in use"})
    user.password = hash_password(user.password)
    created = crud.create_user(db, user)
    if not created:
        raise JSONResponse(status_code=500, content={"detail": "User creation failed"})
    return created


@router.post("/api/login")
def api_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise JSONResponse(status_code=401, content={"detail": "Invalid credentials"})
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/api/me", response_model=schemas.UserResponse)
def api_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload:
        raise JSONResponse(status_code=401, content={"detail": "Invalid token"})
    email = payload.get("sub")
    user = crud.get_user_by_email(db, email)
    if not user:
        raise JSONResponse(status_code=404, content={"detail": "User not found"})
    return user
