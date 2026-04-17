"""
GitHub Projects V2 GraphQL adapter.

Two public functions:
  get_board_state(org, project_number, token) -> BoardState
  create_story(org, project_number, title, token) -> str  (returns new item id)

All HTTP is done via a module-level client factory so tests can inject a fake.
Non-2xx responses and GraphQL `errors` arrays both raise GitHubAPIError.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Callable, Optional

from alfred.schemas.agent import BoardState, BoardStory

_GRAPHQL_URL = "https://api.github.com/graphql"

_GET_BOARD_QUERY = """
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

_ADD_ITEM_MUTATION = """
mutation($projectId: ID!, $title: String!) {
  addProjectV2DraftIssue(input: {projectId: $projectId, title: $title}) {
    projectItem { id }
  }
}
"""

_GET_PROJECT_ID_QUERY = """
query($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) { id }
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


def _parse_board_state(data: dict[str, Any]) -> BoardState:
    items = (
        data.get("organization", {})
        .get("projectV2", {})
        .get("items", {})
        .get("nodes", [])
    ) or []

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
    data = _post(client, _GET_BOARD_QUERY, {"org": org, "number": project_number})
    return _parse_board_state(data)


def create_story(org: str, project_number: int, title: str, token: str) -> str:
    """Create a draft issue on the board. Returns the new item id.

    Authorization (HITL approval) is enforced at the orchestrator layer.
    This function executes the write unconditionally once called.
    """
    client = _client_factory(token)

    id_data = _post(
        client, _GET_PROJECT_ID_QUERY, {"org": org, "number": project_number}
    )
    project_id: str = (
        (id_data.get("organization") or {}).get("projectV2") or {}
    ).get("id", "")
    if not project_id:
        raise GitHubAPIError("Could not resolve project id from org/project_number")

    mut_data = _post(
        client, _ADD_ITEM_MUTATION, {"projectId": project_id, "title": title}
    )
    item_id: str = (
        mut_data.get("addProjectV2DraftIssue", {})
        .get("projectItem", {})
        .get("id", "")
    )
    if not item_id:
        raise GitHubAPIError("Mutation succeeded but returned no item id")
    return item_id
