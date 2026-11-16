def create_user(connection, email, display_name, created_at):
    cursor = connection.execute(
        "INSERT INTO users (email, display_name, created_at) VALUES (?, ?, ?)",
        (email.strip().lower(), display_name, created_at),
    )
    connection.commit()
    return cursor.lastrowid


def mark_verified(connection, user_id, verified_at):
    connection.execute(
        "UPDATE users SET verified_at = ? WHERE id = ? AND verified_at IS NULL", (verified_at, user_id)
    )
    connection.commit()


def record_login(connection, user_id, logged_in_at):
    connection.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (logged_in_at, user_id))
    connection.commit()


def find_by_email(connection, email):
    return connection.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()


def count_users(connection):
    return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
