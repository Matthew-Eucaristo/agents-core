import dataclasses
import json
import urllib.error
import urllib.request

from payments.errors import TransportError


@dataclasses.dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: dict
    body: dict | None = None


@dataclasses.dataclass(frozen=True)
class Response:
    status: int
    body: dict


def decode_body(raw):
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


class HttpTransport:
    def __init__(self, timeout=10.0):
        self.timeout = timeout

    def send(self, request):
        data = None if request.body is None else json.dumps(request.body).encode()
        outgoing = urllib.request.Request(request.url, data=data, headers=request.headers, method=request.method)
        try:
            with urllib.request.urlopen(outgoing, timeout=self.timeout) as reply:
                return Response(reply.status, decode_body(reply.read()))
        except urllib.error.HTTPError as error:
            return Response(error.code, decode_body(error.read()))
        except (urllib.error.URLError, TimeoutError) as error:
            raise TransportError(f"could not reach {request.url}: {error}") from error
