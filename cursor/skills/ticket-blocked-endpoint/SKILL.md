---
name: ticket-blocked-endpoint
description: Add or modify a ticket workflow so tickets support the blocked status and expose POST /tickets/{id}/block. Use when implementing ticket status changes, database migrations, FastAPI/Express ticket endpoints, or tests for blocking a ticket.
---

# Add Ticket Blocked Status

Implement a consistent, database-backed `blocked` ticket status and the endpoint `POST /tickets/{id}/block`. Preserve the repository's existing framework, persistence layer, validation conventions, response envelope, error format, authentication behavior, and test tooling. Do not replace the project architecture to add this small feature.

## Inspect Before Editing

Locate the ticket entity or model, status declaration, request and response schemas, router or controller, repository/service layer, migrations, existing ticket tests, and API documentation. Identify whether status is represented by a string, language enum, database enum, check constraint, or a separate status table. Reuse the existing source of truth; do not create a second, conflicting status list.

Confirm how the project treats missing records, invalid state changes, timestamps, transactions, and authorization. If the repository already has a status-transition policy, extend that policy instead of inventing a parallel rule.

## Required Behavior

Add `blocked` to every relevant ticket status definition, including validation schemas and database constraints or enum values where present. Persist it exactly as the lowercase string `blocked` unless the repository uses a different established serialized format.

Implement this route:

```http
POST /tickets/{id}/block
```

Make the endpoint set the selected ticket's status to `blocked`, persist the change, update any existing `updated_at` mechanism, and return the updated ticket using the project's normal success shape. Do not require a request body unless the codebase already supports a documented blocking reason or status-change metadata.

Apply the following default contract only where the repository has no established alternative:

| Situation | Required response |
|---|---|
| Ticket exists and is not blocked | `200 OK` with the updated ticket |
| Ticket is already blocked | `200 OK` with the ticket; keep the operation idempotent |
| Ticket ID does not exist | `404 Not Found` using the project's normal error schema |
| Existing workflow disallows blocking from the current status | `409 Conflict` using the project's normal error schema |

Treat terminal statuses according to existing domain rules. If no such rules exist, avoid adding arbitrary restrictions beyond the behavior above.

## Persistence and Migration Rules

Make the schema and application change atomically. If status has a database enum or check constraint, add a migration that permits `blocked` before deployment. If the database stores an unconstrained string, do not create an unnecessary migration solely to restate application validation.

Use the repository's migration tool and naming style. Do not use destructive migrations, drop ticket data, recreate tables, or alter existing ticket status values. Ensure the downgrade path is safe where the project requires reversible migrations.

## Implementation Requirements

Keep all status logic centralized. Reuse existing helpers such as `get_ticket_or_404`, service methods, dependency injection, transaction wrappers, serializers, and authorization checks.

Use parameterized ORM or query-builder operations; do not build SQL with string interpolation. Commit only after a successful update and roll back or surface the repository-standard error response on persistence failure. Do not expose database exception text in API responses.

For FastAPI projects, keep the handler thin: validate the path parameter, delegate to the service or repository, and return the existing response model. For Express projects, use the established router/controller/service split. For other stacks, follow their local conventions.

## Tests

Add or extend automated tests at the same level as existing ticket endpoint tests. Cover the following cases:

| Test | Expected assertion |
|---|---|
| Block an existing ticket | Returns success and response status is `blocked` |
| Persistence | A subsequent fetch or database query still reports `blocked` |
| Block twice | Remains successful and does not duplicate side effects |
| Unknown ticket ID | Returns the established `404` response |
| Prohibited transition, if applicable | Returns the established `409` response |
| Regression | Existing ticket creation, retrieval, and other supported status updates still work |

Run the targeted test suite and the repository's normal formatting, linting, type-checking, and migration validation commands when available. Report commands run and their result. If a required dependency such as PostgreSQL is unavailable, state which checks could not be performed rather than claiming success.

## Documentation and Handoff

Update API documentation, OpenAPI annotations, or endpoint examples only if the repository maintains them. Include an example request without a body:

```bash
curl -X POST http://127.0.0.1:8000/tickets/123/block
```

In the final implementation summary, state the files changed, the stored status value, the endpoint's success and error behavior, migration impact, and test results. Call out any assumption that could not be verified from the repository.
