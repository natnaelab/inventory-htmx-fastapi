from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from typing import Dict, Any

from app.models.audit_log import AuditLog
from app.audit.context import audit_context


def get_model_changes(model_instance) -> Dict[str, Any]:
    state = inspect(model_instance)
    changes = {}
    for attr in state.attrs:
        history = attr.history
        if not history.has_changes():
            continue

        old_value = history.deleted[0] if history.deleted else None
        new_value = history.added[0] if history.added else None

        if old_value != new_value:
            changes[attr.key] = {"old": str(old_value), "new": str(new_value)}
    return changes


def before_flush_listener(session: Session, flush_context, instances):
    context = audit_context.get() or {}

    session.info.setdefault("pending_audit_logs", [])

    # Log Updated Objects
    for instance in session.dirty:
        if not hasattr(instance, "__tablename__") or isinstance(instance, AuditLog):
            continue
        changes = get_model_changes(instance)
        if not changes:
            continue
        pk_val = inspect(instance).identity[0] if inspect(instance).identity else None
        log = AuditLog(
            action="UPDATE",
            entity_name=instance.__class__.__name__,
            entity_id=str(pk_val) if pk_val else None,
            changes=changes,
            **context
        )
        session.add(log)

    # Log Deleted Objects
    for instance in session.deleted:
        if not hasattr(instance, "__tablename__") or isinstance(instance, AuditLog):
            continue
        state = inspect(instance)
        old_values = {attr.key: str(getattr(instance, attr.key, None)) for attr in state.attrs}
        pk_val = state.identity[0] if state.identity else None
        log = AuditLog(
            action="DELETE",
            entity_name=instance.__class__.__name__,
            entity_id=str(pk_val) if pk_val else None,
            changes={"old_values": old_values},
            **context
        )
        session.add(log)

    for instance in session.new:
        if not hasattr(instance, "__tablename__") or isinstance(instance, AuditLog):
            continue

        state = inspect(instance)
        new_values = {attr.key: str(getattr(instance, attr.key)) for attr in state.attrs}

        session.info["pending_audit_logs"].append({"instance": instance, "new_values": new_values, "context": context})


def after_flush_listener(session: Session, flush_context):
    pending_logs = session.info.get("pending_audit_logs", [])
    if not pending_logs:
        return

    for log_info in pending_logs:
        instance = log_info["instance"]

        pk_name = inspect(instance.__class__).primary_key[0].name
        pk_val = getattr(instance, pk_name, None)

        if pk_val:
            log = AuditLog(
                action="CREATE",
                entity_name=instance.__class__.__name__,
                entity_id=str(pk_val),
                changes={"new_values": log_info["new_values"]},
                **log_info["context"]
            )
            session.add(log)

    session.info["pending_audit_logs"] = []


def initialize_audit_listeners():
    event.listen(Session, "before_flush", before_flush_listener)
    event.listen(Session, "after_flush", after_flush_listener)
