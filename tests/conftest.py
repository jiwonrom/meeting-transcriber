"""공통 테스트 fixture."""
from __future__ import annotations

import pathlib

import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    """테스트 fixture 디렉토리 경로."""
    return FIXTURES_DIR


@pytest.fixture
def tmp_workspace(tmp_path: pathlib.Path) -> pathlib.Path:
    """임시 워크스페이스 디렉토리."""
    workspace = tmp_path / ".meeting_transcriber"
    workspace.mkdir()
    (workspace / "models").mkdir()
    return workspace
