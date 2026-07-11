# Payments API Latency Runbook

Service: `payments-api`

## Symptoms

- Checkout requests are slower than normal.
- p95 or p99 latency is elevated.
- Customers may report delayed payment confirmation.

## Initial Checks

1. Check p95 and p99 latency dashboards for checkout endpoints.
2. Review database CPU, slow queries, and connection pool saturation.
3. Check recent deployments for payments-api and dependent services.
4. Inspect application logs for timeout or upstream dependency errors.
5. Check external payment provider status pages.

## Escalation

Escalate if customer-facing checkout failure rate increases, payment confirmation is delayed, or latency remains elevated after rollback and dependency checks.
