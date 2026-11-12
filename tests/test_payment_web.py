from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from django.urls import reverse

from integrations.onjourney.adapters.demo import DemoClient
from storefront.models import PaymentIntent
from storefront.services import BookingService


@pytest.fixture
def booking():
    return BookingService(client=DemoClient(today=date(2026, 11, 12))).create_booking(
        subject="demo-traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=uuid4(),
    )


@pytest.fixture
def demo_user(client):
    client.post(reverse("demo_login"))
    return client


def create_intent(client, booking, term=1):
    return client.post(
        reverse("payment_intent_create", args=[booking.id]),
        {
            "installment_number": str(term),
            "option_id": "9001",
            "operation_id": str(uuid4()),
        },
    )


@pytest.mark.django_db
def test_invoice_is_not_readable_by_another_subject(client, demo_user):
    other = BookingService(client=DemoClient(today=date(2026, 11, 12))).create_booking(
        subject="another-traveller",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=1,
        season_id=None,
        operation_id=uuid4(),
    )

    response = demo_user.get(reverse("invoice", args=[other.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_invoice_starts_with_dp_and_separates_product_and_fees(demo_user, booking):
    response = demo_user.get(reverse("invoice", args=[booking.id]))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Rp5.700.000" in content
    assert "Rp2.850.000" in content
    assert "Rp4.000" in content
    assert "Rp2.854.000" in content
    assert 'name="installment_number" value="1"' in content
    assert "termasuk PPN" in content
    assert "Belum lunas" in content


@pytest.mark.django_db
def test_payment_intent_shows_va_without_confirming_payment(demo_user, booking):
    response = create_intent(demo_user, booking)
    intent = PaymentIntent.objects.get()

    assert response.status_code == 302
    assert response.url == reverse("payment_pending", args=[intent.id])
    content = demo_user.get(response.url).content.decode()
    assert intent.va_code in content
    assert "Belum terbukti lunas" in content
    assert "Rp2.854.000" in content
    booking.refresh_from_db()
    assert booking.is_fully_paid is False


@pytest.mark.django_db
def test_double_intent_submission_creates_one_intent(demo_user, booking):
    operation_id = str(uuid4())
    payload = {
        "installment_number": "1",
        "option_id": "9001",
        "operation_id": operation_id,
    }

    first = demo_user.post(reverse("payment_intent_create", args=[booking.id]), payload)
    second = demo_user.post(reverse("payment_intent_create", args=[booking.id]), payload)

    assert PaymentIntent.objects.count() == 1
    assert first.url == second.url


@pytest.mark.django_db
def test_forged_browser_return_does_not_settle_intent(demo_user, booking):
    create_intent(demo_user, booking)
    intent = PaymentIntent.objects.get()

    response = demo_user.get(reverse("payment_return", args=[intent.id]), follow=True)

    intent.refresh_from_db()
    booking.refresh_from_db()
    assert intent.status == "accepted"
    assert booking.is_fully_paid is False
    assert "Belum lunas" in response.content.decode()


@pytest.mark.django_db
def test_provider_settlement_reconciles_partial_then_full_payment(demo_user, booking):
    create_intent(demo_user, booking)
    first = PaymentIntent.objects.get()
    response = demo_user.post(reverse("demo_payment_settle", args=[first.id]), follow=True)

    content = response.content.decode()
    assert "Belum lunas" in content
    assert "Rp2.850.000" in content
    booking.refresh_from_db()
    assert booking.paid_product_amount == Decimal("2850000.00")

    create_intent(demo_user, booking, term=2)
    second = PaymentIntent.objects.get(installment_number=2)
    response = demo_user.post(reverse("demo_payment_settle", args=[second.id]), follow=True)

    assert "Lunas" in response.content.decode()
    booking.refresh_from_db()
    assert booking.is_fully_paid is True


@pytest.mark.django_db
def test_manual_status_recovery_sets_last_checked_timestamp(demo_user, booking):
    response = demo_user.post(reverse("payment_status", args=[booking.id]), follow=True)

    booking.refresh_from_db()
    assert booking.last_status_check is not None
    assert "Terakhir diperiksa" in response.content.decode()


@pytest.mark.django_db
def test_seasonal_po_journey_reaches_full_payment_sequentially(demo_user):
    seasonal = BookingService(client=DemoClient(today=date(2026, 11, 12))).create_booking(
        subject="demo-traveller-1",
        product_id=201,
        start_at=None,
        guest_no=2,
        season_id=2001,
        operation_id=uuid4(),
    )

    create_intent(demo_user, seasonal, term=1)
    first = PaymentIntent.objects.get()
    assert first.amount == Decimal("2370000.00")
    demo_user.post(reverse("demo_payment_settle", args=[first.id]))
    seasonal.refresh_from_db()
    assert seasonal.is_fully_paid is False

    create_intent(demo_user, seasonal, term=2)
    second = PaymentIntent.objects.get(installment_number=2)
    assert second.amount == Decimal("5530000.00")
    response = demo_user.post(reverse("demo_payment_settle", args=[second.id]), follow=True)

    seasonal.refresh_from_db()
    assert seasonal.is_fully_paid is True
    assert "Lunas" in response.content.decode()
