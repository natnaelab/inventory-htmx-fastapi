from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, text, Column, DateTime, Index


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    username: str = Field(max_length=255, unique=True, index=True)
    email: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)

    role: str = Field(max_length=50)
    is_active: bool = Field(default=True)

    ad_object_guid: Optional[str] = Field(default=None, max_length=100, unique=True)
    ad_last_sync: Optional[datetime] = Field(default=None, sa_column=Column("ad_last_sync", DateTime(timezone=True)))

    last_login: Optional[datetime] = Field(default=None, sa_column=Column("last_login", DateTime(timezone=True)))
    current_session_token: Optional[str] = Field(default=None, max_length=500)
    session_expires: Optional[datetime] = Field(default=None, sa_column=Column("session_expires", DateTime(timezone=True)))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("updated_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    )

    login_count: int = Field(default=0)
    last_ip: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)

    class Config:
        indexes = [
            Index("idx_users_username", "username"),
            Index("idx_users_role", "role"),
            Index("idx_users_active", "is_active"),
            Index("idx_users_session_token", "current_session_token"),
            Index("idx_users_ad_object_guid", "ad_object_guid"),  # For AD lookups
        ]
