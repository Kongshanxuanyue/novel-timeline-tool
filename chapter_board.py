"""章节看板面板组件"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QMessageBox,
    QAbstractItemView, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from dialogs import AddChapterDialog, EditChapterDialog, WRITING_STATUS_OPTIONS, CHAPTER_STATUS_OPTIONS


class ChapterCard(QFrame):
    """章节卡片组件"""
    
    clicked = Signal(int)  # chapter_id
    edit_requested = Signal(int)  # chapter_id
    
    def __init__(self, chapter_data, event_count=0):
        super().__init__()
        self.chapter_data = chapter_data
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self.setCursor(Qt.PointingHandCursor)
        
        # 根据状态设置背景色
        status = chapter_data.get('status', 0)
        status_colors = {
            0: "#F3F4F6",  # 规划中 - 灰色
            1: "#FEF3C7",  # 写作中 - 黄色
            2: "#D1FAE5",  # 已完成 - 绿色
        }
        self.setStyleSheet(f"background-color: {status_colors.get(status, '#F3F4F6')}; border-radius: 8px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # 章节标题
        title_label = QLabel(f"第{chapter_data['number']}章 {chapter_data['title']}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 状态和字数
        status_name = CHAPTER_STATUS_OPTIONS[status][0]
        info_label = QLabel(f"状态: {status_name} | 字数: {chapter_data.get('word_count', 0)} | 事件: {event_count}")
        info_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(info_label)
        
        # 摘要（如果有）
        if chapter_data.get('summary'):
            summary_label = QLabel(chapter_data['summary'][:50] + "..." if len(chapter_data['summary']) > 50 else chapter_data['summary'])
            summary_label.setStyleSheet("color: #9CA3AF; font-size: 10px;")
            summary_label.setWordWrap(True)
            layout.addWidget(summary_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.chapter_data['id'])
        elif event.button() == Qt.RightButton:
            self.edit_requested.emit(self.chapter_data['id'])
        super().mousePressEvent(event)


class ChapterBoardPanel(QWidget):
    """章节看板面板"""
    
    chapter_selected = Signal(int)  # chapter_id
    chapter_edit_requested = Signal(int)  # chapter_id
    create_chapter_from_events = Signal(list)  # event_ids
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.selected_events = []
        
        self.setMinimumWidth(250)
        self.setMaximumWidth(350)
        self.setStyleSheet("background-color: #F9FAFB;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题栏
        header_layout = QHBoxLayout()
        header_label = QLabel("📚 章节看板")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        
        self.manage_btn = QPushButton("管理")
        self.manage_btn.setMaximumWidth(60)
        header_layout.addWidget(self.manage_btn)
        
        self.add_btn = QPushButton("+")
        self.add_btn.setMaximumWidth(30)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # 章节列表区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.chapter_container = QWidget()
        self.chapter_layout = QVBoxLayout(self.chapter_container)
        self.chapter_layout.setSpacing(8)
        self.chapter_layout.setContentsMargins(0, 0, 0, 0)
        self.chapter_layout.addStretch()
        
        self.scroll_area.setWidget(self.chapter_container)
        layout.addWidget(self.scroll_area)
        
        # 选中事件区域（用于创建章节）
        self.selection_frame = QFrame()
        self.selection_frame.setFrameStyle(QFrame.StyledPanel)
        self.selection_frame.setStyleSheet("background-color: #E0E7FF; border-radius: 6px;")
        self.selection_frame.setVisible(False)
        
        selection_layout = QVBoxLayout(self.selection_frame)
        selection_layout.setContentsMargins(8, 8, 8, 8)
        
        self.selection_label = QLabel("已选中 0 个事件")
        self.selection_label.setStyleSheet("font-size: 12px; color: #4F46E5;")
        selection_layout.addWidget(self.selection_label)
        
        selection_btn_layout = QHBoxLayout()
        self.create_chapter_btn = QPushButton("创建章节")
        self.clear_selection_btn = QPushButton("清除")
        selection_btn_layout.addWidget(self.create_chapter_btn)
        selection_btn_layout.addWidget(self.clear_selection_btn)
        selection_layout.addLayout(selection_btn_layout)
        
        layout.addWidget(self.selection_frame)
        
        # 统计信息
        self.stats_label = QLabel("共 0 章 | 0 事件 | 0 字")
        self.stats_label.setStyleSheet("color: #9CA3AF; font-size: 10px;")
        layout.addWidget(self.stats_label)
        
        # 连接信号
        self.add_btn.clicked.connect(self._add_chapter)
        self.manage_btn.clicked.connect(self._manage_chapters)
        self.create_chapter_btn.clicked.connect(self._create_from_selection)
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        
        self._refresh_chapters()
    
    def _refresh_chapters(self):
        """刷新章节列表"""
        # 清空现有卡片
        while self.chapter_layout.count() > 1:
            item = self.chapter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        chapters = self.db.get_all_chapters()
        total_events = 0
        total_words = 0
        
        for ch in chapters:
            events = self.db.get_events_by_chapter(ch['number'])
            event_count = len(events)
            total_events += event_count
            total_words += ch.get('word_count', 0)
            
            card = ChapterCard(ch, event_count)
            card.clicked.connect(self.chapter_selected.emit)
            card.edit_requested.connect(self.chapter_edit_requested.emit)
            self.chapter_layout.insertWidget(self.chapter_layout.count() - 1, card)
        
        self.stats_label.setText(f"共 {len(chapters)} 章 | {total_events} 事件 | {total_words} 字")
    
    def set_selected_events(self, event_ids):
        """设置选中的事件列表"""
        self.selected_events = event_ids
        if event_ids:
            self.selection_frame.setVisible(True)
            self.selection_label.setText(f"已选中 {len(event_ids)} 个事件")
        else:
            self.selection_frame.setVisible(False)
    
    def _add_chapter(self):
        """添加章节"""
        dialog = AddChapterDialog(self.db, self)
        if dialog.exec() == AddChapterDialog.Accepted:
            data = dialog.get_chapter_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入章节标题")
                return
            
            self.db.create_chapter(
                data['number'], data['title'], data['summary'],
                data['word_count'], data['status']
            )
            
            for ev_id in data['event_ids']:
                self.db.bind_event_to_chapter(ev_id, data['number'], data['title'])
            
            self._refresh_chapters()
            self._clear_selection()
    
    def _manage_chapters(self):
        """管理章节"""
        from dialogs import ManageChaptersDialog
        dialog = ManageChaptersDialog(self.db, self)
        dialog.exec()
        self._refresh_chapters()
    
    def _create_from_selection(self):
        """从选中事件创建章节"""
        if self.selected_events:
            self.create_chapter_from_events.emit(self.selected_events)
    
    def _clear_selection(self):
        """清除选中"""
        self.selected_events = []
        self.selection_frame.setVisible(False)
    
    def refresh(self):
        """刷新面板"""
        self._refresh_chapters()