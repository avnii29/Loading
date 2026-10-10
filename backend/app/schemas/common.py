from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: str | None
    is_read: bool
    created_at: datetime


class ImpactSummary(BaseModel):
    meals_distributed: float
    items_delivered: float
    kg_recovered: float
    donations_completed: float
    has_events: bool
