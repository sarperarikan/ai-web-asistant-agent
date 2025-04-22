# app/routes/api.py

import threading
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal
from app import crud, schemas
from app.state import running, task_log
from app.services.agent_runner import run_agent
from app.core.auth import decode_access_token
from fastapi import Header

router = APIRouter(prefix="/api")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ——— DB SESSION DEPENDENCY ———
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ——— USER AUTH DEPENDENCY ———
def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya eksik token",
        )
    return payload["sub"]


# ——— RUN TASK ———
@router.post(
    "/run_task",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict
)
def run_task_api(
    task_text: str,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    if running["state"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zaten çalışan bir görev var."
        )

    # Kullanıcıyı al
    user = crud.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )

    # DB'ye yeni görev kaydet
    task = crud.create_task(db, schemas.TaskCreate(title=task_text), user.id)

    # Ajanı arka planda başlat
    running["state"] = True
    thread = threading.Thread(
        target=lambda: asyncio.run(run_agent(task_text))
    )
    thread.start()

    return {"message": "Görev başladı.", "task_id": task.id}


# ——— STOP TASK ———
@router.post(
    "/stop_task",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
def stop_task_api(
    token: str = Depends(oauth2_scheme)
):
    if not running["state"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Çalışan bir görev yok."
        )

    # Durumu değiştir; agent_runner sonunda da False olacak
    running["state"] = False
    return {"message": "Görev durduruldu."}


# ——— LIST TASKS ———
@router.get(
    "/tasks",
    response_model=List[schemas.TaskResponse]
)
def list_tasks_api(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    user = crud.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )
    return crud.get_tasks_by_user(db, user.id)


# ——— GET LOGS ———
@router.get(
    "/logs",
    response_model=List[str]
)
def get_logs_api(
    token: str = Depends(oauth2_scheme)
):
    # Sadece kimlikli kullanıcı erişsin
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token."
        )
    return task_log


# ——— CLEAR HISTORY ———
@router.post(
    "/clear_history",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
def clear_history_api(
    token: str = Depends(oauth2_scheme)
):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token."
        )
    task_log.clear()
    return {"message": "Log geçmişi temizlendi."}
