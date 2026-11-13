# Integration flow architecture

This document describes the integration architecture of the OnJourney Mitra Django example. It distinguishes the **implemented credential-free POC** from the **target live integration**. Target diagrams are design guidance, not claims of deployed compatibility.

## 1. Scope and authority

The application is a backend-for-frontend (BFF) for one Mitra-owned traveller storefront. OnJourney is intended to remain the authority for traveller identity, catalogue, availability, bookings, invoices, and payment state. Local records support browser sessions, ownership, idempotency, and reconciliation; they are not a second booking engine.

The current repository implements the following flow entirely with synthetic data:

```text
Catalogue → simulated sign-in → booking → invoice → payment intent
          → simulated provider settlement → status recovery → partial or fully paid invoice
```

Not implemented: live HTTP transport, hosted OIDC, encrypted traveller tokens, response-signature verification, webhooks/SSE, PostgreSQL concurrency, real payment discovery, or real charges. See `api-coverage.md` for the capability matrix.

## 2. Implemented POC architecture

```mermaid
flowchart LR
    T[Traveller] --> B[Browser]

    subgraph Django[Django backend-for-frontend]
        M[DemoModeMiddleware]
        V[Views and forms]
        S[BookingService and PaymentService]
        M --> V --> S
    end

    A[DemoClient adapter]
    P[Demo payment provider]
    D[(SQLite)]

    B -->|Opaque session cookie and CSRF| M
    S --> A
    S --> D
    B -->|Settlement simulation only| P
    P -->|POST settle| V
    A -->|Synthetic tenant, products and departures| V
```

### Component responsibilities

| Component | Responsibility | Main files |
| --- | --- | --- |
| Browser | Renders server-generated HTML and holds only the local session cookie. Never receives tenant credentials or traveller tokens. | `templates/`, `static/` |
| Demo mode middleware | Closes the storefront when demo mode is disabled and applies private/no-store headers to demo, booking, and payment paths. | `storefront/middleware.py` |
| Views and forms | Validate input, safe return URLs, CSRF-protected writes, and ownership checks. | `storefront/views.py`, `storefront/forms.py` |
| Application services | Own booking/payment rules, Decimal arithmetic, sequential terms, idempotency, deadlines, settlement, and status reads. | `storefront/services.py` |
| Demo adapter | Supplies synthetic tenant, product, and relative-date departure contracts without upstream calls. | `integrations/onjourney/adapters/demo.py` |
| Local models | Bind booking references to tenant and demo subject, retain operation IDs and payload hashes, and persist intents and payment terms. | `storefront/models.py` |
| Demo provider | Simulates provider settlement. It never handles money and is unavailable when demo mode is disabled. | `storefront/views.py`, `templates/storefront/demo_payment_provider.html` |

### Local data boundaries

- `BookingReference.subject` and `tenant_slug` scope every booking read. A UUID alone does not grant access.
- `operation_id` and `payload_hash` make booking creation replay-safe. Reusing an operation with a changed payload raises a conflict.
- A payment intent has a unique operation ID and a unique booking/installment pair. Repeated submissions cannot create a second intent for the same term.
- Booking terms store decimal-string amounts and paid flags. Product-paid, remaining-product, and fee-paid amounts remain separate.
- Authenticated pages use private/no-store cache headers. Production mode closes all demo routes except `/health/`.

## 3. Current demo sequence

### 3.1 Catalogue, simulated identity, and booking

