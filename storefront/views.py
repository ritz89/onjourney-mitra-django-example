import uuid
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from integrations.onjourney.adapters.demo import DemoClient
from integrations.onjourney.errors import (
    BookingValidationError,
    OperationConflict,
    PaymentSequenceError,
)
from storefront.forms import BookingForm
from storefront.models import PaymentIntent
from storefront.services import BookingService, PaymentService


def _subject(request):
    return request.session.get("demo_subject")


def _login_redirect(request):
    login_url = reverse("demo_login")
    return redirect(f"{login_url}?next={request.get_full_path()}")


def health(request):
    mode = "demo" if settings.ONJOURNEY_DEMO_MODE else "disabled"
    return JsonResponse({"status": "ok", "mode": mode})


def catalog(request):
    return render(
        request,
        "storefront/catalog.html",
        {"products": DemoClient().list_products()},
    )


def product_detail(request, product_id):
    client = DemoClient()
    try:
        product = client.get_product(product_id)
    except KeyError as exc:
        raise Http404 from exc
    departures = client.list_departures(product_id)
    for departure in departures:
        for field in ("tour_date", "po_deadline", "payment_completion_deadline"):
            departure[field] = date.fromisoformat(departure[field])
    return render(
        request,
        "storefront/product_detail.html",
        {"product": product, "departures": departures},
    )


@require_http_methods(["GET", "POST"])
def demo_login(request):
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("catalog")
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("catalog")
    if request.method == "POST":
        request.session.cycle_key()
        request.session["demo_subject"] = "demo-traveller-1"
        request.session["demo_name"] = "Wisatawan Demo"
        return redirect(next_url)
    return render(request, "storefront/login.html", {"next_url": next_url})


@require_POST
def demo_logout(request):
    request.session.flush()
    return redirect("catalog")


@require_http_methods(["GET", "POST"])
def booking_create(request, product_id):
    subject = _subject(request)
    if subject is None:
        return _login_redirect(request)
    client = DemoClient()
    try:
        product = client.get_product(product_id)
    except KeyError as exc:
        raise Http404 from exc
    departures = client.list_departures(product_id)
    form = BookingForm(
        request.POST or None,
        product=product,
        departures=departures,
    )
    if request.method == "POST" and form.is_valid():
        try:
            booking = BookingService(client=client).create_booking(
                subject=subject,
                product_id=product_id,
                start_at=form.cleaned_data.get("start_at"),
                guest_no=form.cleaned_data["guest_no"],
                season_id=(
                    int(form.cleaned_data["season_id"])
                    if form.cleaned_data.get("season_id")
                    else None
                ),
                operation_id=form.cleaned_data["operation_id"],
            )
        except (BookingValidationError, OperationConflict) as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("invoice", booking_id=booking.id)
    return render(
        request,
        "storefront/booking_form.html",
        {"product": product, "form": form},
    )


def booking_list(request):
    subject = _subject(request)
    if subject is None:
        return _login_redirect(request)
    bookings = BookingService(client=DemoClient()).list_bookings(subject)
    return render(request, "storefront/booking_list.html", {"bookings": bookings})


def _owned_booking_or_404(request, booking_id):
    booking = BookingService(client=DemoClient()).get_booking(booking_id, _subject(request))
    if booking is None:
        raise Http404
    return booking


def _owned_intent_or_404(request, intent_id):
    intent = PaymentIntent.objects.filter(
        id=intent_id,
        booking__subject=_subject(request),
        booking__tenant_slug="nusantara-journeys",
    ).select_related("booking").first()
    if intent is None:
        raise Http404
    return intent


def _invoice_context(booking):
    next_term = booking.next_term
    pending_intent = None
    if next_term is not None:
        pending_intent = booking.payment_intents.filter(
            installment_number=next_term["number"],
            status__in=["accepted", "action_required"],
        ).first()
    paid_fee_amount = sum(
        (intent.fee for intent in booking.payment_intents.filter(status="paid")),
        Decimal("0.00"),
    )
    return {
        "booking": booking,
        "next_term": next_term,
        "pending_intent": pending_intent,
        "next_total": Decimal(next_term["amount"]) + Decimal("4000") if next_term else None,
        "paid_fee_amount": paid_fee_amount,
        "operation_id": uuid.uuid4(),
    }


def invoice(request, booking_id):
    if _subject(request) is None:
        return _login_redirect(request)
    booking = _owned_booking_or_404(request, booking_id)
    return render(request, "storefront/invoice.html", _invoice_context(booking))


@require_POST
def payment_intent_create(request, booking_id):
    if _subject(request) is None:
        return _login_redirect(request)
    booking = _owned_booking_or_404(request, booking_id)
    try:
        installment_number = int(request.POST["installment_number"])
        option_id = int(request.POST["option_id"])
        operation_id = uuid.UUID(request.POST["operation_id"])
    except (KeyError, TypeError, ValueError):
        return HttpResponseBadRequest("Data pembayaran tidak lengkap atau tidak valid.")
    try:
        intent = PaymentService(client=DemoClient()).create_intent(
            booking=booking,
            installment_number=installment_number,
            option_id=option_id,
            operation_id=operation_id,
        )
    except (BookingValidationError, OperationConflict, PaymentSequenceError) as exc:
        messages.error(request, str(exc))
        return redirect("invoice", booking_id=booking.id)
    return redirect("payment_pending", intent_id=intent.id)


def payment_pending(request, intent_id):
    if _subject(request) is None:
        return _login_redirect(request)
    intent = _owned_intent_or_404(request, intent_id)
    if intent.status == "paid":
        return redirect("invoice", booking_id=intent.booking_id)
    return render(request, "storefront/payment_pending.html", {"intent": intent})


def demo_payment_provider(request, intent_id):
    if not settings.ONJOURNEY_DEMO_MODE:
        raise Http404
    if _subject(request) is None:
        return _login_redirect(request)
    intent = _owned_intent_or_404(request, intent_id)
    return render(request, "storefront/demo_payment_provider.html", {"intent": intent})


@require_POST
def demo_payment_settle(request, intent_id):
    if not settings.ONJOURNEY_DEMO_MODE:
        raise Http404
    if _subject(request) is None:
        return _login_redirect(request)
    intent = _owned_intent_or_404(request, intent_id)
    PaymentService(client=DemoClient()).settle_intent(intent)
    return redirect("payment_return", intent_id=intent.id)


def payment_return(request, intent_id):
    if _subject(request) is None:
        return _login_redirect(request)
    intent = _owned_intent_or_404(request, intent_id)
    PaymentService(client=DemoClient()).get_status(intent.booking)
    return redirect("invoice", booking_id=intent.booking_id)


@require_POST
def payment_status(request, booking_id):
    if _subject(request) is None:
        return _login_redirect(request)
    booking = _owned_booking_or_404(request, booking_id)
    PaymentService(client=DemoClient()).get_status(booking)
    messages.success(request, "Status pembayaran terbaru sudah diperiksa.")
    return redirect("invoice", booking_id=booking.id)
