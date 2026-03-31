"""사이드바 폴더 트리 위젯 — QTreeView 기반 파일시스템 브라우저."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QFileSystemWatcher, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.storage.workspace import WorkspaceManager
from meeting_transcriber.utils.constants import ANALYSES_DIR, MIN_SELECTION_COUNT


class SidebarWidget(QWidget):
    """사이드바 폴더 트리 위젯.

    워크스페이스 폴더를 QTreeView로 표시하고, CRUD 작업을 지원한다.
    QFileSystemWatcher로 외부 변경을 감지한다.
    Selection 모드로 다중 transcript를 선택하여 크로스 미팅 분석을 수행할 수 있다.
    """

    folder_selected = pyqtSignal(str)
    transcript_selected = pyqtSignal(str)
    folder_created = pyqtSignal(str)
    folder_renamed = pyqtSignal(str, str)
    folder_deleted = pyqtSignal(str)
    analysis_requested = pyqtSignal(list)
    analysis_selected = pyqtSignal(str)

    def __init__(
        self,
        workspace: WorkspaceManager | None = None,
        parent: Any = None,
    ) -> None:
        """SidebarWidget을 초기화한다.

        Args:
            workspace: WorkspaceManager 인스턴스. None이면 기본값 생성.
            parent: Qt 부모 위젯
        """
        super().__init__(parent)
        self._workspace = workspace or WorkspaceManager()
        self._workspace.ensure_default_folders()

        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Folders"])

        self._watcher = QFileSystemWatcher()
        self._watcher.directoryChanged.connect(self._on_directory_changed)

        self._selection_mode: bool = False
        self._action_bar: QWidget | None = None
        self._action_label: QLabel | None = None
        self._analyze_btn: QPushButton | None = None
        self._select_btn: QPushButton | None = None
        self._select_all_btn: QPushButton | None = None
        self._cancel_btn: QPushButton | None = None

        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        """레이아웃과 위젯을 구성한다."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 툴바
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)

        self._new_folder_btn = QPushButton("+ New Folder")
        self._new_folder_btn.clicked.connect(self._on_new_folder_clicked)
        toolbar.addWidget(self._new_folder_btn)

        self._select_btn = QPushButton("Select")
        self._select_btn.clicked.connect(self._on_select_btn_clicked)
        toolbar.addWidget(self._select_btn)

        # Selection 모드 버튼 (초기 숨김)
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self._on_select_all_clicked)
        self._select_all_btn.setVisible(False)
        toolbar.addWidget(self._select_all_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._cancel_btn.setVisible(False)
        toolbar.addWidget(self._cancel_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 트리뷰
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.clicked.connect(self._on_item_clicked)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)

        layout.addWidget(self._tree)

        # 액션 바 (초기 숨김)
        self._action_bar = QWidget()
        action_layout = QHBoxLayout(self._action_bar)
        action_layout.setContentsMargins(8, 4, 8, 4)

        self._action_label = QLabel("")
        action_layout.addWidget(self._action_label)
        action_layout.addStretch()

        self._analyze_btn = QPushButton("Analyze")
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        action_layout.addWidget(self._analyze_btn)

        self._action_bar.setVisible(False)
        layout.addWidget(self._action_bar)

    @property
    def tree_view(self) -> QTreeView:
        """내부 QTreeView 인스턴스."""
        return self._tree

    def refresh(self) -> None:
        """폴더 목록을 다시 로드하여 트리를 갱신한다."""
        # Selection 모드 시 선택 상태 보존
        checked_paths: set[str] = set()
        if self._selection_mode:
            checked_paths = set(self._get_checked_transcript_paths())

        self._model.clear()
        self._model.setHorizontalHeaderLabels(["Folders"])

        # 기존 감시 경로 제거
        paths = self._watcher.directories()
        if paths:
            self._watcher.removePaths(paths)

        # 루트 디렉토리 감시
        root_str = str(self._workspace.root)
        self._watcher.addPath(root_str)

        folders = self._workspace.list_folders()
        for folder in folders:
            item = QStandardItem(folder.name)
            item.setData(str(folder.path), Qt.ItemDataRole.UserRole)
            item.setData("folder", Qt.ItemDataRole.UserRole + 1)

            # transcript 서브아이템은 lazy load — 폴더 클릭 시 로드
            if folder.transcript_count > 0:
                placeholder = QStandardItem(f"{folder.transcript_count} transcripts")
                placeholder.setEnabled(False)
                item.appendRow(placeholder)

            self._model.appendRow(item)
            self._watcher.addPath(str(folder.path))

        # Analyses 섹션 추가
        self._add_analyses_section()

        # Selection 모드 재적용
        if self._selection_mode:
            self._apply_checkable_state()
            self._restore_checked_paths(checked_paths)

    def _add_analyses_section(self) -> None:
        """Analyses 섹션을 트리 하단에 추가한다."""
        header = QStandardItem("Analyses")
        bold_font = QFont()
        bold_font.setBold(True)
        header.setFont(bold_font)
        header.setEditable(False)
        header.setData("analyses_header", Qt.ItemDataRole.UserRole + 1)

        analyses_dir = self._workspace.root / ANALYSES_DIR
        if analyses_dir.exists():
            for path in sorted(analyses_dir.glob("analysis_*.json")):
                name = path.stem  # "analysis_2026-03-31_140005"
                # analysis_ 프리픽스 제거 및 포맷팅
                display = name.replace("analysis_", "").replace("_", " ")
                child = QStandardItem(display)
                child.setData(str(path), Qt.ItemDataRole.UserRole)
                child.setData("analysis", Qt.ItemDataRole.UserRole + 1)
                child.setEditable(False)
                header.appendRow(child)

        self._model.appendRow(header)

    # ============================================================
    # Selection 모드 메서드
    # ============================================================

    def _on_select_btn_clicked(self) -> None:
        """Select 버튼 클릭 핸들러."""
        self._enter_selection_mode()

    def _enter_selection_mode(self) -> None:
        """Selection 모드를 활성화하고 체크박스를 표시한다."""
        self._selection_mode = True

        # 툴바 버튼 전환
        self._new_folder_btn.setVisible(False)
        if self._select_btn is not None:
            self._select_btn.setVisible(False)
        if self._select_all_btn is not None:
            self._select_all_btn.setVisible(True)
        if self._cancel_btn is not None:
            self._cancel_btn.setVisible(True)

        self._apply_checkable_state()
        self._model.itemChanged.connect(self._on_item_check_changed)

    def _exit_selection_mode(self) -> None:
        """Selection 모드를 비활성화하고 체크박스를 제거한다."""
        self._selection_mode = False

        # 툴바 버튼 복원
        self._new_folder_btn.setVisible(True)
        if self._select_btn is not None:
            self._select_btn.setVisible(True)
        if self._select_all_btn is not None:
            self._select_all_btn.setVisible(False)
        if self._cancel_btn is not None:
            self._cancel_btn.setVisible(False)

        # 체크박스 제거
        self._remove_checkable_state()

        try:
            self._model.itemChanged.disconnect(self._on_item_check_changed)
        except TypeError:
            pass  # 이미 연결 해제됨

        # 액션 바 숨김
        if self._action_bar is not None:
            self._action_bar.setVisible(False)

    def _on_cancel_clicked(self) -> None:
        """Cancel 버튼 클릭 핸들러."""
        self._exit_selection_mode()

    def _on_select_all_clicked(self) -> None:
        """Select All 버튼 클릭 — 모든 transcript를 선택한다."""
        self._model.blockSignals(True)
        try:
            for row in range(self._model.rowCount()):
                folder_item = self._model.item(row)
                if folder_item is None:
                    continue
                item_type = folder_item.data(Qt.ItemDataRole.UserRole + 1)
                if item_type == "analyses_header":
                    continue
                if item_type == "folder":
                    folder_item.setCheckState(Qt.CheckState.Checked)
                    for child_row in range(folder_item.rowCount()):
                        child = folder_item.child(child_row)
                        if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                            child.setCheckState(Qt.CheckState.Checked)
        finally:
            self._model.blockSignals(False)
        self._update_action_bar()

    def _apply_checkable_state(self) -> None:
        """모든 folder/transcript 아이템에 체크박스를 추가한다."""
        for row in range(self._model.rowCount()):
            folder_item = self._model.item(row)
            if folder_item is None:
                continue
            item_type = folder_item.data(Qt.ItemDataRole.UserRole + 1)
            if item_type == "analyses_header":
                continue  # Analyses 섹션은 체크 불가
            if item_type == "folder":
                folder_item.setCheckable(True)
                folder_item.setCheckState(Qt.CheckState.Unchecked)
                for child_row in range(folder_item.rowCount()):
                    child = folder_item.child(child_row)
                    if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                        child.setCheckable(True)
                        child.setCheckState(Qt.CheckState.Unchecked)

    def _remove_checkable_state(self) -> None:
        """모든 아이템에서 체크박스를 제거한다."""
        for row in range(self._model.rowCount()):
            folder_item = self._model.item(row)
            if folder_item is None:
                continue
            folder_item.setCheckable(False)
            for child_row in range(folder_item.rowCount()):
                child = folder_item.child(child_row)
                if child:
                    child.setCheckable(False)

    def _restore_checked_paths(self, checked_paths: set[str]) -> None:
        """저장된 체크 상태를 복원한다.

        Args:
            checked_paths: 체크된 transcript 경로 집합
        """
        if not checked_paths:
            return
        self._model.blockSignals(True)
        try:
            for row in range(self._model.rowCount()):
                folder_item = self._model.item(row)
                if folder_item is None:
                    continue
                if folder_item.data(Qt.ItemDataRole.UserRole + 1) != "folder":
                    continue
                for child_row in range(folder_item.rowCount()):
                    child = folder_item.child(child_row)
                    if child and child.data(Qt.ItemDataRole.UserRole) in checked_paths:
                        child.setCheckState(Qt.CheckState.Checked)
                # 부모 상태 업데이트
                self._update_folder_check_state(folder_item)
        finally:
            self._model.blockSignals(False)
        self._update_action_bar()

    # ============================================================
    # 체크박스 전파 및 액션 바
    # ============================================================

    def _on_item_check_changed(self, item: QStandardItem) -> None:
        """체크박스 변경 시 부모/자식 전파를 처리한다.

        Args:
            item: 변경된 QStandardItem
        """
        item_type = item.data(Qt.ItemDataRole.UserRole + 1)

        if item_type == "folder":
            # 폴더 체크 -> 모든 자식에 전파
            self._model.blockSignals(True)
            try:
                check_state = item.checkState()
                for child_row in range(item.rowCount()):
                    child = item.child(child_row)
                    if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                        child.setCheckState(check_state)
            finally:
                self._model.blockSignals(False)

        elif item_type == "transcript":
            # 자식 체크 -> 부모 상태 업데이트
            parent = item.parent()
            if parent is not None:
                self._model.blockSignals(True)
                try:
                    self._update_folder_check_state(parent)
                finally:
                    self._model.blockSignals(False)

        self._update_action_bar()

    def _update_folder_check_state(self, folder_item: QStandardItem) -> None:
        """폴더의 체크 상태를 자식 상태로부터 갱신한다.

        Args:
            folder_item: 폴더 QStandardItem
        """
        checked = 0
        total = 0
        for child_row in range(folder_item.rowCount()):
            child = folder_item.child(child_row)
            if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                total += 1
                if child.checkState() == Qt.CheckState.Checked:
                    checked += 1

        if total == 0:
            return

        if checked == total:
            folder_item.setCheckState(Qt.CheckState.Checked)
        elif checked == 0:
            folder_item.setCheckState(Qt.CheckState.Unchecked)
        else:
            folder_item.setCheckState(Qt.CheckState.PartiallyChecked)

    def _update_action_bar(self) -> None:
        """선택된 transcript 수에 따라 액션 바를 업데이트한다."""
        paths = self._get_checked_transcript_paths()
        count = len(paths)

        if self._action_bar is not None:
            if count >= MIN_SELECTION_COUNT:
                self._action_bar.setVisible(True)
                if self._action_label is not None:
                    self._action_label.setText(f"Analyze {count} selected")
            else:
                self._action_bar.setVisible(False)

    def _get_checked_transcript_paths(self) -> list[str]:
        """모든 폴더에서 체크된 transcript 경로를 수집한다.

        Returns:
            체크된 transcript 경로 리스트
        """
        paths: list[str] = []
        for row in range(self._model.rowCount()):
            folder_item = self._model.item(row)
            if folder_item is None:
                continue
            if folder_item.data(Qt.ItemDataRole.UserRole + 1) != "folder":
                continue
            for child_row in range(folder_item.rowCount()):
                child = folder_item.child(child_row)
                if (
                    child
                    and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript"
                    and child.checkState() == Qt.CheckState.Checked
                ):
                    path = child.data(Qt.ItemDataRole.UserRole)
                    if path:
                        paths.append(path)
        return paths

    def _on_analyze_clicked(self) -> None:
        """Analyze 버튼 클릭 — 선택된 transcript로 분석을 요청한다."""
        paths = self._get_checked_transcript_paths()
        if len(paths) >= MIN_SELECTION_COUNT:
            self.analysis_requested.emit(paths)
        self._exit_selection_mode()

    # ============================================================
    # 이벤트 핸들러
    # ============================================================

    def _on_item_clicked(self, index: QModelIndex) -> None:
        """트리 아이템 클릭 시 signal을 emit한다."""
        item = self._model.itemFromIndex(index)
        if item is None:
            return

        item_type = item.data(Qt.ItemDataRole.UserRole + 1)
        item_path = item.data(Qt.ItemDataRole.UserRole)

        if item_type == "folder":
            self.folder_selected.emit(item_path)
            self._load_transcripts_for_folder(item.text(), item)
        elif item_type == "transcript":
            self.transcript_selected.emit(item_path)
        elif item_type == "analysis":
            self.analysis_selected.emit(item_path)

    def _load_transcripts_for_folder(self, folder_name: str, parent_item: QStandardItem) -> None:
        """폴더의 transcript 목록을 로드하여 트리에 추가한다."""
        parent_item.removeRows(0, parent_item.rowCount())

        try:
            transcripts = self._workspace.list_transcripts(folder_name)
        except FileNotFoundError:
            return

        for path in transcripts:
            name = path.parent.name
            child = QStandardItem(name)
            child.setData(str(path), Qt.ItemDataRole.UserRole)
            child.setData("transcript", Qt.ItemDataRole.UserRole + 1)
            parent_item.appendRow(child)

        # Selection 모드에서 로드 후 체크박스 적용
        if self._selection_mode:
            for child_row in range(parent_item.rowCount()):
                child = parent_item.child(child_row)
                if child and child.data(Qt.ItemDataRole.UserRole + 1) == "transcript":
                    child.setCheckable(True)
                    child.setCheckState(Qt.CheckState.Unchecked)

    def _on_directory_changed(self, path: str) -> None:
        """QFileSystemWatcher가 감지한 디렉토리 변경을 처리한다."""
        self.refresh()

    def _on_new_folder_clicked(self) -> None:
        """새 폴더 생성 버튼 클릭."""
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            self._create_folder(name.strip())

    def _show_context_menu(self, position: Any) -> None:
        """우클릭 컨텍스트 메뉴를 표시한다."""
        index = self._tree.indexAt(position)
        item = self._model.itemFromIndex(index) if index.isValid() else None

        menu = QMenu(self)

        new_action = QAction("New Folder", self)
        new_action.triggered.connect(self._on_new_folder_clicked)
        menu.addAction(new_action)

        if item and item.data(Qt.ItemDataRole.UserRole + 1) == "folder":
            menu.addSeparator()

            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self._rename_folder_dialog(item))
            menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self._delete_folder_dialog(item))
            menu.addAction(delete_action)

        viewport = self._tree.viewport()
        if viewport is not None:
            menu.popup(viewport.mapToGlobal(position))

    # -- 폴더 CRUD --

    def _create_folder(self, name: str) -> None:
        """폴더를 생성하고 트리를 갱신한다."""
        try:
            self._workspace.create_folder(name)
            self.folder_created.emit(name)
            self.refresh()
        except (FileExistsError, ValueError) as e:
            QMessageBox.warning(self, "Error", str(e))

    def _rename_folder_dialog(self, item: QStandardItem) -> None:
        """폴더 이름 변경 다이얼로그를 표시한다."""
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Folder", "New name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            try:
                self._workspace.rename_folder(old_name, new_name.strip())
                self.folder_renamed.emit(old_name, new_name.strip())
                self.refresh()
            except (FileNotFoundError, FileExistsError, ValueError) as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_folder_dialog(self, item: QStandardItem) -> None:
        """폴더 삭제 확인 다이얼로그를 표시한다."""
        name = item.text()
        reply = QMessageBox.question(
            self,
            "Delete Folder",
            f"Delete '{name}' and all its contents?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._workspace.delete_folder(name)
                self.folder_deleted.emit(name)
                self.refresh()
            except FileNotFoundError as e:
                QMessageBox.warning(self, "Error", str(e))