```mermaid
sequenceDiagram
    autonumber
    actor T as Traveller
    participant B as Browser
    participant D as Django BFF
    participant A as DemoClient
    participant DB as SQLite

    T->>B: Open catalogue
    B->>D: GET /
    D->>A: list_products()
    A-->>D: Synthetic regular and seasonal products
    D-->>B: Server-rendered catalogue

    T->>B: Choose seasonal product
    B->>D: GET /products/{id}/
    D->>A: get_product() and list_departures()
    A-->>D: Product, quota, PO and completion deadlines
    D-->>B: Product detail and departure choices

    T->>B: Book package
    B->>D: GET /products/{id}/book/
    D-->>B: Redirect to demo login when no subject exists
    T->>B: Continue as demo traveller
    B->>D: POST /demo/login/
    D->>D: Rotate session and set demo-traveller-1
    D-->>B: Local session cookie only

    B->>D: GET booking form
    D-->>B: Form with a new operation_id
    T->>B: Submit date or departure and guests
    B->>D: POST booking with operation_id
    D->>A: Validate product and departure
    D->>D: Validate guest count, quota and deadlines
    D->>DB: Read existing operation_id

    alt Same operation and payload
        DB-->>D: Original booking reference
        D-->>B: Redirect to the same invoice
    else No completed operation
        D->>DB: Create tenant/subject-owned booking and terms
        D-->>B: Redirect to owned invoice
    else Same operation with changed payload
        D-->>B: Reject with operation conflict
    end
```

The local history page lists only bookings created by the current demo subject on this installation. It is not a complete OnJourney history.

### 3.2 Intent, simulated settlement, and return

```mermaid
sequenceDiagram
    autonumber
    actor T as Traveller
    participant B as Browser
    participant D as Django BFF
    participant DB as SQLite
    participant P as Demo provider

    T->>B: Open invoice
    B->>D: GET /bookings/{uuid}/invoice/
    D->>DB: Read booking by UUID, tenant and subject
    D-->>B: Terms and first unpaid DP or PO term

    T->>B: Choose Virtual Account
    B->>D: POST payment intent with operation_id
    D->>DB: Find the first unpaid term and existing intent
    D->>D: Check payment-completion deadline
    D->>DB: Persist accepted intent and demo VA
    D-->>B: Payment instructions
    Note over B,DB: accepted or action_required does not mean paid

    T->>B: Open provider simulator
    B->>P: View synthetic VA and amount
    T->>P: Simulate successful payment
    P->>D: POST /demo/payments/{uuid}/settle/
    D->>DB: Atomically mark intent and its term paid
    D-->>B: Redirect to payment return

    B->>D: GET /payments/{uuid}/return/
    D->>DB: Read authoritative demo payment state and save check timestamp
    D-->>B: Redirect to invoice

    alt More unpaid terms remain
        D-->>B: Invoice shows Belum lunas and next term
    else Every term is paid
        D-->>B: Invoice shows Lunas
    end
```

A direct or forged browser return cannot mark an intent paid. Only the provider-simulation route changes settlement state. Revisiting a paid intent redirects to its invoice instead of displaying stale pending instructions.

## 4. Target live architecture

The following components are required before enabling a live adapter. They do not exist in the current POC.

```mermaid
flowchart LR
    B[Traveller browser] -->|Local session and CSRF| D[Django BFF]
    B -->|Hosted authorization and consent| O[OnJourney OIDC]
    O -->|Single-use authorization code| D
    D -->|Tenant key and traveller token| A[External Tenant API]
    A -->|Signed HTTP responses| D
    A -->|Signed webhook| W[Verified durable inbox]
    W --> R[Database-backed reconciliation worker]
    R --> A
    D --> L[(PostgreSQL)]
    W --> L
    R --> L
```

### Required security boundaries

| Secret or authority | Allowed location | Browser exposure |
| --- | --- | --- |
| Tenant API key | Backend secret manager, scoped to the installation | Never |
| OIDC client secret | Backend secret manager | Never |
| Traveller access/refresh token | Encrypted server-side token session with refresh locking | Never |
| External API response-signing keys | Backend trust store with approved initial pins | Public keys only, never private keys |
| Raw event-stream ticket | Server-held, one-use, short-lived connection state | Never |
| Local browser session | Opaque, rotated, HttpOnly, Secure, SameSite=Lax cookie in deployment | Session cookie only |
| Payment status | Signed API response or verified webhook followed by reconciliation | Derived display state only |

