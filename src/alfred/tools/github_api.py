"""
GitHub Projects V2 GraphQL adapter.

Two public functions:
  get_board_state(org, project_number, token) -> BoardState
  create_story(org, project_number, title, token, body="") -> str
      (returns new item id)
  update_story_body(project_item_id, body, token) -> None

Despite the historical ``org`` parameter name, the owner may be either a
GitHub organization login or a personal user login. The adapter checks both
GraphQL roots so the demo can target either kind of Project V2 board.

All HTTP is done via a module-level client factory so tests can inject a fake.
Non-2xx responses and GraphQL `errors` arrays both raise GitHubAPIError.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any, Optional

from alfred.schemas.agent import BoardState, BoardStory

_GRAPHQL_URL = "https://api.github.com/graphql"

_GET_BOARD_QUERY_ORG = """
query($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      items(first: 100) {
        nodes {
          id
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldUserValue {
                users(first: 1) { nodes { login } }
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldLabelValue {
                labels(first: 10) { nodes { name } }
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldIterationValue {
                title
                startDate
                duration
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
          content {
            ... on Issue { title }
            ... on DraftIssue { title }
          }
        }
      }
    }
  }
}
"""

_GET_BOARD_QUERY_USER = """
query($org: String!, $number: Int!) {
  user(login: $org) {
    projectV2(number: $number) {
      items(first: 100) {
        nodes {
          id
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldUserValue {
                users(first: 1) { nodes { login } }
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldLabelValue {
                labels(first: 10) { nodes { name } }
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldIterationValue {
                title
                startDate
                duration
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
          content {
            ... on Issue { title }
            ... on DraftIssue { title }
          }
        }
      }
    }
  }
}
"""

_ADD_ITEM_MUTATION = """
mutation($projectId: ID!, $title: String!, $body: String) {
  addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
    projectItem { id }
  }
}
"""

_GET_PROJECT_ID_QUERY_ORG = """
query($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) { id }
  }
}
"""

_GET_PROJECT_ID_QUERY_USER = """
query($org: String!, $number: Int!) {
  user(login: $org) {
    projectV2(number: $number) { id }
  }
}
"""

_GET_DRAFT_ISSUE_ID_QUERY = """
query($itemId: ID!) {
  node(id: $itemId) {
    ... on ProjectV2Item {
      content {
        ... on DraftIssue { id }
      }
    }
  }
}
"""

_UPDATE_DRAFT_ISSUE_MUTATION = """
mutation($draftIssueId: ID!, $body: String!) {
  updateProjectV2DraftIssue(input: {draftIssueId: $draftIssueId, body: $body}) {
    draftIssue { id }
  }
}
"""


class GitHubAPIError(RuntimeError):
    """Raised on non-2xx responses or GraphQL errors."""


# ---------------------------------------------------------------------------
# HTTP client factory — replaceable for tests
# ---------------------------------------------------------------------------

Client = Any  # httpx.Client


def _default_client_factory(token: str) -> Client:
    import httpx

    return httpx.Client(
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )


_client_factory: Callable[[str], Client] = _default_client_factory


def set_client_factory(factory: Callable[[str], Client]) -> None:
    """Replace the HTTP client factory. Tests use this to inject a fake."""
    global _client_factory
    _client_factory = factory


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _post(client: Client, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    response = client.post(_GRAPHQL_URL, json={"query": query, "variables": variables})
    if response.status_code != 200:
        raise GitHubAPIError(
            f"GitHub returned HTTP {response.status_code}: {response.text[:200]}"
        )
    body: dict[str, Any] = response.json()
    if body.get("errors"):
        messages = "; ".join(e.get("message", str(e)) for e in body["errors"])
        raise GitHubAPIError(f"GraphQL errors: {messages}")
    return body.get("data", {})


def _field_map(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Flatten fieldValues nodes into {field_name: value}."""
    out: dict[str, Any] = {}
    for node in nodes:
        field_info = node.get("field") or {}
        name: str = field_info.get("name", "")
        if not name:
            continue
        if "text" in node:
            out[name] = node["text"]
        elif "name" in node:
            out[name] = node["name"]
        elif "number" in node:
            out[name] = node["number"]
        elif "users" in node:
            logins = [u.get("login") for u in (node["users"].get("nodes") or [])]
            out[name] = logins[0] if logins else None
        elif "labels" in node:
            out[name] = [lb.get("name") for lb in (node["labels"].get("nodes") or [])]
        elif "title" in node and "startDate" in node:
            # Iteration field — store sprint title and date separately
            out[name] = node["title"]
            out[f"{name}__startDate"] = node.get("startDate")
            out[f"{name}__duration"] = node.get("duration")
    return out


def _project_container(data: dict[str, Any]) -> dict[str, Any]:
    """Return the resolved ProjectV2 container from either owner type."""
    direct = data.get("project")
    if isinstance(direct, dict) and direct:
        return direct
    organization = (data.get("organization") or {}).get("projectV2")
    if organization is not None:
        return organization
    user = (data.get("user") or {}).get("projectV2")
    if user is not None:
        return user
    return {}


def _is_owner_resolution_error(exc: GitHubAPIError, owner_type: str) -> bool:
    message = str(exc)
    if owner_type == "organization":
        return "Could not resolve to an Organization with the login of" in message
    if owner_type == "user":
        return (
            "Could not resolve to a User with the login of" in message
            or "Could not resolve to an User with the login of" in message
        )
    return False


def _query_project_container(
    client: Client,
    *,
    owner: str,
    project_number: int,
    org_query: str,
    user_query: str,
) -> dict[str, Any]:
    """Resolve a ProjectV2 container for either an org-owned or user-owned board."""
    variables = {"org": owner, "number": project_number}
    try:
        data = _post(client, org_query, variables)
    except GitHubAPIError as exc:
        if not _is_owner_resolution_error(exc, "organization"):
            raise
    else:
        container = _project_container(data)
        if container:
            return container
        if "organization" in data and data.get("organization") is not None:
            raise GitHubAPIError("Could not resolve project container from owner/project_number")

    try:
        data = _post(client, user_query, variables)
    except GitHubAPIError as exc:
        if _is_owner_resolution_error(exc, "user"):
            raise GitHubAPIError(
                f"Could not resolve project owner {owner!r} as either an organization or a user"
            ) from exc
        raise

    container = _project_container(data)
    if container:
        return container
    if "user" in data and data.get("user") is not None:
        raise GitHubAPIError("Could not resolve project container from owner/project_number")
    raise GitHubAPIError("Could not resolve project container from owner/project_number")


def _parse_board_state(data: dict[str, Any]) -> BoardState:
    items = (_project_container(data).get("items", {}) or {}).get("nodes", []) or []

    stories: list[BoardStory] = []
    sprint_number: Optional[int] = None
    sprint_start: Optional[date] = None
    sprint_end: Optional[date] = None

    for item in items:
        item_id: str = item.get("id", "")
        content = item.get("content") or {}
        title: str = content.get("title", "")
        fv_nodes = (item.get("fieldValues") or {}).get("nodes") or []
        fields = _field_map(fv_nodes)

        status: str = str(fields.get("Status", ""))
        points_raw = fields.get("Story Points") or fields.get("Points")
        points: Optional[int] = int(points_raw) if points_raw is not None else None
        assignee: Optional[str] = fields.get("Assignees") or fields.get("Assignee")
        labels_raw = fields.get("Labels") or []
        labels: list[str] = [labels_raw] if isinstance(labels_raw, str) else labels_raw

        if sprint_number is None:
            raw_iter = fields.get("Sprint__startDate") or fields.get("Iteration__startDate")
            raw_dur = fields.get("Sprint__duration") or fields.get("Iteration__duration")
            sprint_title = fields.get("Sprint") or fields.get("Iteration")
            if raw_iter:
                try:
                    sprint_start = date.fromisoformat(raw_iter)
                    if raw_dur:
                        sprint_end = sprint_start + timedelta(weeks=int(raw_dur))
                except (ValueError, TypeError):
                    pass
            if sprint_title:
                m = re.search(r"\d+", str(sprint_title))
                if m:
                    sprint_number = int(m.group())

        stories.append(
            BoardStory(
                id=item_id,
                title=title,
                status=status,
                story_points=points,
                assignee=assignee,
                labels=labels,
            )
        )

    return BoardState(
        sprint_number=sprint_number,
        sprint_start=sprint_start,
        sprint_end=sprint_end,
        stories=stories,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_board_state(org: str, project_number: int, token: str) -> BoardState:
    """Return a read-only snapshot of the GitHub Projects V2 board."""
    client = _client_factory(token)
    project = _query_project_container(
        client,
        owner=org,
        project_number=project_number,
        org_query=_GET_BOARD_QUERY_ORG,
        user_query=_GET_BOARD_QUERY_USER,
    )
    return _parse_board_state({"project": project})


def create_story(
    org: str,
    project_number: int,
    title: str,
    token: str,
    *,
    body: str = "",
) -> str:
    """Create a draft issue on the board. Returns the new item id.

    Authorization (HITL approval) is enforced at the orchestrator layer.
    This function executes the write unconditionally once called.
    """
    client = _client_factory(token)

    try:
        project = _query_project_container(
            client,
            owner=org,
            project_number=project_number,
            org_query=_GET_PROJECT_ID_QUERY_ORG,
            user_query=_GET_PROJECT_ID_QUERY_USER,
        )
    except GitHubAPIError as exc:
        if "project container" in str(exc):
            raise GitHubAPIError("Could not resolve project id from owner/project_number") from exc
        raise
    project_id: str = project.get("id", "")
    if not project_id:
        raise GitHubAPIError("Could not resolve project id from owner/project_number")

    mut_data = _post(
        client,
        _ADD_ITEM_MUTATION,
        {"projectId": project_id, "title": title, "body": body},
    )
    item_id: str = (
        mut_data.get("addProjectV2DraftIssue", {})
        .get("projectItem", {})
        .get("id", "")
    )
    if not item_id:
        raise GitHubAPIError("Mutation succeeded but returned no item id")
    return item_id


def update_story_body(project_item_id: str, body: str, token: str) -> None:
    """Update the body of an existing draft issue by project item id."""
    client = _client_factory(token)
    data = _post(client, _GET_DRAFT_ISSUE_ID_QUERY, {"itemId": project_item_id})
    draft_issue = ((data.get("node") or {}).get("content") or {})
    draft_issue_id = draft_issue.get("id", "")
    if not draft_issue_id:
        raise GitHubAPIError(
            f"Could not resolve DraftIssue id from project item {project_item_id!r}"
        )
    _post(
        client,
        _UPDATE_DRAFT_ISSUE_MUTATION,
        {"draftIssueId": draft_issue_id, "body": body},
    )
