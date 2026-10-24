import uuid

from django.conf import settings

COOKIE_NAME = "cf_device"
ONE_YEAR = 60 * 60 * 24 * 365


def _clean_device_id(value):
    """Return the cookie value if it is a valid UUID, else None."""
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None


class DeviceCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        device_id = _clean_device_id(request.COOKIES.get(COOKIE_NAME))
        is_new = device_id is None
        if is_new:
            device_id = str(uuid.uuid4())

        request.device_id = device_id
        response = self.get_response(request)

        if is_new:
            response.set_cookie(
                COOKIE_NAME,
                device_id,
                max_age=ONE_YEAR,
                httponly=True,
                samesite="Lax",
                secure=getattr(settings, "DEVICE_COOKIE_SECURE", False),
            )
        return response