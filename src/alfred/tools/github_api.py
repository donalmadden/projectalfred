"""
GitHub Projects V2 GraphQL adapter.

Phase 4 implementation will:
- Read board state via GraphQL
- Write stories (gated by HITL approval)
- Query velocity history
"""
from alfred.schemas.agent import BoardState, BoardStory


def get_board_state(org: str, project_number: int, token: str) -> BoardState:
    raise NotImplementedError


def create_story(org: str, project_number: int, story: BoardStory, token: str) -> str:
    raise NotImplementedError
