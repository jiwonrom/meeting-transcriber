"""트랜스크립트 메타데이터 인덱스 관리."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime
from typing import Any

from meeting_transcriber.utils.constants import INDEX_FILE, INDEX_VERSION


class MetadataIndex:
    """워크스페이스 내 트랜스크립트 메타데이터를 인덱싱한다.

    index.json 파일을 통해 빠른 조회와 필터링을 지원한다.
    """

    def __init__(self, workspace_root: pathlib.Path) -> None:
        """MetadataIndex를 초기화한다.

        Args:
            workspace_root: 워크스페이스 루트 경로
        """
        self._index_path = workspace_root / INDEX_FILE
        self._data = self._load_or_create()
        self._save()

    def _load_or_create(self) -> dict[str, Any]:
        """인덱스 파일을 로드하거나 새로 생성한다.

        Returns:
            인덱스 데이터 딕셔너리
        """
        if self._index_path.exists():
            try:
                with open(self._index_path, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {"version": INDEX_VERSION, "updated_at": "", "entries": {}}

    def update_entry(
        self, transcript_path: pathlib.Path, transcript: dict[str, Any]
    ) -> None:
        """트랜스크립트 엔트리를 추가 또는 갱신한다.

        Args:
            transcript_path: transcript.json 파일 경로
            transcript: 트랜스크립트 딕셔너리
        """
        meta = transcript.get("metadata", {})
        segments = transcript.get("segments", [])

        # summary_snippet 처리: 문자열이면 100자 잘라서, dict이면 빈 문자열
        raw_summary = meta.get("summary", "")
        if isinstance(raw_summary, str):
            summary_snippet = raw_summary[:100]
        else:
            summary_snippet = ""

        entry: dict[str, Any] = {
            "title": meta.get("title", "Untitled"),
            "created_at": meta.get("created_at", ""),
            "duration_seconds": meta.get("duration_seconds", 0),
            "languages": [meta["language"]] if "language" in meta else [],
            "folder": transcript_path.parent.parent.name,
            "template_type": meta.get("template_type"),
            "keywords": meta.get("keywords", []),
            "summary_snippet": summary_snippet,
            "segment_count": len(segments),
            "word_count": sum(
                len(seg.get("text", "").split()) for seg in segments
            ),
        }

        key = self._relative_key(transcript_path)
        self._data["entries"][key] = entry
        self._data["updated_at"] = datetime.now(tz=UTC).isoformat()
        self._save()

    def remove_entry(self, transcript_path: pathlib.Path) -> None:
        """트랜스크립트 엔트리를 삭제한다.

        Args:
            transcript_path: transcript.json 파일 경로
        """
        key = self._relative_key(transcript_path)
        if key in self._data["entries"]:
            del self._data["entries"][key]
            self._save()

    def get_entry(self, transcript_path: pathlib.Path) -> dict[str, Any] | None:
        """트랜스크립트 엔트리를 조회한다.

        Args:
            transcript_path: transcript.json 파일 경로

        Returns:
            엔트리 딕셔너리 또는 None
        """
        key = self._relative_key(transcript_path)
        return self._data["entries"].get(key)

    def entries(self) -> dict[str, dict[str, Any]]:
        """모든 엔트리를 반환한다.

        Returns:
            엔트리 딕셔너리의 복사본
        """
        return dict(self._data["entries"])

    def rebuild(self, workspace_root: pathlib.Path) -> None:
        """워크스페이스를 스캔하여 인덱스를 재구축한다.

        Args:
            workspace_root: 워크스페이스 루트 경로
        """
        self._data["entries"] = {}
        for transcript_file in workspace_root.rglob("transcript.json"):
            try:
                with open(transcript_file, encoding="utf-8") as f:
                    transcript: dict[str, Any] = json.load(f)
                self.update_entry(transcript_file, transcript)
            except (json.JSONDecodeError, OSError):
                continue

    def _save(self) -> None:
        """인덱스를 파일에 저장한다."""
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _relative_key(self, transcript_path: pathlib.Path) -> str:
        """transcript 경로를 워크스페이스 루트 상대 경로 문자열로 변환한다.

        Args:
            transcript_path: transcript.json 파일 경로

        Returns:
            상대 경로 문자열
        """
        return str(transcript_path.relative_to(self._index_path.parent))
