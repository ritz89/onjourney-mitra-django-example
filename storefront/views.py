from datetime import date

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from integrations.onjourney.adapters.demo import DemoClient
from integrations.onjourney.errors import (
    BookingValidationError,
    OperationConflict,
)
from storefront.forms import BookingForm
from storefront.services import BookingService


def _subject(request):
    return request.session.get("demo_subject")


def _login_redirect(request):
    login_url = reverse("demo_login")
    return redirect(f"{login_url}?next={request.get_full_path()}")


def health(request):
    return JsonResponse({"status": "ok", "mode": "demo"})


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


def invoice(request, booking_id):
    subject = _subject(request)
    if subject is None:
        return _login_redirect(request)
    booking = BookingService(client=DemoClient()).get_booking(booking_id, subject)
    if booking is None:
        raise Http404
    return render(request, "storefront/invoice.html", {"booking": booking})
