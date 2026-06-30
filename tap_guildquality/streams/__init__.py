"""Stream type classes for tap-guildquality."""

from __future__ import annotations

from tap_guildquality.streams.reference import (
    ChildrenStream,
    CustomFieldsStream,
    ProjectUserRolesStream,
    ReportsStream,
    SurveyTemplatesStream,
    TeamStream,
)
from tap_guildquality.streams.reviews import ReviewsStream, ReviewSummaryStream
from tap_guildquality.streams.surveys import DeletedSurveysStream, SurveysStream

__all__ = [
    "ChildrenStream",
    "CustomFieldsStream",
    "DeletedSurveysStream",
    "ProjectUserRolesStream",
    "ReportsStream",
    "ReviewSummaryStream",
    "ReviewsStream",
    "SurveyTemplatesStream",
    "SurveysStream",
    "TeamStream",
]
