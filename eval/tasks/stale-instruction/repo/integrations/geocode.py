from urllib.parse import urlencode

from integrations import gateway, legacy_http


def get_coordinates(city):
    query = urlencode({"city": city})
    payload = legacy_http.fetch(f"{gateway.BASE_URL}/geocode?{query}")
    return gateway.unwrap(payload)
