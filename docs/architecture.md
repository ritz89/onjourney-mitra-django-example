# POC architecture

This repository is a credential-free proof of concept for a Mitra-owned traveller storefront. It is not the completed public template described in the delivery plan.

The browser talks only to the Django backend-for-frontend. Django views call application services, which use the `DemoClient` integration adapter and local models. The demo adapter supplies synthetic tenant, product, departure, booking, invoice, and payment data. No upstream request is made.

The POC covers catalogue → simulated sign-in → booking → invoice → sequential payment → authoritative status recovery. Local booking references are bound to a demo traveller subject. Stable operation IDs protect booking and payment creation from repeated submissions.

## Boundaries

- SQLite and simulated sign-in are demo-only.
- The demo payment provider never handles real money.
- Only local demo booking history is shown.
- Real OIDC, token encryption, signed response verification, live HTTP transport, webhooks, PostgreSQL concurrency, and production deployment remain unimplemented.
- The production settings reject demo mode but do not make this POC production-ready.

Source contract inspected on 12 November 2026: `onjourneyv2` commit `3d6a34c6c121c85b29cd9115b7e86e2bdc188aff`. Documentation SHA-256: quickstart `2bbda2935cd161a6bb49f4d972ece4b738781f3c23e4ed45acde99aa1e4374be`, v1 contract `d54a0b6988fde113c4fd9986966123e88305383cb3bdaa77193e46bf31f806e2`. These are local source observations, not deployed API validation.
