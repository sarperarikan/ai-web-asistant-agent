# app/crud.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import Optional, List

from app import models, schemas
from app.models import TaskStatus as ModelTaskStatus


# ---------- KULLANICI CRUD ----------

def create_user(db: Session, user: schemas.UserCreate) -> Optional[models.User]:
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=user.password,
        role=user.role,
        created_at=datetime.utcnow()
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        return None


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


# ---------- GÖREV CRUD ----------

def create_task(db: Session, task: schemas.TaskCreate, user_id: int) -> models.Task:
    """
    Yeni görevi 'pending' olarak oluşturur.
    """
    db_task = models.Task(
        title=task.title,
        status=ModelTaskStatus.pending,
        created_at=datetime.utcnow(),
        user_id=user_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_tasks_by_user(db: Session, user_id: int) -> List[models.Task]:
    return db.query(models.Task).filter(models.Task.user_id == user_id).all()


def get_task_by_id(db: Session, task_id: int) -> Optional[models.Task]:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


# ---------- LOG CRUD ----------

def add_task_log(db: Session, task_id: int, log: schemas.TaskLogCreate) -> models.TaskLog:
    db_log = models.TaskLog(
        task_id=task_id,
        log_type=log.log_type,
        message=log.message,
        timestamp=datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_logs_by_task(db: Session, task_id: int) -> List[models.TaskLog]:
    return db.query(models.TaskLog).filter(models.TaskLog.task_id == task_id).all()


# ---------- GÖREV SİLME ----------

def delete_task(db: Session, task_id: int, user_id: int) -> bool:
    """
    Sadece sahibi olan kullanıcı kendi görevini silebilsin.
    """
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == user_id
    ).first()
    if not task:
        return False

    db.delete(task)
    db.commit()
    return True


# ---------- GÖREV DURUMU GÜNCELLEME ----------

def update_task_status(
    db: Session,
    task_id: int,
    new_status: ModelTaskStatus
) -> Optional[models.Task]:
    """
    Verilen task_id'li görevin status'unu new_status ile günceller.
    """
    task = get_task_by_id(db, task_id)
    if not task:
        return None

    task.status = new_status
    db.commit()
    db.refresh(task)
    return task


def start_task(db: Session, task_id: int) -> Optional[models.Task]:
    """
    Görevin status'unu 'running' olarak işaretler.
    """
    return update_task_status(db, task_id, ModelTaskStatus.running)


def finish_task(db: Session, task_id: int, success: bool) -> Optional[models.Task]:
    """
    Agent tamamlandığında görevin status'unu 'done' veya 'failed' olarak ayarlar.
    """
    final_status = ModelTaskStatus.done if success else ModelTaskStatus.failed
    return update_task_status(db, task_id, final_status)
