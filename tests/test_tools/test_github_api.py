"""Tests for the GitHub Projects V2 GraphQL adapter."""
from __future__ import annotations

import json
from typing import Any

import pytest

from alfred.tools import github_api

# ---------------------------------------------------------------------------
# Fake HTTP client
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self) -> Any:
        return self._body


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = iter(responses)
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, json: dict[str, Any]) -> _FakeResponse:
        self.calls.append({"url": url, "json": json})
        return next(self._responses)


def _ok(data: Any) -> _FakeResponse:
    return _FakeResponse(200, {"data": data})


def _gql_error(message: str) -> _FakeResponse:
    return _FakeResponse(200, {"errors": [{"message": message}]})


@pytest.fixture(autouse=True)
def _restore_client_factory():
    original = github_api._client_factory
    yield
    github_api.set_client_factory(original)


# ---------------------------------------------------------------------------
# Fixture: board response payload
# ---------------------------------------------------------------------------

_BOARD_DATA = {
    "organization": {
        "projectV2": {
            "items": {
                "nodes": [
                    {
                        "id": "ITEM_1",
                        "content": {"title": "Build login page"},
                        "fieldValues": {
                            "nodes": [
                                {
                                    "name": "In Progress",
                                    "field": {"name": "Status"},
                                },
                                {
                                    "number": 3,
                                    "field": {"name": "Story Points"},
                                },
                                {
                                    "users": {"nodes": [{"login": "alice"}]},
                                    "field": {"name": "Assignees"},
                                },
                                {
                                    "labels": {"nodes": [{"name": "frontend"}]},
                                    "field": {"name": "Labels"},
                                },
                                {
                                    "title": "Sprint 5",
                                    "startDate": "2026-04-01",
                                    "duration": 2,
                                    "field": {"name": "Sprint"},
                                },
                            ]
                        },
                    },
                    {
                        "id": "ITEM_2",
                        "content": {"title": "Fix DB migration"},
                        "fieldValues": {
                            "nodes": [
                                {
                                    "name": "Done",
                                    "field": {"name": "Status"},
                                },
                            ]
                        },
                    },
                ]
            }
        }
    }
}

_USER_BOARD_DATA = {
    "user": {
        "projectV2": {
            "items": {
                "nodes": [
                    {
                        "id": "ITEM_U1",
                        "content": {"title": "Draft from personal board"},
                        "fieldValues": {
                            "nodes": [
                                {
                                    "name": "Todo",
                                    "field": {"name": "Status"},
                                },
                            ]
                        },
                    }
                ]
            }
        }
    }
}


# ---------------------------------------------------------------------------
# get_board_state tests
# ---------------------------------------------------------------------------


def test_get_board_state_returns_stories() -> None:
    client = _FakeClient([_ok(_BOARD_DATA)])
    github_api.set_client_factory(lambda token: client)

    state = github_api.get_board_state("myorg", 42, "tok")

    assert len(state.stories) == 2
    s0 = state.stories[0]
    assert s0.id == "ITEM_1"
    assert s0.title == "Build login page"
    assert s0.status == "In Progress"
    assert s0.story_points == 3
    assert s0.assignee == "alice"
    assert s0.labels == ["frontend"]


def test_get_board_state_parses_sprint_metadata() -> None:
    client = _FakeClient([_ok(_BOARD_DATA)])
    github_api.set_client_factory(lambda token: client)

    state = github_api.get_board_state("myorg", 42, "tok")

    assert state.sprint_number == 5
    from datetime import date
    assert state.sprint_start == date(2026, 4, 1)
    assert state.sprint_end == date(2026, 4, 15)  # +2 weeks


def test_get_board_state_supports_user_owned_project() -> None:
    client = _FakeClient(
        [
            _gql_error("Could not resolve to an Organization with the login of 'donalmadden'."),
            _ok(_USER_BOARD_DATA),
        ]
    )
    github_api.set_client_factory(lambda token: client)

    state = github_api.get_board_state("donalmadden", 5, "tok")

    assert len(state.stories) == 1
    assert state.stories[0].id == "ITEM_U1"
    assert state.stories[0].title == "Draft from personal board"
    assert state.stories[0].status == "Todo"


def test_get_board_state_sends_correct_variables() -> None:
    client = _FakeClient([_ok(_BOARD_DATA)])
    github_api.set_client_factory(lambda token: client)

    github_api.get_board_state("acme", 7, "secret")

    call = client.calls[0]
    assert call["url"] == github_api._GRAPHQL_URL
    assert call["json"]["variables"] == {"org": "acme", "number": 7}


def test_get_board_state_http_error_raises() -> None:
    client = _FakeClient([_FakeResponse(401, {"message": "Bad credentials"})])
    github_api.set_client_factory(lambda token: client)

    with pytest.raises(github_api.GitHubAPIError, match="HTTP 401"):
        github_api.get_board_state("org", 1, "bad-token")


