from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.enums import UserRole, VerificationStatus
from app.models.organization import Organization, Destination, RecoveryPartner
from app.models.user import User, Profile
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    to_user_response,
)
from app.security.rate_limit import auth_limiter, client_key
from app.services.audit import write_audit
from app.services.auth import hash_password, verify_password, create_access_token
from app.services.login_identity import resolve_login_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _cookie_samesite() -> str:
    # A Vercel site and an API on another host are different sites.
    # Lax cookies are not sent on those credentialed API calls after refresh.
    # None requires Secure, which is already tied to production.
    settings = get_settings()
    return "none" if settings.environment == "production" else "lax"


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=_cookie_samesite(),
        max_age=settings.access_token_minutes * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite=_cookie_samesite(),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    auth_limiter.check(client_key(request, "register"))
    email = data.email.lower().strip()

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if data.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be publicly registered",
        )

    if data.role == UserRole.DONOR and data.donor_type is None:
        raise HTTPException(
            status_code=422,
            detail="Donor type is required for donor accounts",
        )

    if data.role != UserRole.DONOR and data.donor_type is not None:
        raise HTTPException(
            status_code=422,
            detail="Donor type is only valid for donor accounts",
        )

    if data.role in {UserRole.ORGANIZATION, UserRole.FARM_OPERATOR}:
        name = (data.organization_name or "").strip()
        if len(name) < 2:
            raise HTTPException(
                status_code=422,
                detail="Organisation or recovery partner name is required.",
            )

    try:
        user = User(
            email=email,
            password_hash=hash_password(data.password),
            role=data.role,
        )
        db.add(user)
        db.flush()

        profile = Profile(
            user_id=user.id,
            full_name=data.full_name.strip(),
            phone=data.phone,
            donor_type=data.donor_type,
        )
        db.add(profile)

        if data.role == UserRole.ORGANIZATION:
            org = Organization(
                user_id=user.id,
                name=data.organization_name.strip(),
                verification_status=VerificationStatus.UNVERIFIED,
                is_active=True,
            )
            db.add(org)
            db.flush()
            db.add(
                Destination(
                    organization_id=org.id,
                    name=org.name,
                    is_active=False,
                )
            )

        if data.role == UserRole.FARM_OPERATOR:
            db.add(
                RecoveryPartner(
                    user_id=user.id,
                    name=data.organization_name.strip(),
                    verification_status=VerificationStatus.UNVERIFIED,
                )
            )

        write_audit(
            db,
            action="auth.register",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            extra={"role": data.role.value},
        )
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return to_user_response(user)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    auth_limiter.check(client_key(request, "login"))
    email = resolve_login_email(data.email)
    user = db.scalar(select(User).where(User.email == email))

    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(user.id))
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return to_user_response(user)


@router.post("/logout")
def logout(response: Response):
    _clear_auth_cookie(response)
    return {"ok": True}
