import datetime
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True

SEED = 20260914
USERS = 214
APPLIED = (("0001_create_users", "2025-02-11T10:02:41+00:00"), ("0002_add_users_last_login", "2025-09-03T14:27:09+00:00"))
GIVEN = (
    "Ada Lin Kai Noa Maya Omar Priya Jonas Ines Rahul Chloe Emeka Sofia Hannah Tomas Aiko Marta Dana Lee Sam "
    "Yusuf Elena Mateo Farah Soren Nadia Luca Imani Pavel Greta Hugo Leila Anders Mira Diego Zofia"
).split()
FAMILY = (
    "Whitfield Okafor Rivera Nair Lindqvist Tanaka Kowalska Brandt Carvalho Mehta Bernard Obi Marin Weiss "
    "Haddad Petrov Nakamura Oyelaran Castillo Novak Fischer Dubois Larsen Moreau Sato Ibrahim Keller Romano"
).split()
DOMAINS = ("example.test", "mail.example.test", "corp.example.test", "post.example.test")
START = datetime.datetime(2025, 2, 12, 8, 0, 0)


def stamp(moment):
    return moment.isoformat(timespec="seconds")


def build_rows(rng):
    rows = []
    created = START
    for number in range(1, USERS + 1):
        created += datetime.timedelta(seconds=rng.randrange(1800, 260000))
        given, family = rng.choice(GIVEN), rng.choice(FAMILY)
        email = f"{given}.{family}{number}@{rng.choice(DOMAINS)}".lower()
        verified = None
        if rng.random() < 0.63:
            verified = created + datetime.timedelta(seconds=rng.randrange(40, 172800))
        login = None
        if rng.random() < (0.85 if verified else 0.3):
            login = (verified or created) + datetime.timedelta(seconds=rng.randrange(60, 5000000))
        rows.append((
            email,
            f"{given} {family}",
            stamp(created),
            stamp(verified) if verified else None,
            stamp(login) if login else None,
        ))
    return rows


def main():
    repo = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(repo))
    from app import db, schema

    path = repo / "data" / "app.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = db.connect(path)
    migrations = {migration.name: migration for migration in schema.available(repo / "migrations")}
    for name, applied_at in APPLIED:
        schema.apply(connection, migrations[name], applied_at)
    connection.executemany(
        "INSERT INTO users (email, display_name, created_at, verified_at, last_login_at) VALUES (?, ?, ?, ?, ?)",
        build_rows(random.Random(SEED)),
    )
    connection.commit()
    connection.close()


if __name__ == "__main__":
    main()
