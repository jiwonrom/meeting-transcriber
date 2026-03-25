"""workspace 모듈 단위 테스트."""
from __future__ import annotations

import pathlib

import pytest

from meeting_transcriber.storage.workspace import WorkspaceManager


@pytest.fixture
def workspace(tmp_path: pathlib.Path) -> WorkspaceManager:
    """임시 워크스페이스를 생성한다."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    return ws


def test_list_folders_empty(workspace: WorkspaceManager) -> None:
    """빈 워크스페이스에서 빈 리스트를 반환하는지 확인."""
    folders = workspace.list_folders()
    assert folders == []


def test_create_folder(workspace: WorkspaceManager) -> None:
    """폴더 생성이 파일시스템에 반영되는지 확인."""
    path = workspace.create_folder("TestMeeting")
    assert path.exists()
    assert path.is_dir()
    assert path.name == "TestMeeting"


def test_create_folder_already_exists(workspace: WorkspaceManager) -> None:
    """이미 존재하는 폴더 생성 시 FileExistsError를 발생시키는지 확인."""
    workspace.create_folder("Duplicate")
    with pytest.raises(FileExistsError):
        workspace.create_folder("Duplicate")


def test_create_folder_invalid_name(workspace: WorkspaceManager) -> None:
    """유효하지 않은 이름에 ValueError를 발생시키는지 확인."""
    with pytest.raises(ValueError, match="empty"):
        workspace.create_folder("")
    with pytest.raises(ValueError, match="path separators"):
        workspace.create_folder("a/b")
    with pytest.raises(ValueError, match="dot"):
        workspace.create_folder(".hidden")
    with pytest.raises(ValueError, match="reserved"):
        workspace.create_folder("models")


def test_list_folders(workspace: WorkspaceManager) -> None:
    """생성된 폴더가 목록에 나타나는지 확인."""
    workspace.create_folder("Alpha")
    workspace.create_folder("Beta")

    folders = workspace.list_folders()
    names = [f.name for f in folders]
    assert "Alpha" in names
    assert "Beta" in names
    assert len(folders) == 2


def test_list_folders_sorted(workspace: WorkspaceManager) -> None:
    """폴더 목록이 이름순으로 정렬되는지 확인."""
    workspace.create_folder("Zebra")
    workspace.create_folder("Apple")

    folders = workspace.list_folders()
    assert folders[0].name == "Apple"
    assert folders[1].name == "Zebra"


def test_rename_folder(workspace: WorkspaceManager) -> None:
    """폴더 이름 변경이 동작하는지 확인."""
    workspace.create_folder("OldName")
    # 내부에 파일 생성
    (workspace.root / "OldName" / "test.txt").write_text("data")

    new_path = workspace.rename_folder("OldName", "NewName")
    assert new_path.exists()
    assert not (workspace.root / "OldName").exists()
    # 내부 파일 유지 확인
    assert (new_path / "test.txt").read_text() == "data"


def test_rename_folder_not_found(workspace: WorkspaceManager) -> None:
    """존재하지 않는 폴더 이름 변경 시 FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        workspace.rename_folder("Ghost", "NewGhost")


def test_rename_folder_target_exists(workspace: WorkspaceManager) -> None:
    """대상 이름이 이미 존재할 때 FileExistsError."""
    workspace.create_folder("A")
    workspace.create_folder("B")
    with pytest.raises(FileExistsError):
        workspace.rename_folder("A", "B")


def test_delete_folder(workspace: WorkspaceManager) -> None:
    """폴더 삭제가 파일시스템에 반영되는지 확인."""
    workspace.create_folder("ToDelete")
    (workspace.root / "ToDelete" / "file.txt").write_text("x")

    workspace.delete_folder("ToDelete")
    assert not (workspace.root / "ToDelete").exists()


def test_delete_folder_not_found(workspace: WorkspaceManager) -> None:
    """존재하지 않는 폴더 삭제 시 FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        workspace.delete_folder("Nonexistent")


def test_ensure_default_folders(workspace: WorkspaceManager) -> None:
    """기본 폴더(Work, Personal)가 생성되는지 확인."""
    workspace.ensure_default_folders()
    assert (workspace.root / "Work").is_dir()
    assert (workspace.root / "Personal").is_dir()


def test_ensure_default_folders_idempotent(workspace: WorkspaceManager) -> None:
    """이미 존재하는 기본 폴더에 대해 에러 없이 동작하는지 확인."""
    workspace.ensure_default_folders()
    workspace.ensure_default_folders()  # 두 번 호출해도 에러 없음
    assert (workspace.root / "Work").is_dir()


def test_list_transcripts(workspace: WorkspaceManager) -> None:
    """폴더 내 transcript 목록을 반환하는지 확인."""
    folder = workspace.create_folder("Meetings")
    # 두 개의 transcript 서브폴더 생성
    meeting1 = folder / "Meeting-1"
    meeting1.mkdir()
    (meeting1 / "transcript.json").write_text("{}")

    meeting2 = folder / "Meeting-2"
    meeting2.mkdir()
    (meeting2 / "transcript.json").write_text("{}")

    transcripts = workspace.list_transcripts("Meetings")
    assert len(transcripts) == 2


def test_list_transcripts_folder_not_found(workspace: WorkspaceManager) -> None:
    """존재하지 않는 폴더의 transcript 조회 시 FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        workspace.list_transcripts("Ghost")


def test_folder_info_transcript_count(workspace: WorkspaceManager) -> None:
    """FolderInfo.transcript_count가 정확한지 확인."""
    folder = workspace.create_folder("CountTest")
    sub = folder / "Sub1"
    sub.mkdir()
    (sub / "transcript.json").write_text("{}")

    folders = workspace.list_folders()
    count_test = next(f for f in folders if f.name == "CountTest")
    assert count_test.transcript_count == 1


def test_ignored_dirs_not_listed(workspace: WorkspaceManager) -> None:
    """models 등 예약 디렉토리가 목록에 나타나지 않는지 확인."""
    (workspace.root / "models").mkdir(exist_ok=True)
    (workspace.root / ".hidden_dir").mkdir()
    workspace.create_folder("Visible")

    folders = workspace.list_folders()
    names = [f.name for f in folders]
    assert "models" not in names
    assert ".hidden_dir" not in names
    assert "Visible" in names
