# main.py

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# --- Buraya ekle ---
from app.services.utils import launch_global_browser, shutdown_global_browser

# Ayarları çek
from app.core.config import get_settings

# Veritabanı altyapısı
from app.database import Base, engine
import app.models  # modellerin metadata’sını Base’e kaydetmek için

# Router’lar
from app.routes.user_routes import router as user_router
from app.routes.api import router as api_router
from app.routes.web import router as web_router

# İlk çalıştırmada tabloları oluştur
Base.metadata.create_all(bind=engine)

# FastAPI uygulaması
app = FastAPI(title="Agentic FastAPI App")

# --- Startup / Shutdown eventleri burada ---
@app.on_event("startup")
async def on_startup():
    # Uygulama ayağa kalkarken sadece bir kez Chromium'u başlat
    await launch_global_browser(headless=False)

@app.on_event("shutdown")
async def on_shutdown():
    # Uygulama kapanırken browser'ı kapat
    await shutdown_global_browser()

# Statik dosyalar (CSS, JS, vb.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Router’ları dahil et
app.include_router(user_router)
app.include_router(api_router)
app.include_router(web_router)

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
