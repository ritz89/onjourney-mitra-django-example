# External API coverage for this POC

The inspected External API shapes the demo contracts. No live compatibility is claimed.

| Capability | Demo POC | Live integration status |
| --- | --- | --- |
| Tenant identity | Synthetic partner profile | Not connected |
| Products and details | Synthetic regular and seasonal products | Not connected |
| Departures | Dates, quota, PO and completion deadlines | Not connected |
| Traveller identity | Explicit local simulation | Hosted OIDC not implemented |
| Booking create/read | Local owned references and stable operation IDs | Not connected |
| Invoice | Product total and explicit demo fee breakdown | Real fee semantics not validated |
| Payment schemes | Sequential synthetic terms, DP first | Real scheme selection not validated |
| Payment intent | Virtual-account simulation only | Option discovery remains a backend contract gap |
| Payment status | Local authoritative demo state | Signed status verification not implemented |
| Events and webhooks | Out of scope | Not implemented |
| Invoice templates and key management | Out of scope | Not implemented |

A live adapter must not be exposed before payment-option eligibility, scheme confirmation, guest fields, seasonal enforcement, and fee projections are verified against an approved test tenant. Do not substitute private Mitra endpoints or credentials.
