from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from integrations.onjourney.adapters.demo import DemoClient
from integrations.onjourney.errors import BookingValidationError, PaymentSequenceError
from storefront.models import PaymentIntent
from storefront.services import BookingService, PaymentService


@pytest.fixture
def booking():
    return BookingService(client=DemoClient()).create_booking(
        subject="traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=uuid4(),
    )


@pytest.mark.django_db
def test_first_intent_pays_dp_with_one_vat_inclusive_fee(booking):
    intent = PaymentService().create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )

    assert intent.installment_number == 1
    assert intent.amount == Decimal("2850000.00")
    assert intent.fee == Decimal("4000.00")
    assert intent.total_amount == Decimal("2854000.00")
    assert intent.status == "accepted"
    booking.refresh_from_db()
    assert booking.is_fully_paid is False


@pytest.mark.django_db
def test_intent_cannot_skip_first_unpaid_term(booking):
    with pytest.raises(PaymentSequenceError):
        PaymentService().create_intent(
            booking=booking,
            installment_number=2,
            option_id=9001,
            operation_id=uuid4(),
        )


@pytest.mark.django_db
def test_repeated_payment_operation_returns_original_intent(booking):
    operation_id = uuid4()
    first = PaymentService().create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=operation_id,
    )
    second = PaymentService().create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=operation_id,
    )

    assert first.id == second.id
    assert PaymentIntent.objects.count() == 1


@pytest.mark.django_db
def test_new_operation_cannot_duplicate_active_term(booking):
    first = PaymentService().create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )
    second = PaymentService().create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )

    assert first.id == second.id
    assert PaymentIntent.objects.count() == 1


@pytest.mark.django_db
def test_unknown_payment_option_is_rejected(booking):
    with pytest.raises(BookingValidationError):
        PaymentService().create_intent(
            booking=booking,
            installment_number=1,
            option_id=9999,
            operation_id=uuid4(),
        )


@pytest.mark.django_db
def test_settlement_moves_from_partial_to_fully_paid(booking):
    service = PaymentService()
    first = service.create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )
    service.settle_intent(first)
    booking.refresh_from_db()

    assert booking.paid_product_amount == Decimal("2850000.00")
    assert booking.remaining_product_amount == Decimal("2850000.00")
    assert booking.is_fully_paid is False

    second = service.create_intent(
        booking=booking,
        installment_number=2,
        option_id=9001,
        operation_id=uuid4(),
    )
    service.settle_intent(second)
    booking.refresh_from_db()

    assert booking.paid_product_amount == booking.total_price
    assert booking.remaining_product_amount == Decimal("0.00")
    assert booking.is_fully_paid is True


@pytest.mark.django_db
def test_status_recovery_reports_authoritative_amounts_and_timestamp(booking):
    service = PaymentService()
    intent = service.create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )
    service.settle_intent(intent)

    status = service.get_status(booking)

    assert status["status"] == "pending"
    assert status["paid_product_amount"] == Decimal("2850000.00")
    assert status["paid_fee_amount"] == Decimal("4000.00")
    assert status["remaining_product_amount"] == Decimal("2850000.00")
    assert status["checked_at"] is not None
    booking.refresh_from_db()
    assert booking.last_status_check == status["checked_at"]
