from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from integrations.onjourney.adapters.demo import DemoClient
from integrations.onjourney.errors import BookingValidationError, OperationConflict
from storefront.models import BookingReference
from storefront.services import BookingService


@pytest.fixture
def client():
    return DemoClient()


@pytest.fixture
def service(client):
    return BookingService(client=client)


@pytest.mark.django_db
def test_catalog_contains_regular_and_seasonal_products(client):
    products = client.list_products()

    regular = client.get_product(101)
    seasonal = client.get_product(201)
    assert len(products) >= 2
    assert regular["is_seasonal"] is False
    assert isinstance(regular["price"], str)
    assert seasonal["is_seasonal"] is True
    assert client.list_departures(201)[0]["remaining"] > 0


@pytest.mark.django_db
def test_regular_booking_uses_decimal_product_total(service):
    booking = service.create_booking(
        subject="traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=uuid4(),
    )

    assert booking.total_price == Decimal("5700000.00")
    assert booking.terms[0]["amount"] == "2850000.00"
    assert booking.terms[0]["paid"] is False
    assert booking.is_fully_paid is False


@pytest.mark.django_db
def test_seasonal_booking_uses_selected_departure(service):
    booking = service.create_booking(
        subject="traveller-1",
        product_id=201,
        start_at=None,
        guest_no=2,
        season_id=2001,
        operation_id=uuid4(),
    )

    assert booking.start_at == date(2027, 2, 12)
    assert booking.season_id == 2001
    assert booking.terms[0]["amount"] < booking.terms[1]["amount"]


@pytest.mark.django_db
def test_repeated_operation_returns_original_booking(service):
    operation_id = uuid4()
    first = service.create_booking(
        subject="traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=operation_id,
    )
    second = service.create_booking(
        subject="traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=operation_id,
    )

    assert first.id == second.id
    assert BookingReference.objects.count() == 1


@pytest.mark.django_db
def test_repeated_seasonal_operation_returns_original_booking(service):
    operation_id = uuid4()
    first = service.create_booking(
        subject="traveller-1",
        product_id=201,
        start_at=None,
        guest_no=2,
        season_id=2001,
        operation_id=operation_id,
    )
    second = service.create_booking(
        subject="traveller-1",
        product_id=201,
        start_at=None,
        guest_no=2,
        season_id=2001,
        operation_id=operation_id,
    )

    assert first.id == second.id
    assert BookingReference.objects.count() == 1


@pytest.mark.django_db
def test_operation_id_cannot_be_reused_with_changed_payload(service):
    operation_id = uuid4()
    service.create_booking(
        subject="traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=operation_id,
    )

    with pytest.raises(OperationConflict):
        service.create_booking(
            subject="traveller-1",
            product_id=101,
            start_at=date(2027, 1, 15),
            guest_no=3,
            season_id=None,
            operation_id=operation_id,
        )


@pytest.mark.django_db
def test_booking_history_is_limited_to_current_subject(service):
    owned = service.create_booking(
        subject="traveller-1",
        product_id=101,
        start_at=date(2027, 1, 15),
        guest_no=2,
        season_id=None,
        operation_id=uuid4(),
    )
    service.create_booking(
        subject="traveller-2",
        product_id=101,
        start_at=date(2027, 1, 16),
        guest_no=1,
        season_id=None,
        operation_id=uuid4(),
    )

    assert list(service.list_bookings("traveller-1")) == [owned]
    assert service.get_booking(owned.id, "traveller-2") is None


@pytest.mark.django_db
def test_departure_rejects_more_guests_than_remaining(service):
    with pytest.raises(BookingValidationError, match="kuota"):
        service.create_booking(
            subject="traveller-1",
            product_id=201,
            start_at=None,
            guest_no=3,
            season_id=2002,
            operation_id=uuid4(),
        )
