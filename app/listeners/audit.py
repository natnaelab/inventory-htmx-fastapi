from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from app.models.audit_log import AuditLog
import json


def get_model_changes(model_instance) -> dict:
    """Gets the old and new values for a model instance."""
    state = inspect(model_instance)
    changes = {}

    for attr in state.attrs:
        history = attr.history
        if not history.has_changes():
            continue

        old_value = history.deleted[0] if history.deleted else None
        new_value = history.added[0] if history.added else None
        changes[attr.key] = {"old": old_value, "new": new_value}

    return changes


def log_changes(session: Session):
    """Function to be called before a session is flushed."""
    # Note: You need a way to get user/request context here.
    # This is often done using context variables or by passing it through.

    for obj in session.new:
        # This is a new object (CREATE)
        changes = {key: getattr(obj, key) for key in inspect(obj).attrs.keys()}
        log = AuditLog(
            action="CREATE",
            entity_name=obj.__class__.__name__,
            entity_id=str(getattr(obj, "id", None)),
            changes={"new_values": changes},
            # ... add user, path, and other request info
        )
        session.add(log)

    for obj in session.dirty:
        # This is an updated object (UPDATE)
        changes = get_model_changes(obj)
        if not changes:
            continue

        log = AuditLog(
            action="UPDATE",
            entity_name=obj.__class__.__name__,
            entity_id=str(getattr(obj, "id", None)),
            changes=changes,
            # ... add user, path, and other request info
        )
        session.add(log)


# Register the listener on the Session
event.listen(Session, "before_flush", log_changes)
