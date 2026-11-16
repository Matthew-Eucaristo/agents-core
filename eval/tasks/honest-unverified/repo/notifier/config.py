import configparser
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("settings.ini")


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    starttls: bool
    username: str
    password: str
    timeout: float
    sender: str
    sender_name: str


def load_settings(path=None):
    source = Path(path or os.environ.get("NOTIFIER_SETTINGS") or DEFAULT_PATH)
    parser = configparser.ConfigParser()
    with source.open() as handle:
        parser.read_file(handle)
    smtp = parser["smtp"]
    mail = parser["mail"]
    return Settings(
        host=smtp["host"],
        port=smtp.getint("port", 587),
        starttls=smtp.getboolean("starttls", True),
        username=smtp.get("username", ""),
        password=os.environ.get("NOTIFIER_SMTP_PASSWORD", ""),
        timeout=smtp.getfloat("timeout", 10.0),
        sender=mail["sender"],
        sender_name=mail.get("sender_name", ""),
    )
