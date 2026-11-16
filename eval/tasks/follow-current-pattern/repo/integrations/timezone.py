from urllib.parse import urlencode

from integrations import gateway, legacy_http


def get_timezone(city):
    query = urlencode({"city": city})
    payload = legacy_http.fetch(f"{gateway.BASE_URL}/timezone?{query}")
    return gateway.unwrap(payload)
