"""사이드바 폴더 트리 위젯 — QTreeView 기반 파일시스템 브라우저."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QFileSystemWatcher, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from meeting_transcriber.storage.workspace import WorkspaceManager


class SidebarWidget(QWidget):
    """사이드바 폴더 트리 위젯.

    워크스페이스 폴더를 QTreeView로 표시하고, CRUD 작업을 지원한다.
    QFileSystemWatcher로 외부 변경을 감지한다.
    """

    folder_selected = pyqtSignal(str)
    transcript_selected = pyqtSignal(str)
    folder_created = pyqtSignal(str)
    folder_renamed = pyqtSignal(str, str)
    folder_deleted = pyqtSignal(str)

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

    @property
    def tree_view(self) -> QTreeView:
        """내부 QTreeView 인스턴스."""
        return self._tree

    def refresh(self) -> None:
        """폴더 목록을 다시 로드하여 트리를 갱신한다."""
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

    # -- 이벤트 핸들러 --

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

    def _on_directory_changed(self, path: str) -> None:
        """QFileSystemWatcher가 감지한 디렉토리 변경을 처리한다."""
        self.refresh()

    def _on_new_folder_clicked(self) -> None:
        """새 폴더 생성 버튼 클릭."""
        name, ok = QInputDialog.getText(
            self, "New Folder", "Folder name:"
        )
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
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=old_name
        )
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
