"""Reference / catalog streams for tap-guildquality.

Small, full-table endpoints with no pagination and no incremental key. Each is
re-synced in full every run and MERGEd on its primary key.
"""

from __future__ import annotations

from singer_sdk import typing as th

from tap_guildquality.client import GuildQualityStream


class SurveyTemplatesStream(GuildQualityStream):
    """Survey templates configured for the account (GET /survey-templates)."""

    name = "survey_templates"
    path = "/survey-templates"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("name", th.StringType),
        th.Property("surveyProcess", th.StringType),
        th.Property("schedule", th.StringType),
        th.Property("smartQuestionsMuted", th.BooleanType),
    ).to_dict()


class TeamStream(GuildQualityStream):
    """Team members on the account (GET /team)."""

    name = "team"
    path = "/team"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("role", th.StringType),
        th.Property("name", th.StringType),
        th.Property("email", th.StringType),
        th.Property("avatarUrl", th.StringType),
    ).to_dict()


class ChildrenStream(GuildQualityStream):
    """Child company accounts under this partner account (GET /children)."""

    name = "children"
    path = "/children"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("name", th.StringType),
        th.Property("createdAt", th.StringType),
    ).to_dict()


class ReportsStream(GuildQualityStream):
    """Saved reports available on the account (GET /reports)."""

    name = "reports"
    path = "/reports"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("name", th.StringType),
    ).to_dict()


class ProjectUserRolesStream(GuildQualityStream):
    """Project user-role types (GET /project-user-roles).

    Empty on this account; schema is doc-derived ({id, name}).
    """

    name = "project_user_roles"
    path = "/project-user-roles"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("name", th.StringType),
    ).to_dict()


class CustomFieldsStream(GuildQualityStream):
    """Custom field definitions (GET /custom-fields).

    Returns a *bare JSON array* (handled by the base ``parse_response``). Empty
    on this account; schema is doc-derived ({id, label, values:[{id, value}]}).
    """

    name = "custom_fields"
    path = "/custom-fields"
    primary_keys = ("id",)

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("label", th.StringType),
        th.Property(
            "values",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.IntegerType),
                    th.Property("value", th.StringType),
                ),
            ),
        ),
    ).to_dict()
