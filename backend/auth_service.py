"""Authentication service — JWT token + bcrypt password hashing."""
from __future__ import annotations
import os
import traceback
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import SessionLocal
from user_model import User

SECRET_KEY = os.getenv("JWT_SECRET", "aiexcel-secret-key-change-in-production")
ALGORITHM = "HS256"
EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str) -> str:
    print("[auth] hash_password start")
    try:
        result = pwd_context.hash(password)
        print("[auth] hash_password done")
        return result
    except Exception:
        print("[auth] hash_password ERROR:")
        traceback.print_exc()
        raise


def verify_password(plain: str, hashed: str) -> bool:
    print("[auth] verify_password start")
    try:
        result = pwd_context.verify(plain, hashed)
        print("[auth] verify_password done — match:", result)
        return result
    except Exception:
        print("[auth] verify_password ERROR:")
        traceback.print_exc()
        raise


def create_token(user_id: int, username: str) -> str:
    print("[auth] jwt create start — user_id:", user_id)
    try:
        expire = datetime.utcnow() + timedelta(days=EXPIRE_DAYS)
        payload = {"sub": str(user_id), "username": username, "exp": expire}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        print("[auth] jwt create done")
        return token
    except Exception:
        print("[auth] jwt create ERROR:")
        traceback.print_exc()
        raise


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    print("[auth] get_current_user start")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            print("[auth] get_current_user — no sub in token")
            raise credentials_exception
    except JWTError:
        print("[auth] get_current_user — JWT decode failed")
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            print("[auth] get_current_user — user not found in DB")
            raise credentials_exception
        print("[auth] get_current_user done — user:", user.username)
        return user
    finally:
        db.close()
