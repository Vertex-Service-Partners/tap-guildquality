# tap-guildquality

A [Singer](https://www.singer.io/) tap for the
[GuildQuality](https://www.guildquality.com/) company API, built with the
[Meltano Singer SDK](https://sdk.meltano.com).

GuildQuality is a customer-satisfaction surveying platform for the home-services
industry. This tap pulls survey data (and, as it grows, reviews / templates /
team / custom fields) into the Vertex warehouse.

## Streams

| Stream               | Endpoint                          | Replication                  | Primary key |
|----------------------|-----------------------------------|------------------------------|-------------|
| `surveys`            | `GET /surveys`                    | incremental on `updatedAt`       | `id`        |
| `reviews`            | `GET /reviews`                    | incremental on `lastActivityAt`  | `reviewId`  |
| `review_summary`     | `GET /review-summary`             | full table                       | `companyId` |
| `survey_templates`   | `GET /survey-templates`           | full table                       | `id`        |
| `team`               | `GET /team`                       | full table                       | `id`        |
| `children`           | `GET /children`                   | full table                       | `id`        |
| `reports`            | `GET /reports`                    | full table                       | `id`        |
| `deleted_surveys`    | `GET /surveys/deleted`            | full table                       | `id`        |
| `custom_fields`      | `GET /custom-fields`              | full table                       | `id`        |
| `project_user_roles` | `GET /project-user-roles`         | full table                       | `id`        |

> **Schema notes:** `surveys` and `reviews` are validated against live data with
> zero dropped fields. `custom_fields`, `project_user_roles`, and
> `deleted_surveys` return empty on the account this was built against, and the
> `reviews` `response` / `additionalQuestions` sub-objects were never populated
> in any sampled page — those four schemas are **doc-derived** and should be
> re-verified once real data appears (the SDK logs `not found in catalog schema`
> if a live field is missing). `custom_fields` and `deleted_surveys` return a
> bare JSON array; the base client parses both that and the `{"data": [...]}`
> wrapper.

## Configuration

| Setting      | Required | Default                                            | Description |
|--------------|----------|----------------------------------------------------|-------------|
| `api_key`    | yes      | —                                                  | Bearer token from **Account > API** (secret). |
| `api_url`    | no       | `https://www.guildquality.com/company-api/v3`      | API base URL. |
| `start_date` | no       | `2020-01-01`                                        | Incremental floor (YYYY-MM-DD) when there is no prior state. |

Provide the key via the environment so it never lands on disk:

```bash
export TAP_GUILDQUALITY_API_KEY='...'
```

## API notes

* **Auth:** single Bearer token per member account.
* **Pagination:** HATEOAS — follow `links.next` until null. Setting `limit`
  *disables* pagination, so the tap never sets it.
* **Rate limit:** 300 requests/minute; a 429 carries a 1-minute IP block. The
  tap retries on 429/5xx with backoff.
* **Dates are not ISO 8601** — values look like `2026-06-17T03:03:04 EDT` and are
  often empty strings. All timestamps are emitted as strings and cast in dbt.
* **`project.customFilters` and `project.users`** are dynamic/undocumented
  shapes; the tap JSON-encodes them into string columns. `PARSE_JSON` downstream.

## Develop

```bash
uv venv && source .venv/bin/activate
uv pip install -e '.[s3]'

# Plugin sanity
tap-guildquality --about
tap-guildquality --discover --config ENV    # ENV reads TAP_GUILDQUALITY_* vars

# Live pull (writes Singer messages to stdout)
tap-guildquality --config ENV > out.jsonl 2> err.log

# Tests (live-API tests run only when TAP_GUILDQUALITY_API_KEY is set)
uv pip install '.[test]' && pytest
```

Or via Meltano:

```bash
uvx meltano install
uvx meltano run tap-guildquality target-jsonl
```
