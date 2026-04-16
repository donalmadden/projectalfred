"""
Story Generator — produces validated draft stories from the handover corpus.

Phase 4 implementation will:
- Retrieve relevant corpus chunks via RAG
- Generate candidate stories and apply the quality rubric
- Return only stories that pass the rubric; board writes require HITL approval
"""
from alfred.schemas.agent import StoryGeneratorInput, StoryGeneratorOutput


def run_story_generator(input: StoryGeneratorInput) -> StoryGeneratorOutput:
    """Generate rubric-validated draft stories. Never writes to the board directly."""
    raise NotImplementedError
