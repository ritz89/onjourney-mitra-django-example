from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.urls import reverse

from integrations.onjourney.adapters.demo import DemoClient
from integrations.onjourney.errors import BookingValidationError
from storefront.services import BookingService, PaymentService


def create_seasonal_booking():
    return BookingService(client=DemoClient(today=date(2026, 11, 12))).create_booking(
        subject="demo-traveller-1",
        product_id=201,
        start_at=None,
        guest_no=2,
        season_id=2001,
        operation_id=uuid4(),
    )


@pytest.mark.django_db
def test_paid_intent_url_redirects_to_invoice_instead_of_showing_pending(client):
    booking = create_seasonal_booking()
    intent = PaymentService(client=DemoClient(today=date(2026, 11, 12))).create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )
    PaymentService(client=DemoClient(today=date(2026, 11, 12))).settle_intent(intent)
    client.post(reverse("demo_login"))

    response = client.get(reverse("payment_pending", args=[intent.id]))

    assert response.status_code == 302
    assert response.url == reverse("invoice", args=[booking.id])


@pytest.mark.django_db
def test_new_intent_is_blocked_after_payment_completion_deadline():
    booking = create_seasonal_booking()
    service = PaymentService(client=DemoClient(today=date(2026, 11, 12)))

    with (
        patch("storefront.services.timezone.localdate", return_value=date(2027, 2, 2)),
        pytest.raises(BookingValidationError, match="pelunasan"),
    ):
        service.create_intent(
            booking=booking,
            installment_number=1,
            option_id=9001,
            operation_id=uuid4(),
        )


@pytest.mark.django_db
def test_existing_intent_can_settle_after_completion_deadline():
    booking = create_seasonal_booking()
    service = PaymentService(client=DemoClient(today=date(2026, 11, 12)))
    intent = service.create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )

    with patch("storefront.services.timezone.localdate", return_value=date(2027, 2, 2)):
        service.settle_intent(intent)

    intent.refresh_from_db()
    assert intent.status == "paid"


@pytest.mark.django_db
def test_demo_departures_are_generated_relative_to_the_demo_clock():
    client = DemoClient(today=date(2030, 1, 1))

    departure = client.list_departures(201)[0]

    assert departure["tour_date"] == "2030-04-03"
    assert departure["po_deadline"] > "2030-01-01"
    assert departure["payment_completion_deadline"] > departure["po_deadline"]
