from contextvars import ContextVar
from typing import Optional, Dict

audit_context: ContextVar[Optional[Dict]] = ContextVar("audit_context", default=None)
