from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@require_safe
@never_cache
def healthz(request):
    return HttpResponse("ok", content_type="text/plain")