def test_get_board_state_graphql_error_raises() -> None:
    client = _FakeClient([_gql_error("Could not resolve to a ProjectV2")])
    github_api.set_client_factory(lambda token: client)

    with pytest.raises(github_api.GitHubAPIError, match="GraphQL errors"):
        github_api.get_board_state("org", 999, "tok")


def test_get_board_state_empty_board() -> None:
    data = {"organization": {"projectV2": {"items": {"nodes": []}}}}
    client = _FakeClient([_ok(data)])
    github_api.set_client_factory(lambda token: client)

    state = github_api.get_board_state("org", 1, "tok")
    assert state.stories == []
    assert state.sprint_number is None


# ---------------------------------------------------------------------------
# create_story tests
# ---------------------------------------------------------------------------

_PROJECT_ID_DATA = {"organization": {"projectV2": {"id": "PVT_abc123"}}}
_USER_PROJECT_ID_DATA = {"user": {"projectV2": {"id": "PVT_user123"}}}
_CREATE_ITEM_DATA = {
    "addProjectV2DraftIssue": {"projectItem": {"id": "PVTI_new456"}}
}
_GET_DRAFT_ISSUE_ID_DATA = {"node": {"content": {"id": "DI_123"}}}
_UPDATE_DRAFT_ISSUE_DATA = {"updateProjectV2DraftIssue": {"draftIssue": {"id": "DI_123"}}}


def test_create_story_returns_item_id() -> None:
    client = _FakeClient([_ok(_PROJECT_ID_DATA), _ok(_CREATE_ITEM_DATA)])
    github_api.set_client_factory(lambda token: client)

    item_id = github_api.create_story(
        "myorg",
        42,
        "Add dark mode",
        "tok",
        body="Draft body",
    )

    assert item_id == "PVTI_new456"


def test_create_story_sends_project_id_in_mutation() -> None:
    client = _FakeClient([_ok(_PROJECT_ID_DATA), _ok(_CREATE_ITEM_DATA)])
    github_api.set_client_factory(lambda token: client)

    github_api.create_story("myorg", 42, "My story", "tok", body="Story body")

    mutation_call = client.calls[1]
    assert mutation_call["json"]["variables"]["projectId"] == "PVT_abc123"
    assert mutation_call["json"]["variables"]["title"] == "My story"
    assert mutation_call["json"]["variables"]["body"] == "Story body"


def test_create_story_supports_user_owned_project() -> None:
    client = _FakeClient(
        [
            _gql_error("Could not resolve to an Organization with the login of 'donalmadden'."),
            _ok(_USER_PROJECT_ID_DATA),
            _ok(_CREATE_ITEM_DATA),
        ]
    )
    github_api.set_client_factory(lambda token: client)

    item_id = github_api.create_story(
        "donalmadden",
        5,
        "Personal board story",
        "tok",
        body="Draft on personal board",
    )

    assert item_id == "PVTI_new456"
    mutation_call = client.calls[2]
    assert mutation_call["json"]["variables"]["projectId"] == "PVT_user123"


def test_create_story_raises_if_project_not_found() -> None:
    data = {"organization": {"projectV2": None}}
    client = _FakeClient([_ok(data)])
    github_api.set_client_factory(lambda token: client)

    with pytest.raises(github_api.GitHubAPIError, match="project id"):
        github_api.create_story("org", 999, "title", "tok")


def test_create_story_raises_on_http_error() -> None:
    client = _FakeClient([_FakeResponse(403, {})])
    github_api.set_client_factory(lambda token: client)

    with pytest.raises(github_api.GitHubAPIError, match="HTTP 403"):
        github_api.create_story("org", 1, "title", "tok")


def test_update_story_body_resolves_draft_issue_and_updates_body() -> None:
    client = _FakeClient([_ok(_GET_DRAFT_ISSUE_ID_DATA), _ok(_UPDATE_DRAFT_ISSUE_DATA)])
    github_api.set_client_factory(lambda token: client)

    github_api.update_story_body("PVTI_new456", "Updated body", "tok")

    lookup_call = client.calls[0]
    assert lookup_call["json"]["variables"]["itemId"] == "PVTI_new456"

    mutation_call = client.calls[1]
    assert mutation_call["json"]["variables"]["draftIssueId"] == "DI_123"
    assert mutation_call["json"]["variables"]["body"] == "Updated body"


def test_update_story_body_raises_when_project_item_has_no_draft_issue() -> None:
    client = _FakeClient([_ok({"node": {"content": None}})])
    github_api.set_client_factory(lambda token: client)

    with pytest.raises(github_api.GitHubAPIError, match="Could not resolve DraftIssue id"):
        github_api.update_story_body("PVTI_missing", "Body", "tok")
