from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional

from app.core.config import get_settings
from app.schemas import UserRole

# Ayarları al
settings = get_settings()

# Şifreleme algoritması (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT ayarları
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# ---------- PAROLA İŞLEMLERİ ----------

def hash_password(password: str) -> str:
    """Parolayı bcrypt ile hash'ler."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolanın doğruluğunu kontrol eder."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------- JWT TOKEN ÜRETİMİ ----------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Erişim token'ı üretir."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------- TOKEN DOĞRULAMA ----------

def decode_access_token(token: str) -> Optional[dict]:
    """Token'ı çözümleyip payload'ı döner. Geçersizse None döner."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
