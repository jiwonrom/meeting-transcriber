"""회의 템플릿 관리 — 빌트인 및 사용자 정의 YAML 템플릿."""

from __future__ import annotations

import importlib.resources
import logging
import pathlib
import shutil
from dataclasses import dataclass, field

import yaml

from meeting_transcriber.utils.constants import TEMPLATES_DIR

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MeetingTemplate:
    """회의 템플릿 데이터 클래스.

    YAML 파일에서 로드된 템플릿 정보를 담는다.

    Attributes:
        name: 템플릿 이름 (예: "Team Meeting")
        description: 템플릿 설명
        sections: 구조화 섹션 목록 [{key, label}, ...]
        prompt: AI 프롬프트 텍스트 ({speaker_instruction}, {language_instruction} 플레이스홀더 포함)
        icon: 아이콘 식별자
        file_path: 원본 YAML 파일 경로
    """

    name: str
    description: str = ""
    sections: list[dict[str, str]] = field(default_factory=list)
    prompt: str = ""
    icon: str = ""
    file_path: str = ""

    @property
    def section_keys(self) -> list[str]:
        """섹션 키 목록을 반환한다.

        Returns:
            섹션 key 문자열 리스트
        """
        return [s["key"] for s in self.sections]

    @property
    def is_structured(self) -> bool:
        """구조화 템플릿 여부를 반환한다.

        Returns:
            sections가 비어있지 않으면 True
        """
        return len(self.sections) > 0


class TemplateManager:
    """회의 템플릿을 로드하고 관리한다.

    빌트인 YAML 템플릿과 사용자 정의 템플릿을 모두 지원한다.
    """

    def __init__(self) -> None:
        """TemplateManager를 초기화한다."""
        self._templates: dict[str, MeetingTemplate] = {}

    def ensure_templates(self) -> None:
        """템플릿 디렉토리를 생성하고 빌트인 템플릿을 복사한다.

        TEMPLATES_DIR이 없으면 생성하고, 빌트인 YAML 파일을
        사용자 디렉토리에 복사한다 (이미 존재하면 건너뜀).
        """
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        builtin_pkg = importlib.resources.files(
            "meeting_transcriber.ai.builtin_templates"
        )
        for resource in builtin_pkg.iterdir():
            if not resource.name.endswith(".yaml"):
                continue
            dest = TEMPLATES_DIR / resource.name
            if dest.exists():
                continue
            with importlib.resources.as_file(resource) as src_path:
                shutil.copy2(src_path, dest)

    def load_all(self) -> dict[str, MeetingTemplate]:
        """모든 YAML 템플릿을 로드한다.

        TEMPLATES_DIR에서 *.yaml 파일을 탐색하여 로드한다.
        잘못된 YAML 파일은 건너뛴다.

        Returns:
            {stem_key: MeetingTemplate} 딕셔너리
        """
        self._templates.clear()

        for yaml_path in sorted(TEMPLATES_DIR.glob("*.yaml")):
            try:
                template = self._load_one(yaml_path)
                self._templates[yaml_path.stem] = template
            except Exception:
                logger.warning("Invalid template skipped: %s", yaml_path)

        return dict(self._templates)

    def _load_one(self, path: pathlib.Path) -> MeetingTemplate:
        """단일 YAML 파일에서 MeetingTemplate을 로드한다.

        Args:
            path: YAML 파일 경로

        Returns:
            MeetingTemplate 인스턴스

        Raises:
            ValueError: name 또는 prompt 키가 없을 때.
            yaml.YAMLError: YAML 파싱 실패 시.
        """
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Invalid template format: {path}")

        name = data.get("name")
        prompt = data.get("prompt")
        if not name or not prompt:
            raise ValueError(f"Template missing name or prompt: {path}")

        return MeetingTemplate(
            name=name,
            description=data.get("description", ""),
            sections=data.get("sections") or [],
            prompt=prompt,
            icon=data.get("icon", ""),
            file_path=str(path),
        )

    def get(self, key: str) -> MeetingTemplate | None:
        """캐시에서 템플릿을 키로 조회한다.

        Args:
            key: 템플릿 stem 키 (예: "team_meeting")

        Returns:
            MeetingTemplate 또는 None
        """
        return self._templates.get(key)

    def render_prompt(
        self,
        template: MeetingTemplate,
        *,
        language: str = "auto",
        speakers: dict[str, str] | None = None,
    ) -> str:
        """템플릿 프롬프트를 렌더링한다.

        플레이스홀더 {speaker_instruction}과 {language_instruction}을 치환한다.

        Args:
            template: 렌더링할 MeetingTemplate
            language: 응답 언어 ("auto"면 전사 언어 유지)
            speakers: 화자 매핑 딕셔너리 (예: {"SPEAKER_00": "Alice"})

        Returns:
            렌더링된 프롬프트 문자열
        """
        if speakers:
            names = ", ".join(speakers.values())
            speaker_instruction = f"The speakers in this meeting are: {names}. "
        else:
            speaker_instruction = ""

        if language != "auto":
            language_instruction = f"Respond in {language}."
        else:
            language_instruction = "Respond in the same language as the transcript."

        return template.prompt.format(
            speaker_instruction=speaker_instruction,
            language_instruction=language_instruction,
        )
