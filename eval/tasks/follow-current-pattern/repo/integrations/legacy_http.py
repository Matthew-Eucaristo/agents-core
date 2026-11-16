import json
import urllib.error
import urllib.request

from integrations.gateway import GatewayError


def fetch(url):
    try:
        with urllib.request.urlopen(url) as reply:
            return json.loads(reply.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise GatewayError(f"request to {url} failed: {error}") from error
