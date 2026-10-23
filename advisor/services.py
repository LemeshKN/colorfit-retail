from catalog.services import InvalidCardError, resolve_card

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