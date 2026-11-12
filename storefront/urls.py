from django.urls import path

from storefront import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("health/", views.health, name="health"),
    path("demo/login/", views.demo_login, name="demo_login"),
    path("demo/logout/", views.demo_logout, name="demo_logout"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("products/<int:product_id>/book/", views.booking_create, name="booking_create"),
    path("bookings/", views.booking_list, name="booking_list"),
    path("bookings/<uuid:booking_id>/invoice/", views.invoice, name="invoice"),
]
