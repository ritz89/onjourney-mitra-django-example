from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/images/favicon.svg")),
    path("", include("storefront.urls")),
]