The OIDC signing keys and External API response-signing keys are separate trust domains. Production startup must fail for missing encryption keys, trust pins, or unsafe origins. Demo settings and synthetic identity must remain disabled.

## 5. Target hosted authentication sequence

```mermaid
sequenceDiagram
    autonumber
    actor T as Traveller
    participant B as Browser
    participant D as Django BFF
    participant O as OnJourney OIDC
    participant DB as Token session store

    T->>B: Sign in
    B->>D: Start hosted authorization
    D->>D: Generate state, nonce and S256 PKCE verifier
    D-->>B: Redirect to /external-auth/v1/authorize
    B->>O: Authorization request with exact redirect URI
    O-->>T: Hosted login or signup and consent
    O-->>B: Single-use code and state
    B->>D: OIDC callback with code and state
    D->>D: Reject mismatched or replayed state
    D->>O: Exchange code with client credentials and PKCE verifier
    O-->>D: ID token, access token and rotating refresh token
    D->>D: Validate issuer, audience, signature, times, nonce and azp
    D->>DB: Store encrypted credentials and bind tenant plus subject
    D-->>B: Rotate local session and redirect to a safe local path

    Note over D,DB: Refresh is locked per session and rotation is persisted atomically
```

Logout must revoke supported upstream credentials without relying on upstream availability to clear the local session. `invalid_grant` during refresh expires the local session safely; concurrent refresh requests must not lose the rotated token.

## 6. Target catalogue and booking sequence

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant D as Django BFF
    participant A as External Tenant API
    participant DB as PostgreSQL

    B->>D: Open product and departure
    D->>A: GET products/{id} and departures
    A-->>D: Signed response
    D->>D: Verify raw body, signature, status, target URI and timestamps
    D-->>B: Display only supplied product and availability fields

    B->>D: Submit supported booking fields and operation_id
    D->>DB: Persist operation intent and payload fingerprint
    D->>A: POST bookings with tenant and traveller authorization
    Note over D,A: Reuse the original Idempotency-Key and exact payload

    alt Verified created response
        A-->>D: Signed booking UUID, code, total and invoice reference
        D->>DB: Persist owned booking reference and completed operation
        D-->>B: Redirect to invoice
    else Ambiguous timeout or unavailable upstream
        D->>DB: Retain original operation and payload
        D->>A: Retry the same operation conservatively
        A-->>D: Original result or in-progress/conflict classification
        D-->>B: Show safe recovery state, never create a new booking
    else Verified validation or entitlement error
        D-->>B: Display the safe mapped error without changing booking state
    end
```

Only contract-supported booking fields may be sent. Quota, PO eligibility, guest requirements, and deadlines must be revalidated upstream at write time. Local validation improves UX but is not the authority.

## 7. Target payment and reconciliation sequence

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant D as Django BFF
    participant A as External Tenant API
    participant P as Payment provider
    participant DB as PostgreSQL
    participant W as Reconciliation worker

    B->>D: Open owned invoice
    D->>A: GET booking, invoice and payment-schemes
    A-->>D: Signed invoice and supported terms
    D->>D: Verify responses and identify the first eligible unpaid term
    D-->>B: Product amounts, fees and current payable term

    B->>D: Confirm method and current term
    D->>A: POST payment-intents with original operation key
    A-->>D: Signed accepted or action_required intent
    D->>D: Validate provider error code and safe action fields

    alt Virtual Account or QR action
        D-->>B: Display only the channel and action created by this intent
    else Wallet action
        D-->>B: Open an errCode=0 HTTPS mobilePayUrl
    end
    Note over B,D: HTTP 200, accepted and action_required are not settlement

    P-->>A: Provider payment notification
    A-->>D: Signed webhook delivery
    D->>D: Verify exact public target URI and raw request bytes
    D->>DB: Commit unique receipt and reconciliation job atomically
    D-->>A: Acknowledge durable acceptance

    W->>A: GET payment-status for the owned booking
    A-->>W: Signed authoritative payment state
    W->>DB: Reconcile without allowing an older event to downgrade paid state
    B->>D: Reopen owned invoice
    D->>DB: Read the reconciled booking and invoice state
    D-->>B: Show verified partial or fully paid state
```

