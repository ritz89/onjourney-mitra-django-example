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

## Remaining work before a real integration

Verify the exported API contract and payment-option/scheme gaps with the API owner; implement signed live transport and hosted OIDC; use PostgreSQL for concurrency acceptance; add verified webhooks and reconciliation; complete sandbox validation, deployment, licensing, and public-release review.

The source plan is `/Users/macbook/projects/onjourney/docs/superpowers/plans/2026-11-10-mitra-external-api-django-template.md`. Do not edit that plan during implementation.
