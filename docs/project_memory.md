# Project memory

## Current state

Credential-free POC is implemented locally. Catalogue, simulated login, regular/seasonal booking, invoice, sequential payment, provider simulation, and status recovery are covered by automated tests. No live External API call exists.

## Decisions

- Standalone Django 5.2 application with server-rendered templates and local assets.
- Python 3.12, uv lockfile, SQLite demo storage, no frontend build pipeline.
- Synthetic partner and products only; no customer data or real credentials.
- Stable UUID operation IDs protect booking and payment writes.
- Product amounts and fees remain separate. DP/PO is partial, never fully paid.
- Browser returns trigger status reads and never settle payments.

## Verification and review

Independent implementation and security reviews completed. Paid-intent revisits now redirect to the invoice, payment-completion deadlines block new intents while late provider settlement remains recordable, and seasonal fixtures follow an injectable demo clock. Production mode closes the demo storefront, authenticated paths use no-store cache headers, Compose is localhost-only, and the container uses an unprivileged user. The final suite has 48 passing tests plus clean Ruff, Django deployment, and Compose checks. Chrome journeys pass for regular and seasonal partial→full payment; mobile and axe checks are clean. Image construction remains unverified because the Docker daemon was unavailable.

Deferred polish: disable unavailable departure choices, improve seasonal radio-group semantics and error associations, and centralize fee/percentage presentation.

## Remaining work before a real integration

Verify the exported API contract and payment-option/scheme gaps with the API owner; implement signed live transport and hosted OIDC; use PostgreSQL for concurrency acceptance; add verified webhooks and reconciliation; and complete sandbox validation and deployment. The code is MIT licensed; trademark and hosted API rights are not included.

The public planning context is summarized in `docs/architecture.md` and `docs/api-coverage.md`; no workspace-local files are required to use this repository.
