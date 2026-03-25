"""워크스페이스 폴더 구조 관리 — 파일시스템 1:1 대응."""
from __future__ import annotations

import pathlib
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime

from meeting_transcriber.utils.config import ensure_workspace
from meeting_transcriber.utils.constants import DEFAULT_WORKSPACE_DIR

_IGNORED_DIRS = {"models", ".DS_Store", "__pycache__"}
_IGNORED_FILES = {"settings.json", "workspace.json"}


@dataclass(frozen=True)
class FolderInfo:
    """워크스페이스 폴더 정보."""

    name: str
    path: pathlib.Path
    transcript_count: int
    created_at: str


class WorkspaceManager:
    """워크스페이스 폴더 구조를 관리한다.

    ~/.meeting_transcriber/ 하위 폴더를 CRUD하고,
    각 폴더 내 transcript.json 파일을 탐색한다.
    """

    def __init__(self, workspace_dir: pathlib.Path | None = None) -> None:
        """WorkspaceManager를 초기화한다.

        Args:
            workspace_dir: 워크스페이스 루트 경로. None이면 기본값 사용.
        """
        self._root = workspace_dir or DEFAULT_WORKSPACE_DIR
        ensure_workspace()

    @property
    def root(self) -> pathlib.Path:
        """워크스페이스 루트 경로."""
        return self._root

    def list_folders(self) -> list[FolderInfo]:
        """워크스페이스 최상위 폴더 목록을 반환한다.

        Returns:
            폴더 정보 리스트 (이름순 정렬)
        """
        folders: list[FolderInfo] = []
        if not self._root.exists():
            return folders

        for entry in sorted(self._root.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name in _IGNORED_DIRS or entry.name.startswith("."):
                continue

            transcripts = self._count_transcripts(entry)
            stat = entry.stat()
            created = datetime.fromtimestamp(stat.st_birthtime, tz=UTC).isoformat()

            folders.append(FolderInfo(
                name=entry.name,
                path=entry,
                transcript_count=transcripts,
                created_at=created,
            ))

        return folders

    def list_transcripts(self, folder_name: str) -> list[pathlib.Path]:
        """폴더 내 transcript.json 파일 목록을 반환한다.

        Args:
            folder_name: 폴더 이름

        Returns:
            transcript.json 파일 경로 리스트 (수정 시간 역순)

        Raises:
            FileNotFoundError: 폴더가 존재하지 않을 때
        """
        folder_path = self._root / folder_name
        if not folder_path.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder_name}")

        transcripts: list[pathlib.Path] = []
        for sub in folder_path.iterdir():
            if sub.is_dir():
                transcript_file = sub / "transcript.json"
                if transcript_file.exists():
                    transcripts.append(transcript_file)

        transcripts.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return transcripts

    def create_folder(self, name: str) -> pathlib.Path:
        """새 폴더를 생성한다.

        Args:
            name: 폴더 이름

        Returns:
            생성된 폴더 경로

        Raises:
            FileExistsError: 이미 존재하는 폴더일 때
            ValueError: 유효하지 않은 이름일 때
        """
        self._validate_folder_name(name)
        folder_path = self._root / name
        if folder_path.exists():
            raise FileExistsError(f"Folder already exists: {name}")

        folder_path.mkdir(parents=True)
        return folder_path

    def rename_folder(self, old_name: str, new_name: str) -> pathlib.Path:
        """폴더 이름을 변경한다.

        Args:
            old_name: 현재 폴더 이름
            new_name: 새 폴더 이름

        Returns:
            변경된 폴더 경로

        Raises:
            FileNotFoundError: 원본 폴더가 없을 때
            FileExistsError: 새 이름의 폴더가 이미 존재할 때
            ValueError: 유효하지 않은 이름일 때
        """
        self._validate_folder_name(new_name)
        old_path = self._root / old_name
        new_path = self._root / new_name

        if not old_path.is_dir():
            raise FileNotFoundError(f"Folder not found: {old_name}")
        if new_path.exists():
            raise FileExistsError(f"Folder already exists: {new_name}")

        old_path.rename(new_path)
        return new_path

    def delete_folder(self, name: str) -> None:
        """폴더를 삭제한다. 내부 파일도 모두 삭제된다.

        Args:
            name: 삭제할 폴더 이름

        Raises:
            FileNotFoundError: 폴더가 존재하지 않을 때
        """
        folder_path = self._root / name
        if not folder_path.is_dir():
            raise FileNotFoundError(f"Folder not found: {name}")

        shutil.rmtree(folder_path)

    def ensure_default_folders(self) -> None:
        """기본 폴더(Work, Personal)가 없으면 생성한다."""
        for name in ("Work", "Personal"):
            folder = self._root / name
            if not folder.exists():
                folder.mkdir(parents=True)

    def _count_transcripts(self, folder_path: pathlib.Path) -> int:
        """폴더 내 transcript.json 파일 수를 센다."""
        count = 0
        if not folder_path.is_dir():
            return count
        for sub in folder_path.iterdir():
            if sub.is_dir() and (sub / "transcript.json").exists():
                count += 1
        return count

    @staticmethod
    def _validate_folder_name(name: str) -> None:
        """폴더 이름이 유효한지 검증한다.

        Raises:
            ValueError: 빈 이름, 경로 구분자 포함, 예약어 등
        """
        if not name or not name.strip():
            raise ValueError("Folder name cannot be empty")
        if "/" in name or "\\" in name:
            raise ValueError("Folder name cannot contain path separators")
        if name.startswith("."):
            raise ValueError("Folder name cannot start with a dot")
        if name in _IGNORED_DIRS:
            raise ValueError(f"'{name}' is a reserved name")
