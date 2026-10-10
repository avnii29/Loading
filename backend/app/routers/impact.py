from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.enums import ImpactKind
from app.models.ops import ImpactEvent
from app.models.user import User
from app.schemas.common import ImpactSummary

router = APIRouter(prefix="/api/impact", tags=["impact"])


@router.get("", response_model=ImpactSummary)
def summary(_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = dict(
        db.execute(
            select(ImpactEvent.kind, func.coalesce(func.sum(ImpactEvent.quantity), 0))
            .where(ImpactEvent.is_demo.is_(False))
            .group_by(ImpactEvent.kind)
        ).all()
    )
    total_events = db.scalar(
        select(func.count()).select_from(ImpactEvent).where(ImpactEvent.is_demo.is_(False))
    ) or 0

    def qty(kind: ImpactKind) -> float:
        value = counts.get(kind, 0)
        return float(value or 0)

    return ImpactSummary(
        meals_distributed=qty(ImpactKind.MEALS_DISTRIBUTED),
        items_delivered=qty(ImpactKind.ITEMS_DELIVERED),
        kg_recovered=qty(ImpactKind.KG_RECOVERED),
        donations_completed=qty(ImpactKind.DONATION_COMPLETED),
        has_events=total_events > 0,
    )
