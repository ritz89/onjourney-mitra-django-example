from django.urls import path

from storefront import views

urlpatterns = [
    path("health/", views.health, name="health"),
]
