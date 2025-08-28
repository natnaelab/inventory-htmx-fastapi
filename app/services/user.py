from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user import User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class UserService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, 
                   username: str, 
                   role: str, 
                   email: Optional[str] = None,
                   display_name: Optional[str] = None) -> User:
        """Create a new user"""
        user = User(
            username=username,
            email=email,
            display_name=display_name or username,
            role=role,
            is_active=True,
            login_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Created new user: {username} with role: {role}")
        return user
    
    def update_user_login(self, 
                         user: User, 
                         session_token: str,
                         ip_address: Optional[str] = None,
                         user_agent: Optional[str] = None) -> User:
        session_expire_time = datetime.now(timezone.utc) + timedelta(hours=settings.session_expire_hours)

        user.last_login = datetime.now(timezone.utc)
        user.current_session_token = session_token
        user.session_expires = session_expire_time
        user.login_count += 1
        user.last_ip = ip_address
        user.user_agent = user_agent
        user.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Updated login for user: {user.username}")
        return user

    def update_user_from_ad(self,
                           user: User,
                           ad_object_guid: Optional[str] = None,
                           email: Optional[str] = None) -> User:

        user.ad_object_guid = ad_object_guid
        user.ad_last_sync = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)

        if email and not user.email:
            user.email = email

        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Updated AD info for user: {user.username}")
        return user

    def invalidate_session(self, user: User) -> None:
        user.current_session_token = None
        user.session_expires = None
        user.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        logger.info(f"Invalidated session for user: {user.username}")

    def cleanup_expired_sessions(self) -> int:
        try:
            now = datetime.now(timezone.utc)
            expired_users = self.db.query(User).filter(
                and_(
                    User.session_expires < now,
                    User.current_session_token.isnot(None)
                )
            ).all()

            count = 0
            for user in expired_users:
                user.current_session_token = None
                user.session_expires = None
                count += 1

            self.db.commit()

            if count > 0:
                logger.info(f"Cleaned up {count} expired user sessions")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            self.db.rollback()
            return 0
    
    def get_active_users(self, days: int = 30) -> List[User]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return self.db.query(User).filter(
            and_(
                User.is_active == True,
                User.last_login >= cutoff_date
            )
        ).order_by(User.last_login.desc()).all()
