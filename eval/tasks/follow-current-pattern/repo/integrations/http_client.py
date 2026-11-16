import contextlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from integrations.gateway import GatewayError


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes

    def json(self):
        return json.loads(self.body.decode("utf-8"))


def _urllib_transport(url, timeout):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            return Response(reply.status, reply.read())
    except urllib.error.HTTPError as error:
        return Response(error.code, error.read())
    except (urllib.error.URLError, TimeoutError) as error:
        raise GatewayError(f"request to {url} failed: {error}") from error


_transport = _urllib_transport


@contextlib.contextmanager
def use_transport(transport):
    global _transport
    previous = _transport
    _transport = transport
    try:
        yield transport
    finally:
        _transport = previous


def get(url, *, timeout):
    response = _transport(url, timeout)
    if response.status >= 400:
        raise GatewayError(f"GET {url} returned HTTP {response.status}")
    return response
