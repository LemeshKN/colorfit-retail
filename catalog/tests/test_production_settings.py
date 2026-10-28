from config.settings import production as prod


def test_production_settings_are_safe():
    assert prod.DEBUG is False
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.DEVICE_COOKIE_SECURE is True
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_whitenoise_comes_right_after_security_middleware():
    assert prod.MIDDLEWARE[0] == "django.middleware.security.SecurityMiddleware"
    assert prod.MIDDLEWARE[1] == "whitenoise.middleware.WhiteNoiseMiddleware"


def test_card_rate_limit_uses_a_cache_shared_by_workers():
    assert prod.CACHES["default"]["BACKEND"].endswith("DatabaseCache")


def test_importing_production_does_not_change_base_middleware():
    from config.settings import base

    assert "whitenoise.middleware.WhiteNoiseMiddleware" not in base.MIDDLEWARE