# API Examples

Base URL:

```text
http://localhost:8000
```

Set these placeholders as you go:

```powershell
$TOKEN="paste_access_token_here"
$INCIDENT_ID="paste_incident_id_here"
$RUNBOOK_ID="paste_runbook_id_here"
$TRIAGE_ID="paste_triage_id_here"
$JOB_ID="paste_job_id_here"
```

## Register

```powershell
curl -X POST http://localhost:8000/api/auth/register `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"engineer@example.com\",\"password\":\"correct-horse-battery\",\"full_name\":\"Ops Engineer\"}"
```

## Login

```powershell
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"engineer@example.com\",\"password\":\"correct-horse-battery\"}"
```

## Current User

```powershell
curl http://localhost:8000/api/auth/me `
  -H "Authorization: Bearer $TOKEN"
```

## Create Incident

```powershell
curl -X POST http://localhost:8000/api/incidents `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d "{\"title\":\"Payments API high latency\",\"description\":\"p95 latency is high for checkout requests.\",\"affected_service\":\"payments-api\"}"
```

## Create Runbook

```powershell
curl -X POST http://localhost:8000/api/runbooks `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d "{\"title\":\"Payments API Latency Runbook\",\"service_name\":\"payments-api\",\"description\":\"Steps for investigating checkout latency.\"}"
```

## Add Runbook Chunk

```powershell
curl -X POST http://localhost:8000/api/runbooks/$RUNBOOK_ID/chunks `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d "{\"chunk_text\":\"Check p95 latency, database CPU, recent deployments, slow queries, and external API failures.\",\"chunk_index\":0,\"metadata\":{\"section\":\"initial checks\"}}"
```

## Search Runbooks

```powershell
curl -X POST http://localhost:8000/api/runbooks/search `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"payments checkout p95 latency high\",\"service_name\":\"payments-api\",\"top_k\":5}"
```

Search returns vector distance. Lower `distance` means a closer match.

## Synchronous Triage

```powershell
curl -X POST http://localhost:8000/api/incidents/$INCIDENT_ID/triage `
  -H "Authorization: Bearer $TOKEN"
```

This runs triage during the HTTP request. It remains available for local testing and debugging.

## Async Triage Job

Create a job:

```powershell
curl -X POST http://localhost:8000/api/incidents/$INCIDENT_ID/triage-jobs `
  -H "Authorization: Bearer $TOKEN"
```

Check status:

```powershell
curl http://localhost:8000/api/triage-jobs/$JOB_ID `
  -H "Authorization: Bearer $TOKEN"
```

Statuses:

- `pending`
- `running`
- `succeeded`
- `failed`

## Approve Triage

```powershell
curl -X POST http://localhost:8000/api/triage/$TRIAGE_ID/approve `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d "{\"reviewer_notes\":\"Looks accurate for current symptoms.\"}"
```

## Reject Triage

```powershell
curl -X POST http://localhost:8000/api/triage/$TRIAGE_ID/reject `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d "{\"reviewer_notes\":\"Recommendation does not match observed metrics.\"}"
```

## Audit Logs

```powershell
curl "http://localhost:8000/api/audit-logs?entity_type=incident&action=created&limit=20" `
  -H "Authorization: Bearer $TOKEN"
```

Supported filters:

- `entity_type`
- `entity_id`
- `actor_id`
- `action`
- `limit`
