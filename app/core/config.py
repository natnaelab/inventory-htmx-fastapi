import os


class Settings:
    def __init__(self):
        # required environment variables, it will raise KeyError if not found
        self.base_url = os.environ['BASE_URL']
        self.secret_key = os.environ['SECRET_KEY']
        self.app_host = os.environ['APP_HOST']
        self.app_port = os.environ['APP_PORT']
        self.debug = os.environ['DEBUG']

        self.ldap_url = os.environ["LDAP_URL"]
        self.ldap_base_dn = os.environ["LDAP_BASE_DN"]
        self.ldap_bind_dn = os.environ["LDAP_BIND_DN"]
        self.ldap_bind_password = os.environ["LDAP_BIND_PASSWORD"]
        self.ldap_domain = os.environ["LDAP_DOMAIN"]

        self.admin_group = os.environ["ADMIN_GROUP"]
        self.visitor_group = os.environ["VISITOR_GROUP"]

        # optional environment variables, if not set defaults will be used
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
