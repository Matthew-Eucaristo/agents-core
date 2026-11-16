BASE_URL = "https://partner-gateway.example/v2"


class GatewayError(Exception):
    pass


def unwrap(payload):
    if not isinstance(payload, dict) or not payload.get("ok"):
        reason = payload.get("error") if isinstance(payload, dict) else None
        raise GatewayError(reason or "gateway returned an unexpected payload")
    return payload["result"]
