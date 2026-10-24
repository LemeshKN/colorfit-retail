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