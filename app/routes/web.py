import sys
import asyncio
from datetime import datetime
# Windows’ta subprocess desteği için ProactorEventLoop politikası
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import threading
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.routes.user_routes import get_db, get_current_user
from app.services.agent_runner import run_agent
from app import crud, schemas
from app.state import task_log, add_log

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow

@router.get("/tasks")
async def tasks_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    tasks = crud.get_tasks_by_user(db, user.id)
    logs = task_log.copy()
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "user": user, "tasks": tasks, "logs": logs},
    )


@router.post("/run_task")
async def run_task(
    request: Request,
    db: Session = Depends(get_db),
):
    """Hem HTML form hem JSON API ile yeni görev başlatır."""
    user = get_current_user(request, db)
    if not user:
        if request.headers.get("accept", "").startswith("application/json"):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        return RedirectResponse("/login", status_code=303)

    # task_text al
    ct = request.headers.get("content-type", "")
    if ct.startswith("application/json"):
        payload = await request.json()
        task_text = payload.get("task_text", "").strip()
    else:
        form = await request.form()
        task_text = form.get("task_text", "").strip()

    if not task_text:
        if ct.startswith("application/json"):
            raise HTTPException(status_code=400, detail="task_text is required")
        return RedirectResponse("/tasks", status_code=303)

    # DB kaydı oluştur ve görevi başlat
    task = crud.create_task(db, schemas.TaskCreate(title=task_text), user.id)
    add_log(f"Görev oluşturuldu: {task_text} (ID: {task.id})")

    # Thread içinde async agent'i çalıştır
    threading.Thread(
        target=lambda: asyncio.run(run_agent(task.id, task_text)),
        daemon=True
    ).start()

    if ct.startswith("application/json"):
        return {"message": "Task started", "task_id": task.id}
    return RedirectResponse("/tasks", status_code=303)


@router.post("/delete_task")
async def delete_task_web(
    request: Request,
    task_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    success = crud.delete_task(db, task_id, user.id)
    if not success:
        add_log(f"Silme hatası: Yetkisiz veya bulunamadı (task_id={task_id})")
    else:
        add_log(f"Görev silindi (task_id={task_id})")

    return RedirectResponse("/tasks", status_code=303)


@router.post("/rerun_task")
async def rerun_task(
    request: Request,
    task_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    task = crud.get_task_by_id(db, task_id)
    if not task or task.user_id != user.id:
        add_log(f"Yeniden başlatma hatası: Yetkisiz veya bulunamadı (task_id={task_id})")
        return RedirectResponse("/tasks", status_code=303)

    threading.Thread(
        target=lambda: asyncio.run(run_agent(task.id, task.title)),
        daemon=True
    ).start()

    add_log(f"Görev yeniden başlatıldı: {task.title} (ID: {task.id})")
    return RedirectResponse("/tasks", status_code=303)


@router.post("/clear_history")
async def clear_history(request: Request):
    task_log.clear()
    add_log("Log geçmişi temizlendi.")
    if request.headers.get("accept", "").startswith("application/json"):
        return {"message": "History cleared"}
    return RedirectResponse("/tasks", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response
