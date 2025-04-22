# app/state.py

from datetime import datetime
from typing import Any, Dict, List

# — Global log listesi —
task_log: List[str] = []

# — Agent’in çalışıp çalışmadığını izleyen flag —
running: Dict[str, bool] = {"state": False}

# — Tarayıcı context ve browser nesnesini saklamak için —
#   'ctx' içine BrowserContext, 'browser' içine Browser objesi gelecek
browser_ctx: Dict[str, Any] = {"ctx": None, "browser": None}


def add_log(message: str) -> None:
    """
    Gelen mesajı timestamp ile birlikte task_log'a ekler
    ve konsola basar.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {message}"
    task_log.append(entry)
    print(entry)
