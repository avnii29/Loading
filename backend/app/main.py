from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import check_database
from app.errors import register_error_handlers
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.donations import router as donations_router
from app.routers.impact import router as impact_router
from app.routers.notifications import router as notifications_router
from app.routers.organizations import router as organizations_router
from app.routers.location import router as location_router
from app.routers.logistics import router as logistics_router
from app.routers.rewards import router as rewards_router
from app.routers.uploads import router as uploads_router
from app.routers.users import router as users_router

settings = get_settings()

app = FastAPI(title=settings.app_name)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(donations_router)
app.include_router(organizations_router)
app.include_router(notifications_router)
app.include_router(impact_router)
app.include_router(rewards_router)
app.include_router(admin_router)
app.include_router(uploads_router)
app.include_router(location_router)
app.include_router(logistics_router)


@app.get("/api/health")
def health():
    try:
        check_database()
        return {
            "api": "healthy",
            "database": "connected",
        }
    except Exception:
        return {
            "api": "healthy",
            "database": "disconnected",
        }
