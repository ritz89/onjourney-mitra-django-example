import uuid
from decimal import Decimal

from django.db import models


class BookingReference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation_id = models.UUIDField(unique=True)
    payload_hash = models.CharField(max_length=64)
    tenant_slug = models.SlugField(default="nusantara-journeys")
    subject = models.CharField(max_length=100, db_index=True)
    product_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    start_at = models.DateField()
    guest_no = models.PositiveSmallIntegerField()
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="IDR")
    terms = models.JSONField()
    season_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_status_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def paid_product_amount(self):
        return sum(
            (Decimal(term["amount"]) for term in self.terms if term["paid"]),
            Decimal("0.00"),
        )

    @property
    def remaining_product_amount(self):
        return self.total_price - self.paid_product_amount

    @property
    def is_fully_paid(self):
        return bool(self.terms) and all(term["paid"] for term in self.terms)

    @property
    def next_term(self):
        return next((term for term in self.terms if not term["paid"]), None)

    @property
    def invoice_number(self):
        return f"INV-DEMO-{self.code}"


class PaymentIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(
        BookingReference,
        on_delete=models.CASCADE,
        related_name="payment_intents",
    )
    operation_id = models.UUIDField(unique=True)
    installment_number = models.PositiveSmallIntegerField()
    option_id = models.PositiveIntegerField()
    channel = models.CharField(max_length=30, default="virtual_account")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    fee = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, default="accepted")
    va_code = models.CharField(max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "installment_number"],
                name="unique_booking_installment_intent",
            )
        ]

    @property
    def total_amount(self):
        return self.amount + self.fee
