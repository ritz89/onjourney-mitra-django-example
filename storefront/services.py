import hashlib
import json
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from integrations.onjourney.errors import (
    BookingValidationError,
    OperationConflict,
    PaymentSequenceError,
)
from storefront.models import BookingReference, PaymentIntent


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"))


def _payload_hash(subject, product_id, start_at, guest_no, season_id):
    payload = {
        "subject": subject,
        "product_id": product_id,
        "start_at": start_at.isoformat() if start_at else None,
        "guest_no": guest_no,
        "season_id": season_id,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _terms(product, total_price):
    terms = []
    allocated = Decimal("0.00")
    percentages = product["payment_term_percentages"]
    for index, percentage in enumerate(percentages, start=1):
        if index == len(percentages):
            amount = total_price - allocated
        else:
            amount = _money(total_price * Decimal(percentage) / Decimal("100"))
            allocated += amount
        terms.append({"number": index, "amount": format(amount, ".2f"), "paid": False})
    return terms


class BookingService:
    def __init__(self, client):
        self.client = client

    def list_bookings(self, subject):
        return BookingReference.objects.filter(subject=subject, tenant_slug="nusantara-journeys")

    def get_booking(self, booking_id, subject):
        return BookingReference.objects.filter(
            id=booking_id,
            subject=subject,
            tenant_slug="nusantara-journeys",
        ).first()

    def create_booking(self, *, subject, product_id, start_at, guest_no, season_id, operation_id):
        payload_hash = _payload_hash(subject, product_id, start_at, guest_no, season_id)
        existing = BookingReference.objects.filter(operation_id=operation_id).first()
        if existing is not None:
            if existing.payload_hash != payload_hash:
                raise OperationConflict("Operation ID sudah digunakan untuk data yang berbeda.")
            return existing

        try:
            product = self.client.get_product(product_id)
        except KeyError as exc:
            raise BookingValidationError("Paket tidak ditemukan.") from exc
        if not 1 <= guest_no <= product["capacity"]:
            raise BookingValidationError("Jumlah tamu tidak sesuai kapasitas paket.")

        if product["is_seasonal"]:
            departure = self.client.get_departure(product_id, season_id)
            if departure is None:
                raise BookingValidationError("Pilih jadwal keberangkatan yang tersedia.")
            if guest_no > departure["remaining"]:
                raise BookingValidationError("Jumlah tamu melebihi kuota yang tersisa.")
            today = timezone.localdate()
            if departure["po_deadline"] < today.isoformat():
                raise BookingValidationError("Batas waktu pemesanan awal telah berakhir.")
            if departure["payment_completion_deadline"] < today.isoformat():
                raise BookingValidationError("Batas waktu pelunasan telah berakhir.")
            start_at = date.fromisoformat(departure["tour_date"])
        else:
            if season_id is not None:
                raise BookingValidationError("Paket reguler tidak memakai jadwal musiman.")
            if start_at is None or start_at < timezone.localdate():
                raise BookingValidationError("Pilih tanggal keberangkatan yang valid.")

        total_price = _money(Decimal(product["price"]) * guest_no)
        with transaction.atomic():
            booking = BookingReference.objects.create(
                operation_id=operation_id,
                payload_hash=payload_hash,
                subject=subject,
                product_id=product_id,
                product_name=product["name"],
                code=f"NJ-{operation_id.hex[:6].upper()}",
                start_at=start_at,
                guest_no=guest_no,
                total_price=total_price,
                terms=_terms(product, total_price),
                season_id=season_id,
            )
        return booking


class PaymentService:
    def __init__(self, client):
        self.client = client

    def create_intent(self, *, booking, installment_number, option_id, operation_id):
        existing_operation = PaymentIntent.objects.filter(operation_id=operation_id).first()
        if existing_operation is not None:
            if (
                existing_operation.booking_id != booking.id
                or existing_operation.installment_number != installment_number
                or existing_operation.option_id != option_id
            ):
                raise OperationConflict("Operation ID pembayaran sudah digunakan.")
            return existing_operation

        if option_id != 9001:
            raise BookingValidationError("Metode pembayaran demo tidak dikenal.")
        next_term = booking.next_term
        if next_term is None or next_term["number"] != installment_number:
            raise PaymentSequenceError("Bayar termin yang belum lunas secara berurutan.")

        existing_term = PaymentIntent.objects.filter(
            booking=booking,
            installment_number=installment_number,
        ).first()
        if existing_term is not None:
            return existing_term

        if booking.season_id is not None:
            departure = self.client.get_departure(booking.product_id, booking.season_id)
            if (
                departure is None
                or departure["payment_completion_deadline"] < timezone.localdate().isoformat()
            ):
                raise BookingValidationError("Batas waktu pelunasan telah berakhir.")

        amount = Decimal(next_term["amount"])
        return PaymentIntent.objects.create(
            booking=booking,
            operation_id=operation_id,
            installment_number=installment_number,
            option_id=option_id,
            amount=amount,
            fee=Decimal("4000.00"),
            status="accepted",
            va_code=f"DEMO{operation_id.int % 10**12:012d}",
        )

    def settle_intent(self, intent):
        if intent.status == "paid":
            return intent
        if intent.status not in {"accepted", "action_required"}:
            raise BookingValidationError("Intent pembayaran tidak dapat diselesaikan.")

        with transaction.atomic():
            now = timezone.now()
            intent.status = "paid"
            intent.paid_at = now
            intent.save(update_fields=["status", "paid_at"])
            terms = [dict(term) for term in intent.booking.terms]
            terms[intent.installment_number - 1]["paid"] = True
            intent.booking.terms = terms
            intent.booking.save(update_fields=["terms"])
        return intent

    def get_status(self, booking):
        checked_at = timezone.now()
        booking.last_status_check = checked_at
        booking.save(update_fields=["last_status_check"])
        paid_fee_amount = sum(
            (intent.fee for intent in booking.payment_intents.filter(status="paid")),
            Decimal("0.00"),
        )
        return {
            "booking_id": booking.id,
            "status": "paid" if booking.is_fully_paid else "pending",
            "currency": booking.currency,
            "product_price": booking.total_price,
            "paid_product_amount": booking.paid_product_amount,
            "paid_fee_amount": paid_fee_amount,
            "remaining_product_amount": booking.remaining_product_amount,
            "checked_at": checked_at,
        }
