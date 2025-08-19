from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.audit_log import AuditLog
import logging

logger = logging.getLogger(__name__)


class AuditService:    
    def __init__(self, db: Session):
        self.db = db
    
    def get_log_statistics(self, days: int = 30) -> Dict:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            total_requests = self.db.query(AuditLog).filter(
                AuditLog.timestamp >= cutoff_date
            ).count()

            status_stats = self.db.query(
                AuditLog.status_code,
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.timestamp >= cutoff_date
            ).group_by(AuditLog.status_code).all()

            endpoint_stats = self.db.query(
                AuditLog.path,
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.timestamp >= cutoff_date
            ).group_by(AuditLog.path).order_by(
                func.count(AuditLog.id).desc()
            ).limit(10).all()

            error_count = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.timestamp >= cutoff_date,
                    AuditLog.status_code >= 400
                )
            ).count()

            avg_response_time = self.db.query(
                func.avg(AuditLog.response_time_ms)
            ).filter(
                and_(
                    AuditLog.timestamp >= cutoff_date,
                    AuditLog.response_time_ms.isnot(None)
                )
            ).scalar()

            return {
                'period_days': days,
                'total_requests': total_requests,
                'error_count': error_count,
                'error_rate': (error_count / total_requests * 100) if total_requests > 0 else 0,
                'avg_response_time_ms': round(avg_response_time, 2) if avg_response_time else 0,
                'status_codes': {str(status): count for status, count in status_stats},
                'top_endpoints': [{'path': path, 'count': count} for path, count in endpoint_stats]
            }

        except Exception as e:
            logger.error(f"Error getting log statistics: {e}")
            return None
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        try:
            recent_errors = self.db.query(AuditLog).filter(
                AuditLog.status_code >= 400
            ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
            
            return [
                {
                    'timestamp': error.timestamp.isoformat(),
                    'method': error.method,
                    'path': error.path,
                    'status_code': error.status_code,
                    'remote_addr': error.remote_addr,
                    'user_agent': error.user_agent,
                    'error_message': error.error_message,
                    'response_time_ms': error.response_time_ms
                }
                for error in recent_errors
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return None

    def get_user_activity(self, username: Optional[str] = None, days: int = 7) -> List[Dict]:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = self.db.query(AuditLog).filter(AuditLog.timestamp >= cutoff_date)
            
            if username:
                query = query.filter(AuditLog.username == username)

            query = query.filter(AuditLog.username.isnot(None))
            
            activity_logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
            
            return [
                {
                    'timestamp': log.timestamp.isoformat(),
                    'username': log.username,
                    'method': log.method,
                    'path': log.path,
                    'status_code': log.status_code,
                    'remote_addr': log.remote_addr,
                    'response_time_ms': log.response_time_ms
                }
                for log in activity_logs
            ]
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return None
