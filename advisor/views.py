from functools import wraps

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from catalog.services import (
    InvalidCardError,
    get_bottom_previews,
    get_bottom_type,
    get_bottom_types,
    get_family,
    get_garment,
    get_pairings,
    get_shade,
    get_visible_shades,
    list_families,
    list_garments,
    resolve_card,
)
from shops.services import (
    KeyLockedError,
    check_shop_key,
    get_active_shop,
    list_active_shops,
    shop_needs_key,
)

from .forms import CardEntryForm
from .services import attach_garment, get_remembered_card, remember_card, start_visit

SESSION_SECONDS = 2 * 60 * 60


def shop_flow(view):
    """Find the shop and the saved card. No card means back to card entry."""

    @wraps(view)
    def wrapper(request, shop_slug, *args, **kwargs):
        shop = get_active_shop(shop_slug)
        if shop is None:
            raise Http404
        
        card = get_remembered_card(request.session, shop)
        if card is None:
            return redirect("advisor:card_entry", shop_slug=shop.slug)
        return view(request, shop, card, *args, **kwargs)

    return wrapper


def find_shop(request):
    return render(request, "advisor/find_shop.html", {"shops": list_active_shops()})

def shop_menu(request, shop_slug):
    shop = get_active_shop(shop_slug)
    if shop is None:
        raise Http404
    return render(request, "advisor/shop_menu.html", {"shop": shop})

def card_entry(request, shop_slug):
    shop = get_active_shop(shop_slug)
    if shop is None:
        raise Http404
    needs_key = shop_needs_key(shop)
    key_error = None

    if request.method == "POST":
        form = CardEntryForm(request.POST)
        key_ok = True
        if needs_key:
            try:
                key_ok = check_shop_key(
                    shop, request.POST.get("shop_key", ""), request.device_id
                )
            except KeyLockedError:
                key_ok = False
                key_error = _("Too many tries. Wait one minute and try again.")
            if not key_ok and key_error is None:
                key_error = _("The pass key is not correct.")
        if key_ok and form.is_valid():
            try:
                card = resolve_card(form.cleaned_data["card_id"])
            except InvalidCardError:
                form.add_error(
                    "card_id",
                    _("We could not find this card ID. Check the card and try again."),
                )
            else:
                remember_card(request.session, shop, card)
                request.session.set_expiry(SESSION_SECONDS)
                start_visit(request.session, shop, card, request.device_id)
                return redirect("advisor:garments", shop_slug=shop.slug)
    else:
        form = CardEntryForm()

    return render(
        request,
        "advisor/card_entry.html",
        {"shop": shop, "form": form, "needs_key": needs_key, "key_error": key_error},
    )

@shop_flow
def garments(request, shop, card):
    return render(
        request,
        "advisor/garments.html",
        {"shop": shop, "garments": list_garments()},
    )


@shop_flow
def colors(request, shop, card, garment_slug):
    garment = get_garment(garment_slug)
    if garment is None:
        raise Http404
    attach_garment(request.session, shop, garment)
    return render(
        request,
        "advisor/colors.html",
        {"shop": shop, "garment": garment, "families": list_families()},
    )


@shop_flow
def shades(request, shop, card, garment_slug, family_slug):
    garment, family = get_garment(garment_slug), get_family(family_slug)
    if garment is None or family is None:
        raise Http404
    return render(
        request,
        "advisor/shades.html",
        {
            "shop": shop,
            "garment": garment,
            "family": family,
            "recommendations": get_visible_shades(card.skin_tone, family),
        },
    )


@shop_flow
def pairing_bottoms(request, shop, card, garment_slug, shade_id):
    garment, shade = get_garment(garment_slug), get_shade(shade_id)
    if garment is None or shade is None:
        raise Http404
    bottoms = list(get_bottom_types(garment))
    if not bottoms:  # garment has no pairing
        raise Http404
    return render(
        request,
        "advisor/pairing_bottoms.html",
        {
            "shop": shop,
            "garment": garment,
            "shade": shade,
            "previews": get_bottom_previews(shade, bottoms),
        },
    )


@shop_flow
def pairing(request, shop, card, garment_slug, shade_id, bottom_slug):
    garment, shade = get_garment(garment_slug), get_shade(shade_id)
    bottom = get_bottom_type(bottom_slug)
    if garment is None or shade is None or bottom is None:
        raise Http404
    if not get_bottom_types(garment).filter(pk=bottom.pk).exists():
        raise Http404
    return render(
        request,
        "advisor/pairing.html",
        {
            "shop": shop,
            "garment": garment,
            "shade": shade,
            "bottom": bottom,
            "pairings": get_pairings(shade, bottom),
        },
    )