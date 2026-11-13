from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.urls import reverse

from integrations.onjourney.adapters.demo import DemoClient
from storefront.models import BookingReference


@pytest.fixture
def demo_user(client):
    response = client.post(reverse("demo_login"))
    assert response.status_code == 302
    return client


@pytest.mark.django_db
def test_catalog_uses_partner_brand_and_product_cards(client):
    response = client.get(reverse("catalog"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Nusantara Journeys" in content
    assert "Bali Timur: Pesisir &amp; Desa" in content
    assert "Open Trip Labuan Bajo" in content
    assert "Rp2.850.000" in content
    assert "MODE DEMO" in content


@pytest.mark.django_db
def test_seasonal_detail_shows_real_departure_fields(client):
    with patch(
        "storefront.views.DemoClient",
        side_effect=lambda: DemoClient(today=date(2026, 11, 12)),
    ):
        response = client.get(reverse("product_detail", args=[201]))

    assert response.status_code == 200
    content = response.content.decode()
    assert "12 Februari 2027" in content
    assert "8 kursi tersisa" in content
    assert "Batas PO" in content
    assert "Batas pelunasan" in content


@pytest.mark.django_db
def test_demo_login_rotates_session_without_token_material(client):
    client.get(reverse("catalog"))
    old_key = client.session.session_key

    response = client.post(reverse("demo_login"), {"next": "/products/101/book/"})

    assert response.status_code == 302
    assert response.url == "/products/101/book/"
    assert client.session.session_key != old_key
    assert client.session["demo_subject"] == "demo-traveller-1"
    assert "access_token" not in client.session
    assert "refresh_token" not in client.session
    assert response.cookies["sessionid"]["httponly"]


@pytest.mark.django_db
def test_demo_login_rejects_external_return_url(client):
    response = client.post(reverse("demo_login"), {"next": "https://malicious.example"})

    assert response.status_code == 302
    assert response.url == reverse("catalog")


@pytest.mark.django_db
def test_booking_requires_simulated_sign_in(client):
    response = client.get(reverse("booking_create", args=[101]))

    assert response.status_code == 302
    assert reverse("demo_login") in response.url


@pytest.mark.django_db
def test_booking_form_and_review_are_accessible(demo_user):
    response = demo_user.get(reverse("booking_create", args=[101]))

    assert response.status_code == 200
    content = response.content.decode()
    assert '<label for="id_start_at"' in content
    assert '<label for="id_guest_no"' in content
    assert 'name="operation_id"' in content
    assert "Ringkasan pesanan" in content


@pytest.mark.django_db
def test_regular_booking_submission_redirects_to_owned_invoice(demo_user):
    response = demo_user.post(
        reverse("booking_create", args=[101]),
        {
            "start_at": "2027-01-15",
            "guest_no": "2",
            "operation_id": str(uuid4()),
        },
    )

    booking = BookingReference.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("invoice", args=[booking.id])
    assert booking.subject == "demo-traveller-1"


@pytest.mark.django_db
def test_double_booking_submission_creates_one_record(demo_user):
    operation_id = str(uuid4())
    payload = {
        "start_at": "2027-01-15",
        "guest_no": "2",
        "operation_id": operation_id,
    }

    first = demo_user.post(reverse("booking_create", args=[101]), payload)
    second = demo_user.post(reverse("booking_create", args=[101]), payload)

    assert BookingReference.objects.count() == 1
    assert first.url == second.url


@pytest.mark.django_db
def test_seasonal_booking_submission_uses_departure(demo_user):
    with patch(
        "storefront.views.DemoClient",
        side_effect=lambda: DemoClient(today=date(2026, 11, 12)),
    ):
        response = demo_user.post(
            reverse("booking_create", args=[201]),
            {
                "season_id": "2001",
                "guest_no": "2",
                "operation_id": str(uuid4()),
            },
        )

    booking = BookingReference.objects.get()
    assert response.status_code == 302
    assert booking.season_id == 2001
    assert booking.start_at.isoformat() == "2027-02-12"


@pytest.mark.django_db
def test_unavailable_departure_redisplays_form_with_error(demo_user):
    response = demo_user.post(
        reverse("booking_create", args=[201]),
        {
            "season_id": "2002",
            "guest_no": "3",
            "operation_id": str(uuid4()),
        },
    )

    assert response.status_code == 200
    assert "kuota" in response.content.decode()


@pytest.mark.django_db
def test_history_only_lists_bookings_created_by_current_demo_subject(demo_user):
    demo_user.post(
        reverse("booking_create", args=[101]),
        {
            "start_at": "2027-01-15",
            "guest_no": "2",
            "operation_id": str(uuid4()),
        },
    )

    response = demo_user.get(reverse("booking_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Bali Timur: Pesisir &amp; Desa" in content
    assert "hanya booking yang dibuat" in content
