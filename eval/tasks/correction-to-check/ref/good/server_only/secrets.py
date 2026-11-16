import os

SESSION_SIGNING_KEY = os.environ.get("SESSION_SIGNING_KEY", "local-development-key")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "profiles.sqlite3")
PASSWORD_RESET_TTL_SECONDS = 900
