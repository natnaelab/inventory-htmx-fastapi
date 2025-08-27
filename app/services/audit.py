from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.audit_log import AuditLog
import logging

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def get_entity_history(self, entity_name: str, entity_id: str, page: int = 1, limit: int = 100) -> List[Dict]:
        try:
            base_query = self.db.query(AuditLog).filter(
                AuditLog.entity_name == entity_name,
                AuditLog.entity_id == str(entity_id),
                AuditLog.action.in_(["CREATE", "UPDATE", "DELETE"]),
            )

            total_count = base_query.count()

            offset = (page - 1) * limit
            history_logs = base_query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

            results = [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "username": log.username,
                    "action": log.action,
                    "changes": log.changes,
                    "path": log.path,
                }
                for log in history_logs
            ]

            return {"logs": results, "total": total_count}
        except Exception as e:
            logger.error(f"Error getting entity history for {entity_name} {entity_id}: {e}")
            return None

    def get_log_statistics(self, days: int = 30) -> Dict:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            base_query = self.db.query(AuditLog).filter(AuditLog.timestamp >= cutoff_date, AuditLog.action.is_(None))

            total_requests = base_query.count()

            status_stats = (
                self.db.query(AuditLog.status_code, func.count(AuditLog.id).label("count"))
                .filter(AuditLog.timestamp >= cutoff_date, AuditLog.action.is_(None))
                .group_by(AuditLog.status_code)
                .all()
            )

            endpoint_stats = (
                self.db.query(AuditLog.path, func.count(AuditLog.id).label("count"))
                .filter(AuditLog.timestamp >= cutoff_date, AuditLog.action.is_(None))
                .group_by(AuditLog.path)
                .order_by(func.count(AuditLog.id).desc())
                .limit(10)
                .all()
            )

            error_count = base_query.filter(AuditLog.status_code >= 400).count()

            avg_response_time = (
                self.db.query(func.avg(AuditLog.response_time_ms))
                .filter(
                    AuditLog.timestamp >= cutoff_date, AuditLog.response_time_ms.isnot(None), AuditLog.action.is_(None)
                )
                .scalar()
            )

            return {
                "period_days": days,
                "total_requests": total_requests,
                "error_count": error_count,
                "error_rate": (error_count / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else 0,
                "status_codes": {str(status): count for status, count in status_stats},
                "top_endpoints": [{"path": path, "count": count} for path, count in endpoint_stats],
            }

        except Exception as e:
            logger.error(f"Error getting log statistics: {e}")
            return None

    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        try:
            recent_errors = (
                self.db.query(AuditLog)
                .filter(AuditLog.status_code >= 400, AuditLog.action.is_(None))
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "method": error.method,
                    "path": error.path,
                    "status_code": error.status_code,
                    "remote_addr": error.remote_addr,
                    "user_agent": error.user_agent,
                    "error_message": error.error_message,
                    "response_time_ms": error.response_time_ms,
                }
                for error in recent_errors
            ]

        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return None

    def get_user_activity(self, username: Optional[str] = None, days: int = 7) -> List[Dict]:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = self.db.query(AuditLog).filter(AuditLog.timestamp >= cutoff_date, AuditLog.action.is_(None))

            if username:
                query = query.filter(AuditLog.username == username)

            activity_logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()

            return [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "username": log.username,
                    "method": log.method,
                    "path": log.path,
                    "status_code": log.status_code,
                    "remote_addr": log.remote_addr,
                    "response_time_ms": log.response_time_ms,
                }
                for log in activity_logs
            ]
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return None
