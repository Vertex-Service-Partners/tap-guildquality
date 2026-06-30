"""Review streams for tap-guildquality.

* ``reviews`` — one record per published review, paginated, incremental on
  ``lastActivityAt`` (a company reply added later bumps that timestamp, so it
  catches edits the ``reviewedAt`` filter would miss).
* ``review_summary`` — one aggregate row per company (rating distribution +
  per-question score). Full-table snapshot.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from singer_sdk import typing as th

from tap_guildquality.client import GuildQualityStream

if sys.version_info >= (3, 12):
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

if TYPE_CHECKING:
    from singer_sdk.helpers.types import Context, Record


class ReviewsStream(GuildQualityStream):
    """Published reviews."""

    name = "reviews"
    path = "/reviews"
    primary_keys = ("reviewId",)
    replication_key = "lastActivityAt"

    schema = th.PropertiesList(
        th.Property("reviewId", th.IntegerType),
        th.Property("companyId", th.IntegerType),
        th.Property("projectId", th.IntegerType),
        th.Property("displayName", th.StringType),
        th.Property("city", th.StringType),
        th.Property("state", th.StringType),
        th.Property("reviewedAt", th.StringType),
        th.Property("lastActivityAt", th.StringType),
        th.Property("url", th.StringType),
        th.Property("rating", th.IntegerType),
        th.Property("comment", th.StringType),
        # response/additionalQuestions are doc-derived: unpopulated on this
        # account across every page sampled. Verify against real data if a
        # company starts replying to reviews.
        th.Property(
            "response",
            th.ObjectType(
                th.Property("comment", th.StringType),
                th.Property("createdAt", th.StringType),
                th.Property("updatedAt", th.StringType),
            ),
        ),
        th.Property(
            "additionalQuestions",
            th.ArrayType(
                th.ObjectType(
                    th.Property("question", th.StringType),
                    # int|null per docs; stringified in post_process to be safe.
                    th.Property("rating", th.StringType),
                    th.Property("comment", th.StringType),
                ),
            ),
        ),
    ).to_dict()

    @override
    def post_process(self, row: Record, context: Context | None = None) -> Record | None:
        """Normalize additionalQuestions ratings to strings."""
        row = super().post_process(row, context)
        if row is None:
            return None
        for question in row.get("additionalQuestions") or []:
            rating = question.get("rating")
            if isinstance(rating, (int, float)) and not isinstance(rating, bool):
                question["rating"] = str(rating)
        return row


class ReviewSummaryStream(GuildQualityStream):
    """Per-company aggregate review summary (full-table snapshot)."""

    name = "review_summary"
    path = "/review-summary"
    primary_keys = ("companyId",)

    schema = th.PropertiesList(
        th.Property("companyName", th.StringType),
        th.Property("companyId", th.IntegerType),
        th.Property("companyProfileUrl", th.StringType),
        th.Property("surveys", th.IntegerType),
        th.Property(
            "review",
            th.ObjectType(
                th.Property("total", th.IntegerType),
                th.Property("average", th.NumberType),
                th.Property("stars5", th.IntegerType),
                th.Property("stars4", th.IntegerType),
                th.Property("stars3", th.IntegerType),
                th.Property("stars2", th.IntegerType),
                th.Property("stars1", th.IntegerType),
            ),
        ),
        th.Property(
            "questions",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.IntegerType),
                    th.Property("name", th.StringType),
                    th.Property("percentage", th.IntegerType),
                ),
            ),
        ),
    ).to_dict()
