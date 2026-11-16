import dataclasses
import os
import pathlib

from payments.errors import ConfigError

DEFAULT_BASE_URL = "https://api.northpay.example"


@dataclasses.dataclass(frozen=True)
class PaymentConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 10.0


def read_env_file(path):
    path = pathlib.Path(path)
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and not name.startswith("#"):
            values[name.strip()] = value.strip().strip('"')
    return values


def read_settings(env_file=".env", environ=None):
    environ = os.environ if environ is None else environ
    return {**read_env_file(env_file), **environ}


def load_config(settings=None):
    settings = read_settings() if settings is None else settings
    api_key = settings.get("PAYMENTS_API_KEY", "")
    if not api_key:
        raise ConfigError("PAYMENTS_API_KEY is not set")
    return PaymentConfig(
        api_key=api_key,
        base_url=settings.get("PAYMENTS_BASE_URL", DEFAULT_BASE_URL),
        timeout=float(settings.get("PAYMENTS_TIMEOUT", 10.0)),
    )
