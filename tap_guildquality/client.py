"""REST client handling, including GuildQualityStream base class.

GuildQuality's company API (https://www.guildquality.com/company-api/v3) is a
straightforward Laravel-style JSON API:

* Auth is a single Bearer token (per member account) passed in the
  ``Authorization`` header.
* Responses wrap records in ``data`` and paginate via a ``links.next``
  absolute URL (HATEOAS). Passing ``limit`` *disables* pagination, so we never
  set it and instead follow ``links.next``.
* The documented rate limit is 300 requests/minute; exceeding it returns 429
  and a 1-minute IP block. The SDK's default ``validate_response`` already
  treats 429 + 5xx as retriable, so we just widen the retry budget.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl

from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.pagination import BaseHATEOASPaginator
from singer_sdk.streams import RESTStream

if sys.version_info >= (3, 12):
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Iterable

    import requests
    from singer_sdk.helpers.types import Context, Record


class GuildQualityPaginator(BaseHATEOASPaginator):
    """Follow the absolute URL in ``links.next`` until it is null."""

    @override
    def get_next_url(self, response: requests.Response) -> str | None:
        """Return the next page URL, or None when the last page is reached."""
        links = response.json().get("links") or {}
        return links.get("next")


class GuildQualityStream(RESTStream):
    """GuildQuality base stream class."""

    # URL paths are not sensitive here, and seeing them helps debugging.
    _LOG_REQUEST_METRIC_URLS = True

    @override
    def parse_response(self, response: requests.Response) -> Iterable[Record]:
        """Yield records, tolerating both response shapes.

        Most endpoints wrap records in ``{"data": [...]}``, but a few
        (``custom-fields``, ``surveys/deleted``) return a bare JSON array.
        Handle both so a stream doesn't break on the shape it happens to get.
        """
        body = response.json()
        records = body if isinstance(body, list) else (body.get("data") or [])
        yield from records

    @override
    def post_process(self, row: Record, context: Context | None = None) -> Record | None:
        """Drop records with a null/empty primary key.

        A null PK breaks ``target-snowflake``'s MERGE (``NULL = NULL`` is false,
        so it inserts an unmergeable duplicate every run) and trips NOT NULL if
        the column was declared required. Subclasses that need extra shaping
        should call ``super().post_process(...)`` first.
        """
        del context
        for key in self.primary_keys or ():
            if not row.get(key):
                self.logger.warning("%s: dropping record with null/empty PK %r", self.name, key)
                return None
        return row

    @property
    @override
    def url_base(self) -> str:
        """Return the API root, configurable via the ``api_url`` setting."""
        return self.config["api_url"]

    @property
    @override
    def authenticator(self) -> BearerTokenAuthenticator:
        """Authenticate every request with the account's Bearer token."""
        return BearerTokenAuthenticator(token=self.config["api_key"])

    @property
    @override
    def http_headers(self) -> dict[str, str]:
        """HTTP headers for each request."""
        headers = super().http_headers
        headers["Accept"] = "application/json"
        return headers

    @override
    def backoff_max_tries(self) -> int:
        """Retry generously — a 429 carries a 1-minute IP block."""
        return 8

    @override
    def get_new_paginator(self) -> GuildQualityPaginator:
        """Create a new HATEOAS paginator that follows ``links.next``."""
        return GuildQualityPaginator()

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Return query params for the request.

        On the first page we set the incremental window. On every subsequent
        page we simply replay the query string the API handed us in
        ``links.next`` (which already carries those params forward).
        """
        if next_page_token:
            # ``next_page_token`` is a urllib ParseResult of the next URL.
            return dict(parse_qsl(next_page_token.query))

        params: dict[str, Any] = {}
        if self.replication_key:
            start = self.get_starting_replication_key_value(context)
            if start:
                # The ``since`` filter is date-granular (YYYY-MM-DD). We pull
                # the whole bookmark day each run; MERGE on the PK dedupes.
                # ``dateFilter`` tells the API which timestamp ``since`` applies
                # to, and must equal the replication key.
                params["since"] = str(start)[:10]
                params["dateFilter"] = self.replication_key
        return params
