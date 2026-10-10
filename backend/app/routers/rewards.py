from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.points import summary_for_user

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("/me")
def my_rewards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return summary_for_user(db, user.id)
