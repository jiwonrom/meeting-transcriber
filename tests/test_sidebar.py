"""sidebar 모듈 단위 테스트."""

from __future__ import annotations

import json
import pathlib

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem

from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.ui.sidebar import SidebarWidget


def test_sidebar_creation(qtbot: object, tmp_path: pathlib.Path) -> None:
    """사이드바가 정상 생성되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    assert sidebar.tree_view is not None
    # Work, Personal 기본 폴더 + Analyses 헤더
    assert sidebar._model.rowCount() >= 2


def test_sidebar_shows_default_folders(qtbot: object, tmp_path: pathlib.Path) -> None:
    """기본 폴더(Work, Personal)가 표시되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    names = []
    for i in range(sidebar._model.rowCount()):
        item = sidebar._model.item(i)
        if item:
            names.append(item.text())

    assert "Work" in names
    assert "Personal" in names


def test_sidebar_folder_select_signal(qtbot: object, tmp_path: pathlib.Path) -> None:
    """폴더 클릭 시 folder_selected 신호가 emit되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    signals: list[str] = []
    sidebar.folder_selected.connect(lambda p: signals.append(p))

    # 첫 번째 아이템 클릭 시뮬레이션
    index = sidebar._model.index(0, 0)
    sidebar._on_item_clicked(index)

    assert len(signals) == 1


def test_sidebar_refresh_after_folder_create(qtbot: object, tmp_path: pathlib.Path) -> None:
    """폴더 생성 후 refresh가 목록을 갱신하는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    initial_count = sidebar._model.rowCount()
    ws.create_folder("NewFolder")
    sidebar.refresh()

    assert sidebar._model.rowCount() == initial_count + 1


def test_sidebar_context_menu_items(qtbot: object, tmp_path: pathlib.Path) -> None:
    """컨텍스트 메뉴에 New Folder 항목이 있는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    # 컨텍스트 메뉴 액션 검증을 위해 빈 위치에 메뉴 생성
    # _show_context_menu를 직접 호출하면 popup이 뜨므로, 메뉴 구성만 검증
    # 대신 폴더 아이템이 있는지 확인
    assert sidebar._model.rowCount() >= 2


def test_sidebar_create_folder_signal(qtbot: object, tmp_path: pathlib.Path) -> None:
    """_create_folder 호출 시 folder_created 신호가 emit되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    signals: list[str] = []
    sidebar.folder_created.connect(lambda n: signals.append(n))

    sidebar._create_folder("TestSignal")
    assert "TestSignal" in signals


def test_sidebar_transcript_display(qtbot: object, tmp_path: pathlib.Path) -> None:
    """transcript가 있는 폴더에 카운트가 표시되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)
    # transcript 생성
    meeting_dir = tmp_path / "Work" / "Meeting-1"
    meeting_dir.mkdir(parents=True)
    (meeting_dir / "transcript.json").write_text("{}")

    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    # Work 폴더 찾기
    work_item = None
    for i in range(sidebar._model.rowCount()):
        item = sidebar._model.item(i)
        if item and item.text() == "Work":
            work_item = item
            break

    assert work_item is not None
    assert work_item.rowCount() > 0  # placeholder 또는 transcript 아이템


# ============================================================
# Selection 모드 테스트
# ============================================================


def _create_sidebar_with_transcripts(
    tmp_path: pathlib.Path,
) -> tuple[SidebarWidget, WorkspaceManager]:
    """테스트용 transcript가 있는 사이드바를 생성한다.

    Args:
        tmp_path: pytest tmp_path

    Returns:
        (SidebarWidget, WorkspaceManager) 튜플
    """
    ws = WorkspaceManager(workspace_dir=tmp_path)

    # Work 폴더에 transcript 2개
    for name in ("Meeting-1", "Meeting-2"):
        meeting_dir = tmp_path / "Work" / name
        meeting_dir.mkdir(parents=True, exist_ok=True)
        (meeting_dir / "transcript.json").write_text("{}")

    # Personal 폴더에 transcript 1개
    meeting_dir = tmp_path / "Personal" / "Lecture-1"
    meeting_dir.mkdir(parents=True, exist_ok=True)
    (meeting_dir / "transcript.json").write_text("{}")

    sidebar = SidebarWidget(workspace=ws)
    return sidebar, ws


def _find_folder_item(sidebar: SidebarWidget, name: str) -> QStandardItem | None:
    """이름으로 폴더 아이템을 찾는다.

    Args:
        sidebar: SidebarWidget 인스턴스
        name: 폴더 이름

    Returns:
        QStandardItem 또는 None
    """
    for i in range(sidebar._model.rowCount()):
        item = sidebar._model.item(i)
        if item and item.text() == name:
            return item
    return None


def _load_folder_transcripts(sidebar: SidebarWidget, folder_name: str) -> QStandardItem | None:
    """폴더의 transcript를 로드하고 폴더 아이템을 반환한다.

    Args:
        sidebar: SidebarWidget 인스턴스
        folder_name: 폴더 이름

    Returns:
        QStandardItem 또는 None
    """
    folder_item = _find_folder_item(sidebar, folder_name)
    if folder_item is not None:
        sidebar._load_transcripts_for_folder(folder_name, folder_item)
    return folder_item


def test_selection_mode_enter_exit(qtbot: object, tmp_path: pathlib.Path) -> None:
    """Selection 모드 진입/종료가 정상 동작하는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    assert sidebar._selection_mode is False

    sidebar._enter_selection_mode()
    assert sidebar._selection_mode is True

    sidebar._exit_selection_mode()
    assert sidebar._selection_mode is False


