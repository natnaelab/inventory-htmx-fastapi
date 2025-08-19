import os


class Settings:
    def __init__(self):
        self.base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        self.secret_key = os.getenv('SECRET_KEY', 'secret-key')
        self.app_host = os.getenv('APP_HOST', '0.0.0.0')
        self.app_port = os.getenv('APP_PORT', '8000')
        self.debug = os.getenv('DEBUG', 'false')

        self.ldap_url = os.getenv("LDAP_URL")
        self.ldap_base_dn = os.getenv("LDAP_BASE_DN")
        self.ldap_bind_dn = os.getenv("LDAP_BIND_DN")
        self.ldap_bind_password = os.getenv("LDAP_BIND_PASSWORD")
        self.ldap_domain = os.getenv("LDAP_DOMAIN")

        self.admin_group = os.getenv("ADMIN_GROUP")
        self.visitor_group = os.getenv("VISITOR_GROUP")

        self.session_expire_hours = int(os.getenv('SESSION_EXPIRE_HOURS', '8'))
        self.session_cookie_name = os.getenv('SESSION_COOKIE_NAME', 'inventory_session')

        self.log_level = os.getenv('LOG_LEVEL', 'INFO')

        self.threshold_all_in_one = int(os.getenv('THRESHOLD_ALL_IN_ONE', '4'))
        self.threshold_notebook = int(os.getenv('THRESHOLD_NOTEBOOK', '4'))
        self.threshold_docking_station = int(os.getenv('THRESHOLD_DOCKING_STATION', '4'))
        self.threshold_micro_form_factor = int(os.getenv('THRESHOLD_MICRO_FORM_FACTOR', '2'))
        self.threshold_monitor = int(os.getenv('THRESHOLD_MONITOR', '3'))
        self.threshold_backpack = int(os.getenv('THRESHOLD_BACKPACK', '4'))


settings = Settings()
