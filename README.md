# OnJourney Mitra Django Example — POC

A credential-free proof of concept for a **Mitra-owned traveller storefront** using the shape of the OnJourney External Tenant API. The sample partner is the fictional **Nusantara Journeys**.

This is a vertical slice of the OnJourney Mitra External API delivery plan, not the completed public integration template. It demonstrates:

- Partner-branded catalogue with regular and seasonal products.
- Departure quota, PO deadline, and payment-completion deadline.
- Simulated traveller sign-in with a database-backed session.
- Owned booking creation with stable idempotency IDs.
- Invoice with separate product, paid-product, remaining-product, and fee amounts.
- Sequential DP/PO and settlement payments through a simulated Virtual Account provider.
- Manual payment-status recovery and local booking history.

## Quickstart: local Python

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/). No OnJourney credentials, private repository, Node.js, or database server is needed.

```bash
uv sync --frozen
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000>. The persistent banner confirms that every record and payment is synthetic.

## Quickstart: Docker Compose

```bash
docker compose up --build
```

Open <http://127.0.0.1:8000>. Compose binds only to localhost and the container runs as an unprivileged user. The `demo_data` volume keeps the SQLite database across container recreation. Stop with `docker compose down`; remove that volume only when intentionally resetting demo data. The development server and shared identity are for local demonstration only.

## Guided demo

### Regular package and DP

1. Open **Bali Timur: Pesisir & Desa** and choose **Pesan paket ini**.
2. Continue as **Wisatawan Demo**. No password is requested.
3. Select a future departure date and guest count, then create the booking.
4. The invoice starts with **DP 50%**, not the later installment. The current payment is the term plus one VAT-inclusive demo service fee.
5. Create the Virtual Account intent. `accepted` does **not** mean paid.
6. Open the provider simulator and choose **Simulasikan pembayaran berhasil**.
7. Return to the invoice: the first term is paid, the invoice remains **Belum lunas**.
8. Pay the second term and repeat settlement: the invoice becomes **Lunas**.

### Seasonal package and PO

1. Open **Open Trip Labuan Bajo**.
2. Choose a listed departure; its date, remaining seats, PO deadline, and completion deadline come from the demo adapter.
3. Create the booking and pay **PO 30%**, then the **70%** balance in sequence. New intents are blocked after the completion deadline; a provider settlement for an intent created before that deadline is still recorded.
4. Use **Periksa status terbaru** to refresh the authoritative demo payment state and timestamp.

Demo departures and deadlines are generated relative to the current date, so the walkthrough remains usable in future checkouts. Tests inject a fixed demo clock.

**Perjalanan saya** lists only bookings created by the current demo subject on this installation. It is not a complete OnJourney history.

## Verification

```bash
uv run pytest -q
uv run ruff check .
uv run python manage.py check
```

The suite covers catalogue rendering, session safety, return-URL validation, regular/seasonal booking, quota and ownership boundaries, idempotent writes, DP-first sequencing, fee calculations, partial/full settlement, forged browser returns, and local assets.

## Architecture documentation

- `docs/architecture.md`: POC components and integration boundaries.
- `docs/integration-flow.md`: Current and target architectures, Mermaid sequence diagrams, authentication, booking, payment, reconciliation, recovery, and failure handling.
- `docs/api-coverage.md`: Demo capabilities and explicit live-integration gaps.

## Project map

```text
config/settings/             Demo, test, and guarded production settings
integrations/onjourney/      Synthetic adapter and typed integration errors
storefront/                  Views, forms, models, services, and URLs
templates/                   Server-rendered Indonesian storefront
static/                      Local CSS, JavaScript, and SVG illustrations
tests/                       Domain and HTTP integration tests
docs/                        Architecture and explicit API coverage
```

Change partner copy, colours, products, and departures in `integrations/onjourney/adapters/demo.py`, `templates/`, and `static/css/app.css`. Financial rules remain in `storefront/services.py`, not in templates.

## Explicit POC limits

- No live API calls, OIDC tokens, response signatures, webhooks, SSE, or real charges.
- No real payment-option discovery or claim of deployed API compatibility.
- SQLite and the demo provider are not production concurrency or security models.
- Production settings reject demo mode, but this POC is not production-ready.
- Test-tenant validation and deployment remain release decisions.

See `docs/architecture.md` and `docs/api-coverage.md` before starting a live adapter.

## License

Code is available under the MIT License. The license does not grant OnJourney trademark rights, hosted API access, payment-provider access, or production credentials.
