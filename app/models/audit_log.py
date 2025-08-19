from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, text, Column, DateTime, Text


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    method: str = Field(max_length=10)
    path: str = Field(max_length=500)
    query_params: Optional[str] = Field(default=None, sa_column=Column("query_params", Text))
    user_agent: Optional[str] = Field(default=None, max_length=500)
    remote_addr: Optional[str] = Field(default=None, max_length=45)

    status_code: int
    response_time_ms: Optional[float] = Field(default=None)

    user_id: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("timestamp", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), index=True)
    )

    error_message: Optional[str] = Field(default=None, sa_column=Column("error_message", Text))
    request_body_size: Optional[int] = Field(default=None)
    response_body_size: Optional[int] = Field(default=None)
