from functools import wraps

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from shops.services import get_active_shop

from .services import get_frame_styles, get_shape, list_active_shapes

UNCLEAR_REASONS = {
    "no_face": _("We could not find a face in this photo."),
    "many_faces": _("We found more than one face in this photo."),
    "turned": _("Your head looks turned or tilted in this photo."),
    "small": _("Your face looks too small in the photo."),
    "cut_off": _("Part of your face is outside the photo."),
    "unreadable": _("We could not get a clear styling suggestion from this photo."),
    "unsupported": _("This phone cannot check photos."),
}


def sunglasses_page(view):
    """Hide the page when the switch is off. Find the shop. Else 404."""

    @wraps(view)
    def wrapper(request, shop_slug, *args, **kwargs):
        if not getattr(settings, "SUNGLASSES_ENABLED", False):
            raise Http404
        shop = get_active_shop(shop_slug)
        if shop is None:
            raise Http404
        return view(request, shop, *args, **kwargs)

    return wrapper


@sunglasses_page
def intro(request, shop):
    return render(request, "sunglasses/intro.html", {"shop": shop})


@sunglasses_page
def shapes(request, shop):
    return render(
        request,
        "sunglasses/shapes.html",
        {"shop": shop, "shapes": list_active_shapes()},
    )


@sunglasses_page
def shape_detail(request, shop, shape_slug):
    shape = get_shape(shape_slug)
    if shape is None:
        raise Http404
    also = get_shape(request.GET.get("also", ""))
    if also is not None and also.pk == shape.pk:
        also = None
    return render(
        request,
        "sunglasses/shape_detail.html",
        {
            "shop": shop,
            "shape": shape,
            "frames": get_frame_styles(shape),
            "also": also,
            "from_photo": request.GET.get("source") == "photo",
        },
    )


@sunglasses_page
def unclear(request, shop):
    reason = request.GET.get("reason", "")
    message = UNCLEAR_REASONS.get(reason, UNCLEAR_REASONS["unreadable"])
    return render(
        request,
        "sunglasses/unclear.html",
        {"shop": shop, "message": message},
    )