from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, COLLECTOR_API_KEY
from .database import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def verify_collector_api_key(x_api_key: str | None = Header(default=None)):
    """校验 Collector 请求中的 API Key"""
    if not COLLECTOR_API_KEY:
        return  # 未配置 API Key 则跳过校验
    if not x_api_key or x_api_key != COLLECTOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return bcrypt.hash(plain)


def create_access_token(username: str) -> str:
    expire = datetime.now() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
