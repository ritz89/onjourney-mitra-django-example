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
    path(
        "bookings/<uuid:booking_id>/payment-intents/",
        views.payment_intent_create,
        name="payment_intent_create",
    ),
    path("bookings/<uuid:booking_id>/status/", views.payment_status, name="payment_status"),
    path("payments/<uuid:intent_id>/", views.payment_pending, name="payment_pending"),
    path("payments/<uuid:intent_id>/return/", views.payment_return, name="payment_return"),
    path(
        "demo/payments/<uuid:intent_id>/provider/",
        views.demo_payment_provider,
        name="demo_payment_provider",
    ),
    path(
        "demo/payments/<uuid:intent_id>/settle/",
        views.demo_payment_settle,
        name="demo_payment_settle",
    ),
]
