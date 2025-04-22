# app/services/utils.py

import asyncio
from typing import Tuple, Any
from pydantic import SecretStr
from langchain_google_genai import ChatGoogleGenerativeAI

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContext
from app.core.config import get_settings

settings = get_settings()


class ResilientBrowser(Browser):
    """
    - click_element: metin bazlı fallback, wait_for_selector, scrollIntoView, sonra click.
    - close(): _keep_open True olduğu sürece kapanmayı bekletir.
    """

    def __init__(self, config: BrowserConfig):
        super().__init__(config=config)
        # Tarayıcıyı varsayılan olarak açık tut
        self._keep_open = True

    async def click_element(self, selector: str, **kwargs):
        # Metin bazlı locator fallback
        if not selector.strip().startswith(('.', '#', '<', '/')):
            text_selector = f'text="{selector}"'
        else:
            text_selector = selector

        # 1) Görünene kadar bekle
        try:
            await self.page.wait_for_selector(text_selector, timeout=5000)
        except Exception:
            pass

        # 2) ScrollIntoView
        try:
            await self.page.evaluate(
                "(sel) => document.querySelector(sel)?.scrollIntoView()", text_selector
            )
        except Exception:
            pass

        # 3) Asıl click
        return await super().click_element(text_selector, **kwargs)

    async def close(self):
        """
        Tarayıcıyı, _keep_open False olana dek kapatmaz.
        """
        while self._keep_open:
            await asyncio.sleep(1)
        await super().close()

    def allow_close(self):
        """
        close()’un kapanmasına izin verir.
        """
        self._keep_open = False


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Google Gemini LLM örneğini oluşturur.
    """
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=SecretStr(settings.gemini_api_key),
        temperature=settings.gemini_temperature,
        max_tokens=settings.gemini_max_tokens,
        top_p=settings.gemini_top_p,
    )


def get_browser_instance() -> ResilientBrowser:
    """
    Mevcut kodun geriye dönük uyumluluğu için: 
    Yeni bir ResilientBrowser örneği oluşturur.
    """
    config = BrowserConfig(
        headless=False,
        new_context_config=BrowserContextConfig(viewport_expansion=0)
    )
    return ResilientBrowser(config=config)


# --- Aşağıdaki fonksiyonları dosyanın en altına ekleyin ---

# Global browser örneği (uygulama seviyesinde bir kez açılacak)
GLOBAL_BROWSER: Browser | None = None

async def launch_global_browser(headless: bool = False) -> Browser:
    """
    FastAPI startup event'ında bir kez çağrılarak GLOBAL_BROWSER'ı başlatır.
    """
    global GLOBAL_BROWSER
    if GLOBAL_BROWSER is None:
        config = BrowserConfig(
            headless=headless,
            new_context_config=BrowserContextConfig(viewport_expansion=0)
        )
        GLOBAL_BROWSER = Browser(config=config)
        # Eğer BrowserUse API'sinde ayrı bir launch() gerekiyorsa:
        # await GLOBAL_BROWSER.launch()
    return GLOBAL_BROWSER

async def shutdown_global_browser() -> None:
    """
    FastAPI shutdown event'ında GLOBAL_BROWSER'ı kapatır.
    """
    global GLOBAL_BROWSER
    if GLOBAL_BROWSER is not None:
        await GLOBAL_BROWSER.close()
        GLOBAL_BROWSER = None

async def get_browser_context() -> Tuple[BrowserContext, Any]:
    """
    GLOBAL_BROWSER'dan yeni bir context ve page oluşturur.
    Burada context.close() metodu override edilerek otomatik kapanma engellenir.
    Kullanım:
        ctx, page = await get_browser_context()
    """
    if GLOBAL_BROWSER is None:
        raise RuntimeError("GLOBAL_BROWSER başlatılmamış. Önce launch_global_browser çağrılmalı.")
    context: BrowserContext = await GLOBAL_BROWSER.new_context()
    page = await context.new_page()

    # context.close'u no-op ile override ederek pencerenin kapanmasını engelle
    async def _no_op_close(*args, **kwargs):
        return  # hiç kapanma

    context.close = _no_op_close  # override!

    return context, page