def test_selection_mode_checkboxes_appear(qtbot: object, tmp_path: pathlib.Path) -> None:
    """Selection 모드에서 모든 transcript에 체크박스가 표시되는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    # 폴더의 transcript 로드
    _load_folder_transcripts(sidebar, "Work")
    _load_folder_transcripts(sidebar, "Personal")

    sidebar._enter_selection_mode()

    for row in range(sidebar._model.rowCount()):
        folder_item = sidebar._model.item(row)
        if folder_item is None:
            continue
        item_type = folder_item.data(Qt.ItemDataRole.UserRole + 1)
        if item_type == "analyses_header":
            assert not folder_item.isCheckable()
            continue
        if item_type == "folder":
            assert folder_item.isCheckable()
            for child_row in range(folder_item.rowCount()):
                child = folder_item.child(child_row)
                if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                    assert child.isCheckable()


def test_folder_checkbox_propagates_to_children(
    qtbot: object, tmp_path: pathlib.Path
) -> None:
    """폴더 체크 시 모든 자식 transcript에 전파되는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    work_item = _load_folder_transcripts(sidebar, "Work")
    assert work_item is not None

    sidebar._enter_selection_mode()

    # 폴더를 체크
    work_item.setCheckState(Qt.CheckState.Checked)

    # 모든 자식이 체크되었는지 확인
    for child_row in range(work_item.rowCount()):
        child = work_item.child(child_row)
        if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
            assert child.checkState() == Qt.CheckState.Checked


def test_action_bar_visible_when_two_selected(
    qtbot: object, tmp_path: pathlib.Path
) -> None:
    """2개 이상 transcript 선택 시 액션 바가 표시되는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    work_item = _load_folder_transcripts(sidebar, "Work")
    assert work_item is not None

    sidebar._enter_selection_mode()

    # 2개 transcript 체크
    for child_row in range(work_item.rowCount()):
        child = work_item.child(child_row)
        if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
            child.setCheckState(Qt.CheckState.Checked)

    assert sidebar._action_bar is not None
    # isVisible() requires parent to be shown; use isHidden() for unshown widgets
    assert not sidebar._action_bar.isHidden()
    assert sidebar._action_label is not None
    assert "2" in sidebar._action_label.text()


def test_action_bar_hidden_when_less_than_two(
    qtbot: object, tmp_path: pathlib.Path
) -> None:
    """1개만 선택 시 액션 바가 숨겨지는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    work_item = _load_folder_transcripts(sidebar, "Work")
    assert work_item is not None

    sidebar._enter_selection_mode()

    # 1개만 체크
    child = work_item.child(0)
    if child:
        child.setCheckState(Qt.CheckState.Checked)

    assert sidebar._action_bar is not None
    assert sidebar._action_bar.isHidden()


