from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
import ldap
import uuid
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


class UserRole:
    ADMINISTRATOR = "administrator"
    VISITOR = "visitor"


class AuthService:
    def authenticate_ad(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            ldap_conn = ldap.initialize(settings.ldap_url)
            ldap_conn.protocol_version = ldap.VERSION3
            ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
            
            try:
                ldap_conn.simple_bind_s(settings.ldap_bind_dn, settings.ldap_bind_password)
                logger.debug(f"Service account bind successful")

                username_clean = username.split('@')[0] if '@' in username else username
                search_filter = f"(&(objectClass=user)(sAMAccountName={username_clean}))"
                result = ldap_conn.search_s(
                    settings.ldap_base_dn, 
                    ldap.SCOPE_SUBTREE, 
                    search_filter, 
                    ['distinguishedName', 'memberOf', 'mail', 'displayName', 'objectGUID']
                )

                if not result:
                    logger.warning(f"User {username} not found in AD")
                    return None

                user_entries = [entry for entry in result if entry[0] is not None]
                if not user_entries:
                    return None

                user_dn, user_attrs = user_entries[0]
                logger.info(f"Found user: {user_dn}")
                user_groups = [group.decode('utf-8') for group in user_attrs.get('memberOf', [])]

                role = self._determine_role(user_groups)
                if role is None:
                    logger.warning(f"User {username} has no valid role assignment")
                    logger.debug(f"User groups: {user_groups}")
                    return None

                try:
                    user_conn = ldap.initialize(settings.ldap_url)
                    user_conn.protocol_version = ldap.VERSION3
                    user_conn.set_option(ldap.OPT_REFERRALS, 0)

                    auth_username = username if '@' in username else f"{username_clean}@{settings.ldap_domain}"
                    user_conn.simple_bind_s(auth_username, password)
                    user_conn.unbind()

                    ad_object_guid = None
                    if 'objectGUID' in user_attrs and user_attrs['objectGUID']:
                        guid_bytes = user_attrs['objectGUID'][0]
                        ad_object_guid = str(uuid.UUID(bytes_le=guid_bytes))
                    
                    display_name = username_clean
                    if 'displayName' in user_attrs and user_attrs['displayName']:
                        display_name = user_attrs['displayName'][0].decode('utf-8')
                    
                    email = None
                    if 'mail' in user_attrs and user_attrs['mail']:
                        email = user_attrs['mail'][0].decode('utf-8')
                    
                    return {
                        "username": username_clean,
                        "role": role,
                        "display_name": display_name,
                        "email": email,
                        "ad_object_guid": ad_object_guid,
                        "ad_groups": user_groups
                    }
                    
                except ldap.INVALID_CREDENTIALS:
                    logger.warning(f"Invalid credentials for {username}")
                    return None
                except ldap.LDAPError as e:
                    logger.error(f"LDAP error during user authentication for {username}: {e}")
                    return None
                
            except ldap.INVALID_CREDENTIALS:
                logger.error(f"Service account bind failed - check LDAP_BIND_DN and LDAP_BIND_PASSWORD")
                return None
            except ldap.LDAPError as e:
                logger.error(f"LDAP error during service account bind: {e}")
                return None
            finally:
                ldap_conn.unbind()
                
        except Exception as e:
            logger.error(f"AD authentication error for {username}: {e}")
            return None

    def _determine_role(self, user_groups: List[str]) -> Optional[str]:
        if settings.admin_group in user_groups:
            return UserRole.ADMINISTRATOR

        if settings.visitor_group in user_groups:
            return UserRole.VISITOR

        return None
    
    def create_session_token(self, user_data: Dict[str, Any]) -> str:
        session_data = {
            "username": user_data.get("username"),
            "role": user_data.get("role"),
            "user_id": user_data.get("user_id"),
            "exp": (datetime.now(timezone.utc) + timedelta(hours=settings.session_expire_hours)).timestamp()
        }

        token = jwt.encode(session_data, settings.secret_key, algorithm=ALGORITHM)
        return token
    
    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

            if datetime.now(timezone.utc).timestamp() > payload.get('exp', 0):
                return None
            
            return payload
            
        except JWTError as e:
            logger.debug(f"Session token verification failed: {e}")
            return None
