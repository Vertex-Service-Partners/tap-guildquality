"""Tests for tap-guildquality.

The SDK harness (``get_tap_test_class``) runs discovery + record-emission tests
against the live API, so it only runs when ``TAP_GUILDQUALITY_API_KEY`` is set.
The schema-shape tests below run with no credentials and pin the decisions that
are easy to "clean up" and silently regress.
"""

from __future__ import annotations

import os

import pytest
from singer_sdk.testing import get_tap_test_class

from tap_guildquality.streams.reviews import ReviewsStream
from tap_guildquality.streams.surveys import SurveysStream
from tap_guildquality.tap import TapGuildQuality


class _FakeResponse:
    """Minimal stand-in for requests.Response with a .json() method."""

    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload


def _stream(cls: type) -> object:
    return cls(TapGuildQuality(config={"api_key": "x"}, validate_config=False))

API_KEY = os.environ.get("TAP_GUILDQUALITY_API_KEY")

if API_KEY:
    TestTapGuildQuality = get_tap_test_class(
        tap_class=TapGuildQuality,
        # Bound the live sync so the harness doesn't pull from 2020.
        config={
            "api_key": API_KEY,
            "start_date": os.environ.get("TAP_GUILDQUALITY_START_DATE", "2026-06-01"),
        },
    )


_PROJECT_PROPS = SurveysStream.schema["properties"]["project"]["properties"]


def test_pk_is_not_required() -> None:
    """PK must not be required=True — target-snowflake would make it NOT NULL."""
    assert "id" not in SurveysStream.schema.get("required", [])


def test_timestamps_are_strings_not_datetimes() -> None:
    """GuildQuality dates ('2026-06-17T03:03:04 EDT', '') are not ISO 8601."""
    for field in ("createdAt", "updatedAt", "sendAt", "endedAt", "lastActivityAt"):
        assert SurveysStream.schema["properties"][field]["type"] == ["string", "null"]


@pytest.mark.parametrize("field", ["customFilters", "users"])
def test_dynamic_project_fields_are_strings(field: str) -> None:
    """Dynamic-shape sub-objects are JSON-encoded to strings, not dropped."""
    assert _PROJECT_PROPS[field]["type"] == ["string", "null"]


def test_post_process_drops_null_pk() -> None:
    """A record with no id is dropped, not emitted with a null PK."""
    stream = SurveysStream(TapGuildQuality(config={"api_key": "x"}, validate_config=False))
    assert stream.post_process({"id": None}) is None
    assert stream.post_process({}) is None


def test_post_process_json_encodes_dynamic_fields() -> None:
    """customFilters/users come out as JSON strings ready for PARSE_JSON."""
    stream = SurveysStream(TapGuildQuality(config={"api_key": "x"}, validate_config=False))
    row = stream.post_process(
        {"id": 1, "project": {"customFilters": {"Color": ["Onyx Black"]}, "users": []}},
    )
    assert row is not None
    assert row["project"]["customFilters"] == '{"Color": ["Onyx Black"]}'
    assert row["project"]["users"] == "[]"


def test_parse_response_handles_both_shapes() -> None:
    """Wrapped {data:[...]} and bare-array responses both yield records."""
    stream = _stream(SurveysStream)
    assert list(stream.parse_response(_FakeResponse({"data": [{"id": 1}]}))) == [{"id": 1}]
    assert list(stream.parse_response(_FakeResponse([{"id": 2}]))) == [{"id": 2}]
    assert list(stream.parse_response(_FakeResponse([]))) == []
    assert list(stream.parse_response(_FakeResponse({"data": None}))) == []


def test_reviews_additional_question_rating_stringified() -> None:
    """additionalQuestions[].rating (int|null per docs) is coerced to a string."""
    stream = _stream(ReviewsStream)
    row = stream.post_process(
        {"reviewId": 1, "additionalQuestions": [{"question": "q", "rating": 5, "comment": ""}]},
    )
    assert row is not None
    assert row["additionalQuestions"][0]["rating"] == "5"


def test_reviews_drops_null_pk() -> None:
    """The generic base guard drops a review with no reviewId."""
    stream = _stream(ReviewsStream)
    assert stream.post_process({"reviewId": None}) is None
