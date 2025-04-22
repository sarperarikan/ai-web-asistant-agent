# app/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum as SAEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum

from app.database import Base  # Tek Base kaynağımız buradan geliyor


# ---------- ENUM Tanımları ----------
class UserRole(PyEnum):
    admin = "admin"
    user = "user"
    editor = "editor"


class TaskStatus(PyEnum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


# ---------- USER Modeli ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete")

    def __repr__(self):
        return f"<User(username={self.username!r}, role={self.role.value!r})>"


# ---------- TASK Modeli ----------
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tasks")

    logs = relationship("TaskLog", back_populates="task", cascade="all, delete")

    def __repr__(self):
        return f"<Task(title={self.title!r}, status={self.status.value!r})>"


# ---------- TASK LOG Modeli ----------
class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    log_type = Column(String(20), default="info", nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="logs")

    def __repr__(self):
        return f"<TaskLog(task_id={self.task_id!r}, type={self.log_type!r})>"
