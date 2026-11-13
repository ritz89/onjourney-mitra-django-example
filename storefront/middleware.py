from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.utils.cache import patch_cache_control


class DemoModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.ONJOURNEY_DEMO_MODE and request.path != reverse("health"):
            raise Http404

        response = self.get_response(request)
        if request.path.startswith(("/demo/", "/bookings/", "/payments/")):
            patch_cache_control(response, private=True, no_store=True)
        return response
