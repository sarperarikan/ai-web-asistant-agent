from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    editor = "editor"


class TaskStatus (str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class UserBase(BaseModel):
    username : str
    email : EmailStr
    role : UserRole = UserRole.user


class UserCreate(UserBase):
    password : str


class UserResponse(UserBase):
    id : int
    created_at : datetime
    class Config:
        orm_mode = True


class TaskBase(BaseModel):
    title : str
    status : TaskStatus = TaskStatus.pending


class TaskCreate (TaskBase):
    pass


class TaskResponse(TaskBase):
    id : int
    created_at : datetime
    user_id : int

    class Config:
        orm_mode = True


class TaskLogBase(BaseModel):
    log_type : str
    message : str


class TaskLogCreate(TaskLogBase):
    pass

class TaskLogResponse(TaskLogBase):
    id : int
    task_id : int
    timestamp : datetime

    class Config:
        orm_mode = True


     

  



