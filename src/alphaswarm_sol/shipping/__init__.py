"""Shipping skills and agents for end-user distribution via `alphaswarm init`."""

from pathlib import Path


def get_shipped_skills_path() -> Path:
    """Return path to shipped skills directory.

    Returns:
        Path to the skills/ subdirectory containing skill markdown files
        distributed to end-user projects.
    """
    return Path(__file__).parent / "skills"


def get_shipped_agents_path() -> Path:
    """Return path to shipped agents directory.

    Returns:
        Path to the agents/ subdirectory containing agent markdown files
        distributed to end-user projects.
    """
    return Path(__file__).parent / "agents"
