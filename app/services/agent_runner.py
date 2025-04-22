import sys
import asyncio
import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.state import add_log, browser_ctx, running
from app.crud import start_task, finish_task
from app.core.config import get_settings
from app.services.utils import get_llm, get_browser_instance
from browser_use import Agent

logger = logging.getLogger("agent_runner")
logger.setLevel(logging.INFO)

# Windows üzerinde ProactorEventLoop kullanımı
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def run_agent(task_id: int, task_text: str):
    """
    1) Task kaydını başlatır ve log’u açar.
    2) Chain‑of‑thought + text‑based click talimatı içeren prompt’u hazırlar.
    3) ResilientBrowser ile Agent’i çalıştırır.
    4) Zaman aşımı koruması ve hata yönetimi sağlar.
    5) Sonucu DB’ye kaydeder.
    """
    settings = get_settings()
    db: Session = SessionLocal()

    def log(msg: str):
        full = f"[Task {task_id}] {msg}"
        add_log(full)
        logger.info(full)

    # Prompt şablonu
    system_prompt = """
You are an autonomous web-automation agent. Always think step by step, and before each action, explain your reasoning.
When you need to click an element, just specify its visible text (e.g., "Submit", "Next Page").
The ResilientBrowser will:
  1. Convert this text into a text= locator.
  2. Wait up to 5 seconds for it to appear.
  3. Scroll it into view.
  4. Click it.
If after three retries it's still not found, report failure.
At the end, generate a JSON summary of your actions and any fallback steps.
""".strip()

    full_task = f"{system_prompt}\n\nTask: {task_text}"
    timeout = getattr(settings, "agent_timeout", None) or 300

    try:
        # Başlatma
        start_task(db, task_id)
        running["state"] = True
        log("status → running")

        # LLM ve browser örneğini al
        llm = get_llm()
        browser = get_browser_instance()
        browser_ctx["browser"] = browser
        log("ResilientBrowser initialized")

        # Agent konfigürasyonu
        agent = Agent(
            task=full_task,
            llm=llm,
            browser=browser,
            max_actions_per_step=settings.agent_max_actions,
        )

        # Çalıştırma (zaman aşımı)
        log(f"Running agent (timeout={timeout}s)")
        await asyncio.wait_for(
            agent.run(max_steps=settings.agent_max_steps),
            timeout=timeout
        )

        # Başarı
        finish_task(db, task_id, True)
        log("status → done")

    except asyncio.TimeoutError:
        finish_task(db, task_id, False)
        log(f"status → failed (timeout after {timeout}s)")

    except Exception as e:
        finish_task(db, task_id, False)
        log(f"status → failed ({e})")

    finally:
        # Kaynak temizliği
        db.close()
        running["state"] = False
        log("DB session closed; agent state reset")
