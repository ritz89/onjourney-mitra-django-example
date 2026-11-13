import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from django.test import override_settings
from django.urls import reverse

from integrations.onjourney.adapters.demo import DemoClient
from storefront.services import BookingService, PaymentService


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


@pytest.mark.django_db
@override_settings(ONJOURNEY_DEMO_MODE=False)
def test_production_mode_closes_demo_login_and_storefront(client, booking):
    assert client.post(reverse("demo_login")).status_code == 404
    assert "demo_subject" not in client.session
    assert client.get(reverse("catalog")).status_code == 404
    assert client.get(reverse("product_detail", args=[101])).status_code == 404
    assert client.get(reverse("booking_list")).status_code == 404
    assert client.get(reverse("invoice", args=[booking.id])).status_code == 404


@pytest.mark.django_db
def test_booking_and_invoice_pages_are_not_cacheable(client, booking):
    client.post(reverse("demo_login"))

    history = client.get(reverse("booking_list"))
    invoice = client.get(reverse("invoice", args=[booking.id]))

    assert "no-store" in history["Cache-Control"]
    assert "no-store" in invoice["Cache-Control"]


@pytest.mark.django_db
def test_payment_pages_are_not_cacheable(client, booking):
    client.post(reverse("demo_login"))
    intent = PaymentService(client=DemoClient(today=date(2026, 11, 12))).create_intent(
        booking=booking,
        installment_number=1,
        option_id=9001,
        operation_id=uuid4(),
    )

    pending = client.get(reverse("payment_pending", args=[intent.id]))
    provider = client.get(reverse("demo_payment_provider", args=[intent.id]))

    assert "no-store" in pending["Cache-Control"]
    assert "no-store" in provider["Cache-Control"]


def test_production_deploy_check_has_no_security_warnings():
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "ONJOURNEY_DEMO_MODE": "false",
            "SECRET_KEY": "test-only-7!kP2xR9vL4mQ8sN1cF6hJ3bG5dT0yW7zX2vB4nM8qK1",
            "ALLOWED_HOSTS": "mitra.example",
            "SQLITE_NAME": ":memory:",
        }
    )

    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_demo_container_is_local_only_and_unprivileged():
    root = Path(__file__).resolve().parent.parent
    compose = (root / "compose.yaml").read_text()
    dockerfile = (root / "Dockerfile").read_text()

    assert '"127.0.0.1:8000:8000"' in compose
    assert "\nUSER demo\n" in dockerfile
