import os
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def _database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg://" + raw[len("postgres://") :]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg://" + raw[len("postgresql://") :]
        return _ensure_hosted_ssl(raw)

    user = os.getenv("DB_USER") or ""
    password = quote_plus(os.getenv("DB_PASSWORD") or "")
    host = os.getenv("DB_HOST") or ""
    port = os.getenv("DB_PORT") or ""
    name = os.getenv("DB_NAME") or ""
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def _ensure_hosted_ssl(url: str) -> str:
    """Require TLS for public database hosts. Local and private hosts stay unchanged."""
    host = urlparse(url.replace("postgresql+psycopg", "postgresql", 1)).hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"} or "." not in host:
        return url
    if "sslmode=" in url:
        return url
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}sslmode=require"


DATABASE_URL = _database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=2,
    pool_recycle=300,
)

def check_database():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True

from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
