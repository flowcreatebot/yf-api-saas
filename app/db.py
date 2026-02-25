from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import APIKey, Base, User
from .security import hash_api_key


def _sqlite_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def build_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=_sqlite_connect_args(url))


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


def verify_database_connection() -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def sync_configured_api_keys() -> None:
    configured_keys = [settings.api_master_key]
    if settings.api_valid_keys.strip():
        configured_keys.extend([k.strip() for k in settings.api_valid_keys.split(",") if k.strip()])

    deduped_keys: list[str] = []
    seen: set[str] = set()
    for key in configured_keys:
        if key and key not in seen:
            deduped_keys.append(key)
            seen.add(key)

    if not deduped_keys:
        return

    with SessionLocal() as db:
        bootstrap_user = db.query(User).filter(User.email == "system@yfapi.local").first()
        if bootstrap_user is None:
            bootstrap_user = User(
                email="system@yfapi.local",
                hashed_password="!",
            )
            db.add(bootstrap_user)
            db.flush()

        existing_hashes = {
            row[0]
            for row in db.query(APIKey.key_hash)
            .filter(APIKey.user_id == bootstrap_user.id)
            .all()
        }

        for index, key in enumerate(deduped_keys):
            key_hash = hash_api_key(key)
            if key_hash in existing_hashes:
                continue

            label = "master" if index == 0 else f"bootstrap-{index}"
            db.add(
                APIKey(
                    key_hash=key_hash,
                    user_id=bootstrap_user.id,
                    name=label,
                    status="active",
                )
            )

        db.commit()
