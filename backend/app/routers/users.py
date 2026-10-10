from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import ProfileUpdateRequest, UserResponse, to_user_response

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return to_user_response(user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = user.profile
    if data.full_name:
        profile.full_name = data.full_name.strip()
    if data.phone is not None:
        profile.phone = data.phone
    db.add(profile)
    db.commit()
    db.refresh(user)
    return to_user_response(user)
