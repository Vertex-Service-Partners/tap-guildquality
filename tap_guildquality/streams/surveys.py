"""Surveys stream for tap-guildquality.

GET /company-api/v3/surveys — one record per survey sent to a homeowner, with
the customer/contact, the project, the survey template, lifecycle timestamps,
and (with ``questions=1``) the per-question ratings and comments.

Schema notes worth knowing before you touch this file:

* **Dates are NOT ISO 8601.** GuildQuality returns ``"2026-06-17T03:03:04 EDT"``
  (a space and a timezone *abbreviation*) and frequently an empty string ``""``
  for dates that haven't happened yet. ``th.DateTimeType`` would reject both, so
  every timestamp here is ``th.StringType`` and is cast downstream in dbt.
* **``project.customFilters`` and ``project.users`` are dynamic.** customFilters
  is a free-form ``{label: [values]}`` map that varies per template, and users
  is an array of an undocumented shape (empty in every sample). The Singer SDK
  strips un-enumerated nested keys, so rather than lose data we JSON-encode both
  into string columns in ``post_process`` and let dbt ``PARSE_JSON`` them.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

from singer_sdk import typing as th

from tap_guildquality.client import GuildQualityStream

if sys.version_info >= (3, 12):
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

if TYPE_CHECKING:
    from singer_sdk.helpers.types import Context, Record


class SurveysStream(GuildQualityStream):
    """Company surveys."""

    name = "surveys"
    path = "/surveys"
    primary_keys = ("id",)
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),  # PK — never required=True (NOT NULL footgun)
        th.Property(
            "contact",
            th.ObjectType(
                th.Property("id", th.IntegerType),
                th.Property("name", th.StringType),
                th.Property("email1", th.StringType),
                th.Property("email2", th.StringType),
                th.Property("phone1", th.StringType),
                th.Property("phone2", th.StringType),
                th.Property("createdAt", th.StringType),
                th.Property("updatedAt", th.StringType),
            ),
        ),
        th.Property(
            "company",
            th.ObjectType(
                th.Property("id", th.IntegerType),
                th.Property("customCompanyId", th.StringType),
                th.Property("name", th.StringType),
            ),
        ),
        th.Property(
            "project",
            th.ObjectType(
                th.Property("id", th.IntegerType),
                th.Property("address", th.StringType),
                th.Property("city", th.StringType),
                th.Property("state", th.StringType),
                th.Property("zip", th.StringType),
                th.Property("leadDate", th.StringType),
                th.Property("startDate", th.StringType),
                th.Property("endDate", th.StringType),
                th.Property("createdAt", th.StringType),
                th.Property("updatedAt", th.StringType),
                th.Property("externalId", th.StringType),
                th.Property("value", th.StringType),  # money as string preserves precision
                th.Property("notes", th.StringType),
                # Dynamic shapes — JSON-encoded to strings in post_process.
                th.Property("customFilters", th.StringType),
                th.Property("users", th.StringType),
            ),
        ),
        th.Property("template", th.StringType),
        th.Property("endedAt", th.StringType),
        th.Property("createdAt", th.StringType),
        th.Property("updatedAt", th.StringType),
        th.Property("sendAt", th.StringType),
        th.Property("completionMode", th.StringType),
        th.Property("isImported", th.BooleanType),
        th.Property("lastResponseMethod", th.StringType),
        th.Property("lastActivityAt", th.StringType),
        th.Property("status", th.StringType),
        th.Property("surveyTakeUrl", th.StringType),
        th.Property(
            "questions",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.IntegerType),
                    th.Property("questionId", th.IntegerType),
                    th.Property("order", th.IntegerType),
                    th.Property("name", th.StringType),
                    th.Property("type", th.StringType),  # rating | mcs | mcm | comment
                    # rating is int OR "" (no rating); ratingScale is "1-5" (not an int);
                    # response is an array of choice strings. All normalized to strings in
                    # post_process so the warehouse column types stay stable.
                    th.Property("rating", th.StringType),
                    th.Property("ratingScale", th.StringType),
                    th.Property("comment", th.StringType),
                    th.Property("published", th.BooleanType),
                    th.Property("response", th.StringType),
                ),
            ),
        ),
    ).to_dict()

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Add ``questions=1`` so per-question detail is included."""
        params = super().get_url_params(context, next_page_token)
        # On the first page only — subsequent pages replay the next URL verbatim,
        # which already carries questions=1 forward.
        if not next_page_token:
            params["questions"] = 1
        return params

    @override
    def post_process(self, row: Record, context: Context | None = None) -> Record | None:
        """Drop null-PK records and JSON-encode dynamic project sub-objects."""
        row = super().post_process(row, context)
        if row is None:
            return None

        project = row.get("project")
        if isinstance(project, dict):
            for key in ("customFilters", "users"):
                value = project.get(key)
                if isinstance(value, (dict, list)):
                    project[key] = json.dumps(value)

        # questions[].rating is int-or-"", and questions[].response is an array of
        # choice strings. Normalize both to strings so column types don't flap.
        for question in row.get("questions") or []:
            rating = question.get("rating")
            if isinstance(rating, (int, float)) and not isinstance(rating, bool):
                question["rating"] = str(rating)
            response = question.get("response")
            if isinstance(response, (dict, list)):
                question["response"] = json.dumps(response)
        return row


class DeletedSurveysStream(GuildQualityStream):
    """Deleted-survey tombstones (GET /surveys/deleted).

    Returns a *bare JSON array* (handled by the base ``parse_response``). This
    account currently returns none, so the schema is doc-derived. Full-table:
    it's a small tombstone list and the deleted endpoint's incremental support
    is unconfirmed.
    """

    name = "deleted_surveys"
    path = "/surveys/deleted"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("status", th.IntegerType),
        th.Property("companyId", th.IntegerType),
        th.Property("deletedAt", th.StringType),  # "2019-01-29 14:41:14" — not ISO-T
    ).to_dict()