Payment-option discovery and scheme-confirmation semantics remain contract gates. The POC's configured VA option must not be presented as proof that general live discovery works.

## 8. Browser return and manual recovery

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant D as Django BFF
    participant A as External Tenant API
    participant DB as PostgreSQL

    B->>D: Return from payment action or request manual refresh
    Note over B,D: The return itself never marks the booking paid
    D->>A: GET bookings/{uuid}/payment-status
    A-->>D: Signed authoritative status
    D->>D: Verify response before using any fields
    D->>DB: Save verified state and last-check timestamp

    alt Paid
        D-->>B: Show fully paid invoice and stop polling
    else Pending or action required
        D-->>B: Preserve pending instructions and bounded retry policy
    else Unverified or temporarily unavailable
        D-->>B: Keep the last verified state and show a safe recovery message
    end
```

A production reconciliation policy should combine webhooks with manual refresh and a capped schedule for known pending bookings. It must honor `Retry-After`, stop after settlement or configured expiry, and account for request-credit usage.

## 9. State and amount rules

| Concept | Meaning |
| --- | --- |
| `accepted` | The upstream intent was accepted without a required browser action. It is not proof of payment. |
| `action_required` | The traveller must complete a validated payment action. It is not proof of payment. |
| DP/PO paid | The first partial-payment term is settled. The invoice remains unpaid until all required terms are settled. |
| Fully paid | The authoritative invoice says all required payment is complete. An older event must not downgrade this state. |
| Product price | Booking `total_price`, not an invoice total that may include fees. |
| Current payment | Current term plus the applicable VAT-inclusive transaction fee exactly once. |
| Product reconciliation | Product-paid plus remaining-product equals product price when the API supplies an unambiguous breakdown. |

All money calculations use `Decimal` and preserve decimal-string API values. Unknown or ambiguous fee projections must be labelled as limitations rather than reconstructed in the UI.

## 10. Failure handling checklist

- Disable implicit upstream redirects and enforce configured HTTPS origins, timeouts, response-size limits, and redacted logs.
- Verify every signed response before parsing or trusting its fields; unsigned proxy errors cannot update transaction state.
- Retry reads conservatively. Retry writes only with the persisted identical operation, key, and payload.
- Treat authentication, scope, credits, not-found, validation, idempotency, rate-limit, provider, verification, and availability failures as separate safe categories.
- Deduplicate webhook delivery IDs and event IDs with durable retention; acknowledge only after persistence succeeds.
- Never let challenge handling, SSE frames, browser returns, or stale events directly prove or downgrade settlement.
- Keep one tenant per installation and enforce tenant plus subject ownership locally and upstream.

## 11. Verification map

| Behavior | Automated coverage |
| --- | --- |
| Regular and seasonal booking, quota, deadlines and ownership | `tests/test_demo_booking.py`, `tests/test_storefront_web.py` |
| Idempotent booking/payment creation and sequential DP/PO | `tests/test_demo_payment.py`, `tests/test_payment_web.py` |
| Partial and fully paid journeys, forged browser returns | `tests/test_payment_web.py` |
| Paid-intent revisit, completion cutoff and relative demo dates | `tests/test_review_regressions.py` |
| Production demo guard and private/no-store responses | `tests/test_release_security.py` |
| Deployment warnings and local-only unprivileged container | `tests/test_release_security.py` |

Run the current verification suite with:

```bash
uv run pytest -q
uv run ruff check .
uv run python manage.py check
```

Passing demo tests do not prove deployed External API compatibility. A live release still needs contract pinning, signed-transport tests, OIDC/security review, PostgreSQL concurrency tests, and validation against an approved test tenant.
