import os
from dotenv import load_dotenv
from datetime import timedelta

from authx import AuthX, AuthXConfig
from fastapi.security import HTTPBearer
from passlib.context import CryptContext

load_dotenv()

config = AuthXConfig(
    JWT_ALGORITHM="HS256",
    JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY_env"),
    JWT_TOKEN_LOCATION=["headers"],
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_env"))),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_env"))),
)

security = AuthX(config=config)
bearer = HTTPBearer()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")