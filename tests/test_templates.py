"""meeting template 시스템 단위 테스트."""

from __future__ import annotations

import pathlib
import textwrap

import pytest

from meeting_transcriber.ai.templates import MeetingTemplate, TemplateManager
from meeting_transcriber.utils.constants import BUILTIN_TEMPLATE_NAMES


# -- TemplateManager 로드 테스트 --


def test_load_builtin_templates(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TemplateManager.load_all()이 5개 빌트인 템플릿을 반환하는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()
    assert len(templates) == 5
    for name in BUILTIN_TEMPLATE_NAMES:
        assert name in templates


def test_template_has_required_fields(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """각 MeetingTemplate에 필수 필드가 있는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()

    # General: 비구조화 (빈 sections)
    general = templates["general"]
    assert general.name == "General"
    assert general.prompt != ""
    assert general.sections == []

    # Team Meeting: 구조화 (3개 sections)
    team = templates["team_meeting"]
    assert team.name == "Team Meeting"
    assert len(team.sections) == 3


def test_is_structured(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """General은 is_structured=False, Team Meeting은 True인지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()

    assert templates["general"].is_structured is False
    assert templates["team_meeting"].is_structured is True


def test_section_keys(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Team Meeting의 section_keys가 올바른지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()

    assert templates["team_meeting"].section_keys == [
        "decisions",
        "action_items",
        "next_steps",
    ]


def test_render_prompt_with_speakers(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_prompt에 speakers를 전달하면 이름이 프롬프트에 포함되는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()

    prompt = mgr.render_prompt(
        templates["team_meeting"],
        language="auto",
        speakers={"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"},
    )
    assert "Alice" in prompt
    assert "Bob" in prompt


def test_render_prompt_without_speakers(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_prompt에 speakers 없이 호출하면 speaker instruction이 비어 있는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()

    prompt = mgr.render_prompt(templates["general"], language="auto", speakers=None)
    assert "Speaker" not in prompt


def test_render_prompt_language(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_prompt에 language='ko'를 전달하면 응답 언어 지시가 포함되는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()
    templates = mgr.load_all()

    prompt = mgr.render_prompt(templates["general"], language="ko", speakers=None)
    assert "Respond in ko" in prompt


def test_custom_template_load(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """사용자 정의 YAML 템플릿이 load_all()에서 로드되는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()

    # 커스텀 템플릿 작성
    custom_yaml = textwrap.dedent("""\
        name: "Custom"
        description: "A custom template"
        sections: []
        prompt: "Summarize this: {speaker_instruction}{language_instruction}"
    """)
    (tmp_path / "custom.yaml").write_text(custom_yaml, encoding="utf-8")

    templates = mgr.load_all()
    assert "custom" in templates
    assert templates["custom"].name == "Custom"


def test_invalid_yaml_skipped(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """잘못된 YAML 파일은 건너뛰고 다른 템플릿은 정상 로드되는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()

    # 잘못된 YAML 파일 작성
    (tmp_path / "broken.yaml").write_text("{{invalid yaml: [", encoding="utf-8")

    templates = mgr.load_all()
    assert "broken" not in templates
    assert len(templates) >= 5  # 빌트인 5개는 정상 로드


def test_ensure_templates_creates_dir(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ensure_templates()가 디렉토리가 없을 때 생성하는지 확인."""
    target = tmp_path / "new_templates"
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", target)
    mgr = TemplateManager()
    mgr.ensure_templates()
    assert target.is_dir()


def test_ensure_templates_copies_builtins(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ensure_templates()가 5개 빌트인 YAML을 사용자 디렉토리에 복사하는지 확인."""
    monkeypatch.setattr("meeting_transcriber.ai.templates.TEMPLATES_DIR", tmp_path)
    mgr = TemplateManager()
    mgr.ensure_templates()

    yaml_files = list(tmp_path.glob("*.yaml"))
    assert len(yaml_files) == 5
