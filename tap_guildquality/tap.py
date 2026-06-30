"""GuildQuality tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_guildquality import streams


class TapGuildQuality(Tap):
    """Singer tap for the GuildQuality company API."""

    name = "tap-guildquality"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            secret=True,
            description="GuildQuality API bearer token (Account > API).",
        ),
        th.Property(
            "api_url",
            th.StringType,
            default="https://www.guildquality.com/company-api/v3",
            description="Base URL for the GuildQuality company API.",
        ),
        th.Property(
            "start_date",
            th.StringType,
            default="2020-01-01",
            description=(
                "Earliest record date to sync on first run (YYYY-MM-DD). "
                "Used as the incremental floor when there is no prior state."
            ),
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.SurveysStream]:
        """Return a list of discovered streams.

        Returns:
            A list of the tap's streams.
        """
        return [
            streams.SurveysStream(self),
        ]


if __name__ == "__main__":
    TapGuildQuality.cli()
