import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Security, BackgroundTasks, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text

from authx import TokenPayload

from core.database import get_db
from core.email.service import EmailService
from core.storage.local import LocalStorage
from models import User
from schemas.auth import *
from core.security import security, bearer, pwd_context
from core.auth.service import AuthService

from core.deps import get_current_user



router = APIRouter(prefix="/auth", tags=["auth"])
storage = LocalStorage()


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {
            "description": "Invalid credentials"
        }
    }
)
async def login(
    data: UserLoginSchema, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    access_token = security.create_access_token(uid=str(user.id))
    refresh_token = security.create_refresh_token(uid=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "email_verified": user.email_verified
    }


@router.post(
    "/register",
    response_model=TokenResponse,
    responses={
        409: {
            "description": "User already exists"
        }
    }
)
async def register(
    data: UserRegisterSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    existing_user = result.scalar_one_or_none()

    hashed_password = pwd_context.hash(data.password)

    if existing_user:
        if existing_user.email_verified:
            raise HTTPException(409, "User already exists")

        # update unverified user
        existing_user.username = data.username
        existing_user.password_hash = hashed_password
        existing_user.email_verified = False
        existing_user.created_at = func.now()

        result = await db.execute(
            text("""
                SELECT EXTRACT(EPOCH FROM (now() - created_at)) AS seconds
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": existing_user.id}
        )

        row = result.first()

        if row and row.seconds < 120:
            raise HTTPException(429, "Try again later")
        
        user = existing_user

    else:
        user = User(
            email=data.email,
            username=data.username,
            password_hash=hashed_password,
            email_verified=False
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = await AuthService.create_email_token(db, user.id)

    background_tasks.add_task(
        EmailService.send_verification_email,
        user.email,
        token
    )

    access_token = security.create_access_token(uid=str(user.id))
    refresh_token = security.create_refresh_token(uid=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "email_verified": user.email_verified
    }


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    responses={401: {"description": "Invalid refresh token"}})
async def refresh(
    token = Security(bearer),
    payload: TokenPayload = Security(security.refresh_token_required)
):
    try:
        new_access_token = security.create_access_token(uid=payload.sub)
        return {"access_token": new_access_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get(
    "/me",
    response_model=ProfileResponse,
    responses={401: {"description": "Not authenticated"}}
)
async def me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return await AuthService.get_profile(db, user.id)


@router.put("/me")
async def update_me(
    data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user.username = data.username

    await db.commit()
    await db.refresh(user)

    return {
        "username": user.username,
        "avatar": user.avatar_url
    }


@router.get("/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    ok = await AuthService.verify_email(db, token)

    if ok:
        return HTMLResponse("""
        <html>
            <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
                <h1>✅ Email подтверждён!</h1>
            </body>
        </html>
        """)
    else:
        return HTMLResponse("""
        <html>
            <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
                <h1>❌ Некорректная или истекшая ссылка</h1>
                <p>Пожалуйста, запросите новое письмо для подтверждения email</p>
            </body>
        </html>
        """)


@router.post(
    "/resend-email",
    responses={
        400: {"description": "Email already verified"},
        401: {"description": "Not authenticated"},
        429: {"description": "Too many requests"}
    }
)
async def resend_email(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.email_verified:
        raise HTTPException(400, "Email already verified")
    
    result = await db.execute(
        text("""
            SELECT expires_at
            FROM email_verification_tokens
            WHERE user_id = :user_id
            ORDER BY id DESC
            LIMIT 1
        """),
        {"user_id": user.id}
    )

    row = result.first()

    if row and row.expires_at:
        if row.expires_at > datetime.now(timezone.utc):
            raise HTTPException(429, "Token still active, try later")
        
    token = await AuthService.create_email_token(db, user.id)

    background_tasks.add_task(
        EmailService.send_verification_email,
        user.email,
        token
    )

    return {"message": "Email sent"}

    
@router.get("/avatars/{filename}")
def get_avatar(filename: str):
    path = f"static/avatars/{filename}"

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path)


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    path = await storage.upload_avatar(file, str(user.id))

    user.avatar_url = path

    await db.commit()

    return {
        "avatar": path
    }