ALTER TABLE users ADD COLUMN last_login_at TEXT;

CREATE INDEX users_last_login_at ON users (last_login_at);
