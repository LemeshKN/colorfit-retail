from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from catalog.services import InvalidCardError

from .models import AdviceSession, Shop


def record_session(shop, card, device_id, garment=None):
    """Save one row for a valid card. Call this only after resolve_card works."""
    if not card.is_active:
        raise InvalidCardError(card.code)
    return AdviceSession.objects.create(
        shop=shop,
        card_code=card,
        garment=garment,
        device_id=device_id,
        local_date=timezone.localdate(),  # India date, from TIME_ZONE
    )


def set_session_garment(session, garment):
    session.garment = garment
    session.save(update_fields=["garment"])
    return session


def unique_visits_report(shop, date_range):
    """date_range is (start_date, end_date), both included.

    Returns total entries, unique devices over the whole range,
    counted visits (one per device per day), and one row per day.
    """
    start, end = date_range
    sessions = AdviceSession.objects.filter(
        shop=shop, local_date__range=(start, end)
    )
    totals = sessions.aggregate(
        total_entries=Count("id"),
        unique_devices=Count("device_id", distinct=True),
    )
    days = []
    for row in (
        sessions.values("local_date")
        .annotate(entries=Count("id"), unique_devices=Count("device_id", distinct=True))
        .order_by("local_date")
    ):
        days.append(
            {
                "date": row["local_date"],
                "entries": row["entries"],
                "unique_devices": row["unique_devices"],
                "repeats": row["entries"] - row["unique_devices"],
            }
        )
    return {
        **totals,
        "counted_visits": sum(d["unique_devices"] for d in days),
        "days": days,
    }

def list_active_shops():
    return Shop.objects.filter(is_active=True).order_by("city", "name")


def get_active_shop(slug):
    """Case does not matter: 'SH-014' and 'sh-014' find the same shop."""
    return Shop.objects.filter(slug=(slug or "").lower(), is_active=True).first()

def get_advice_session(pk, shop):
    """Return the AdviceSession with this id for this shop, or None."""
    return AdviceSession.objects.filter(pk=pk, shop=shop).first()


KEY_MIN_LENGTH = 6
KEY_MAX_WRONG_TRIES = 5
KEY_WINDOW_SECONDS = 60


class KeyLockedError(Exception):
    """Too many wrong keys from this device in the last minute."""


def shop_needs_key(shop):
    return bool(shop.access_key_hash)


def set_shop_key(shop, plain_key):
    """Store a hash of the key. An empty key removes the key."""
    plain_key = (plain_key or "").strip()
    if plain_key and len(plain_key) < KEY_MIN_LENGTH:
        raise ValueError(f"The key needs at least {KEY_MIN_LENGTH} characters.")
    shop.access_key_hash = make_password(plain_key) if plain_key else ""
    shop.save(update_fields=["access_key_hash"])


def check_shop_key(shop, plain_key, device_id):
    """True if the key is right, or the shop has no key.
    Raises KeyLockedError after 5 wrong tries in a minute."""
    if not shop.access_key_hash:
        return True
    cache_key = f"shopkey:{shop.pk}:{device_id}"
    wrong_tries = cache.get(cache_key, 0)
    if wrong_tries >= KEY_MAX_WRONG_TRIES:
        raise KeyLockedError
    if check_password((plain_key or "").strip(), shop.access_key_hash):
        cache.delete(cache_key)
        return True
    cache.set(cache_key, wrong_tries + 1, KEY_WINDOW_SECONDS)
    return False