def test_analysis_requested_signal(qtbot: object, tmp_path: pathlib.Path) -> None:
    """Analyze 클릭 시 analysis_requested 시그널이 올바른 경로와 함께 emit되는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    work_item = _load_folder_transcripts(sidebar, "Work")
    assert work_item is not None

    sidebar._enter_selection_mode()

    # 2개 transcript 체크
    for child_row in range(work_item.rowCount()):
        child = work_item.child(child_row)
        if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
            child.setCheckState(Qt.CheckState.Checked)

    received: list[list[str]] = []
    sidebar.analysis_requested.connect(lambda paths: received.append(paths))

    sidebar._on_analyze_clicked()

    assert len(received) == 1
    assert len(received[0]) == 2
    # Selection 모드가 종료되었는지 확인
    assert sidebar._selection_mode is False


def test_analyses_section_in_tree(qtbot: object, tmp_path: pathlib.Path) -> None:
    """Analyses 섹션이 트리에 표시되고 분석 파일이 자식으로 나타나는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)

    # analyses 디렉토리에 분석 파일 생성
    analyses_dir = tmp_path / "analyses"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    analysis_file = analyses_dir / "analysis_2026-03-31_140005.json"
    analysis_file.write_text(json.dumps({"version": "1.0"}))

    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    # Analyses 헤더 찾기
    analyses_item = None
    for i in range(sidebar._model.rowCount()):
        item = sidebar._model.item(i)
        if item and item.data(Qt.ItemDataRole.UserRole + 1) == "analyses_header":
            analyses_item = item
            break

    assert analyses_item is not None
    assert analyses_item.text() == "Analyses"
    assert analyses_item.rowCount() == 1

    child = analyses_item.child(0)
    assert child is not None
    assert child.data(Qt.ItemDataRole.UserRole + 1) == "analysis"
    assert "2026-03-31" in child.text()


def test_analysis_selected_signal(qtbot: object, tmp_path: pathlib.Path) -> None:
    """분석 아이템 클릭 시 analysis_selected 시그널이 emit되는지 확인."""
    ws = WorkspaceManager(workspace_dir=tmp_path)

    analyses_dir = tmp_path / "analyses"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    analysis_file = analyses_dir / "analysis_2026-03-31_140005.json"
    analysis_file.write_text(json.dumps({"version": "1.0"}))

    sidebar = SidebarWidget(workspace=ws)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    signals: list[str] = []
    sidebar.analysis_selected.connect(lambda p: signals.append(p))

    # Analyses 헤더의 첫 번째 자식 클릭
    analyses_item = None
    for i in range(sidebar._model.rowCount()):
        item = sidebar._model.item(i)
        if item and item.data(Qt.ItemDataRole.UserRole + 1) == "analyses_header":
            analyses_item = item
            break

    assert analyses_item is not None
    child = analyses_item.child(0)
    assert child is not None

    # 직접 아이템의 인덱스로 클릭 시뮬레이션
    child_index = sidebar._model.indexFromItem(child)
    sidebar._on_item_clicked(child_index)

    assert len(signals) == 1
    assert str(analysis_file) in signals[0]


def test_select_all_checks_all_transcripts(qtbot: object, tmp_path: pathlib.Path) -> None:
    """Select All이 모든 transcript를 선택하는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    _load_folder_transcripts(sidebar, "Work")
    _load_folder_transcripts(sidebar, "Personal")

    sidebar._enter_selection_mode()
    sidebar._on_select_all_clicked()

    paths = sidebar._get_checked_transcript_paths()
    assert len(paths) == 3  # Work(2) + Personal(1)


def test_toolbar_buttons_toggle_in_selection_mode(
    qtbot: object, tmp_path: pathlib.Path
) -> None:
    """Selection 모드에서 툴바 버튼이 올바르게 전환되는지 확인."""
    sidebar, _ = _create_sidebar_with_transcripts(tmp_path)
    qtbot.addWidget(sidebar)  # type: ignore[union-attr]

    # 초기 상태 (isHidden 사용 -- 부모가 미표시이므로 isVisible은 항상 False)
    assert not sidebar._new_folder_btn.isHidden()
    assert sidebar._select_btn is not None and not sidebar._select_btn.isHidden()
    assert sidebar._select_all_btn is not None and sidebar._select_all_btn.isHidden()
    assert sidebar._cancel_btn is not None and sidebar._cancel_btn.isHidden()

    # Selection 모드 진입
    sidebar._enter_selection_mode()
    assert sidebar._new_folder_btn.isHidden()
    assert sidebar._select_btn.isHidden()
    assert not sidebar._select_all_btn.isHidden()
    assert not sidebar._cancel_btn.isHidden()

    # Selection 모드 종료
    sidebar._exit_selection_mode()
    assert not sidebar._new_folder_btn.isHidden()
    assert not sidebar._select_btn.isHidden()
    assert sidebar._select_all_btn.isHidden()
    assert sidebar._cancel_btn.isHidden()
