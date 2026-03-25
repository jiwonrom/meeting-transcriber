"""onboarding 모듈 단위 테스트."""
from __future__ import annotations

from unittest.mock import patch

from meeting_transcriber.ui.onboarding import OnboardingWizard


def test_onboarding_creation(qtbot: object) -> None:
    """온보딩 위저드가 정상 생성되는지 확인."""
    wizard = OnboardingWizard()
    qtbot.addWidget(wizard)  # type: ignore[union-attr]

    assert wizard.windowTitle() == "Meeting Transcriber — Setup"
    assert wizard.current_page == 0


def test_onboarding_language_page(qtbot: object) -> None:
    """언어 선택 페이지에 모든 언어 옵션이 있는지 확인."""
    wizard = OnboardingWizard()
    qtbot.addWidget(wizard)  # type: ignore[union-attr]

    buttons = wizard._lang_group.buttons()
    lang_codes = [btn.property("lang_code") for btn in buttons]

    assert "en" in lang_codes
    assert "ko" in lang_codes
    assert "zh" in lang_codes
    assert "ja" in lang_codes
    assert "auto" in lang_codes


def test_onboarding_default_language_is_auto(qtbot: object) -> None:
    """기본 선택이 auto인지 확인."""
    wizard = OnboardingWizard()
    qtbot.addWidget(wizard)  # type: ignore[union-attr]

    assert wizard.selected_language == "auto"


def test_onboarding_go_next(qtbot: object) -> None:
    """Next 버튼으로 페이지가 전환되는지 확인."""
    wizard = OnboardingWizard()
    qtbot.addWidget(wizard)  # type: ignore[union-attr]

    assert wizard.current_page == 0

    with patch(
        "meeting_transcriber.ui.onboarding.is_model_downloaded",
        return_value=True,
    ):
        wizard._go_next()  # 0 -> 1
        assert wizard.current_page == 1

        wizard._go_next()  # 1 -> 2
        assert wizard.current_page == 2


def test_onboarding_go_back(qtbot: object) -> None:
    """Back 버튼으로 이전 페이지로 돌아가는지 확인."""
    wizard = OnboardingWizard()
    qtbot.addWidget(wizard)  # type: ignore[union-attr]

    with patch(
        "meeting_transcriber.ui.onboarding.is_model_downloaded",
        return_value=True,
    ):
        wizard._go_next()
        assert wizard.current_page == 1
        wizard._go_back()
        assert wizard.current_page == 0


def test_onboarding_skips_download_if_model_exists(qtbot: object) -> None:
    """모델이 이미 있으면 다운로드를 건너뛰는지 확인."""
    wizard = OnboardingWizard()
    qtbot.addWidget(wizard)  # type: ignore[union-attr]

    with patch(
        "meeting_transcriber.ui.onboarding.is_model_downloaded",
        return_value=True,
    ):
        wizard._start_download()
        assert wizard._progress_bar.value() == 100
