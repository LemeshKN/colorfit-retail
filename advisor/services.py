from catalog.services import InvalidCardError, resolve_card
from shops.services import get_advice_session, record_session, set_session_garment

ADVICE_SESSION_KEY = "advice_session_id"
SESSION_CARD_KEY = "card_code"
SESSION_SHOP_KEY = "shop_slug"


def remember_card(session, shop, card):
    session[SESSION_CARD_KEY] = card.code
    session[SESSION_SHOP_KEY] = shop.slug


def get_remembered_card(session, shop):
    """Return the active card saved for this shop, or None."""
    if session.get(SESSION_SHOP_KEY) != shop.slug:
        return None
    try:
        return resolve_card(session.get(SESSION_CARD_KEY, ""))
    except InvalidCardError:
        return None


def start_visit(session, shop, card, device_id):
    """Save one AdviceSession row and remember its id in the Django session."""
    advice_session = record_session(shop, card, device_id)
    session[ADVICE_SESSION_KEY] = advice_session.pk
    return advice_session


def attach_garment(session, shop, garment):
    """Fill the garment on the saved row. Return None if the row is missing."""
    pk = session.get(ADVICE_SESSION_KEY)
    if pk is None:
        return None
    advice_session = get_advice_session(pk, shop)
    if advice_session is None:
        session.pop(ADVICE_SESSION_KEY, None)
        return None
    set_session_garment(advice_session, garment)
    return advice_session