"""灵感管理面板和速记窗口"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QComboBox, QListWidget, QListWidgetItem, QScrollArea,
    QFrame, QDialog, QMenu, QMessageBox, QCheckBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QFont, QColor

from semantic_search import SemanticSearcher
from constants import APP_STYLESHEET

CATEGORY_NAMES = {
    0: "人物灵感",
    1: "情节灵感",
    2: "对话灵感",
    3: "设定灵感",
    4: "其他",
}

CATEGORY_COLORS = {
    0: "#8B5CF6",
    1: "#EF4444",
    2: "#3B82F6",
    3: "#10B981",
    4: "#6B7280",
}

SOURCE_OPTIONS = [
    "随手记录",
    "散步时想到",
    "梦中",
    "阅读时",
    "与人讨论",
    "其他",
]


class QuickInspirationDialog(QDialog):
    """快速灵感记录对话框"""
    
    inspiration_added = Signal()
    
    def __init__(self, db_manager, semantic_searcher, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.semantic_searcher = semantic_searcher
        
        self.setWindowTitle("✨ 灵感速记")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(APP_STYLESHEET + """
            QDialog {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            }
        """)
        
        self.resize(480, 320)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        title_label = QLabel("✨ 快速记录灵感")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #1F2937;")
        layout.addWidget(title_label)
        
        # 内容输入
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("输入你的灵感...")
        self.content_edit.setMaximumHeight(120)
        self.content_edit.setStyleSheet("""
            QTextEdit {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                color: #1F2937;
                padding: 8px;
                font-size: 13px;
            }
            QTextEdit:focus {
                border-color: #3B82F6;
            }
        """)
        layout.addWidget(self.content_edit)
        
        # 分类和来源
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        for k, v in CATEGORY_NAMES.items():
            self.category_combo.addItem(v, k)
        self.category_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #1F2937;
                padding: 4px;
                font-size: 12px;
            }
        """)
        row1.addWidget(self.category_combo)
        
        row1.addSpacing(12)
        
        row1.addWidget(QLabel("来源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(SOURCE_OPTIONS)
        self.source_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #1F2937;
                padding: 4px;
                font-size: 12px;
            }
        """)
        row1.addWidget(self.source_combo)
        
        layout.addLayout(row1)
        
        # 标签输入
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("标签:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("多个标签用逗号分隔")
        self.tags_edit.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #1F2937;
                padding: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
            }
        """)
        row2.addWidget(self.tags_edit)
        layout.addLayout(row2)
        
        # 按钮
        btn_row = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2563EB;
            }
        """)
        btn_row.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("✕ 取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #E5E7EB;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
            }
            QPushButton:hover {
                background: #D1D5DB;
            }
        """)
        btn_row.addWidget(self.cancel_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
        
        QTimer.singleShot(100, self.content_edit.setFocus)
    
    def _save(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入灵感内容")
            return
        
        category = self.category_combo.currentData()
        source = self.source_combo.currentText()
        tags = self.tags_edit.text().strip() or None
        
        embedding = self.semantic_searcher.get_embedding(content)
        
        self.db.create_inspiration(content, category, tags, source, embedding)
        
        self.inspiration_added.emit()
        self.accept()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key_Return and (event.modifiers() & Qt.ControlModifier):
            self._save()


class InspirationCard(QFrame):
    """灵感卡片"""
    
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    mark_used_requested = Signal(int)
    convert_to_event_requested = Signal(int)
    
    def __init__(self, insp_data):
        super().__init__()
        self.insp_data = insp_data
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #3B82F6;
                background: #F9FAFB;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        
        # 头部：分类标签 + 状态
        header_row = QHBoxLayout()
        
        category_color = CATEGORY_COLORS.get(insp_data.get('category', 0), '#6B7280')
        category_name = CATEGORY_NAMES.get(insp_data.get('category', 0), '其他')
        cat_label = QLabel(f"[{category_name}]")
        cat_label.setStyleSheet(f"color: {category_color}; font-size: 11px; font-weight: bold;")
        header_row.addWidget(cat_label)
        
        if insp_data.get('is_used', 0):
            status_label = QLabel("✓ 已使用")
            status_label.setStyleSheet("color: #10B981; font-size: 11px;")
        else:
            status_label = QLabel("○ 未使用")
            status_label.setStyleSheet("color: #F59E0B; font-size: 11px;")
        header_row.addWidget(status_label)
        
        header_row.addStretch()
        layout.addLayout(header_row)
        
        # 内容
        content_label = QLabel(insp_data.get('content', ''))
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #1F2937; font-size: 13px;")
        layout.addWidget(content_label)
        
        # 标签
        tags = insp_data.get('tags', '')
        if tags:
            tags_label = QLabel(f"标签: {tags}")
            tags_label.setStyleSheet("color: #6B7280; font-size: 11px;")
            layout.addWidget(tags_label)
        
        # 底部：来源 + 时间
        bottom_row = QHBoxLayout()
        
        source = insp_data.get('source', '')
        if source:
            source_label = QLabel(f"来源: {source}")
            source_label.setStyleSheet("color: #9CA3AF; font-size: 10px;")
            bottom_row.addWidget(source_label)
        
        created_at = insp_data.get('created_at', '')
        if created_at:
            time_label = QLabel(str(created_at)[:19])
            time_label.setStyleSheet("color: #9CA3AF; font-size: 10px;")
            bottom_row.addWidget(time_label)
        
        bottom_row.addStretch()
        layout.addLayout(bottom_row)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
    
    def _show_menu(self, pos):
        menu = QMenu()
        
        if not self.insp_data.get('is_used', 0):
            mark_used_action = menu.addAction("✓ 标记为已使用")
            mark_used_action.triggered.connect(lambda: self.mark_used_requested.emit(self.insp_data['id']))
        
        convert_action = menu.addAction("→ 转化为事件")
        convert_action.triggered.connect(lambda: self.convert_to_event_requested.emit(self.insp_data['id']))
        
        edit_action = menu.addAction("✏️ 编辑")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.insp_data['id']))
        
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.insp_data['id']))
        
        menu.exec_(self.mapToGlobal(pos))


class InspirationPanel(QWidget):
    """灵感管理面板"""
    
    inspiration_selected = Signal(int)
    convert_to_event = Signal(int)
    
    def __init__(self, db_manager, semantic_searcher):
        super().__init__()
        self.db = db_manager
        self.semantic_searcher = semantic_searcher
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.setStyleSheet("background: #F9FAFB;")
        
        # 顶部控制栏
        control_row = QHBoxLayout()
        
        label = QLabel("灵感管理:")
        label.setStyleSheet("color: #1F2937; font-weight: bold;")
        control_row.addWidget(label)
        
        add_btn = QPushButton("➕ 快速记录")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2563EB;
            }
        """)
        add_btn.clicked.connect(self._show_quick_add)
        control_row.addWidget(add_btn)
        
        control_row.addStretch()
        
        # 分类筛选
        cat_label = QLabel("分类:")
        cat_label.setStyleSheet("color: #374151;")
        control_row.addWidget(cat_label)
        self.category_combo = QComboBox()
        self.category_combo.addItem("全部", None)
        for k, v in CATEGORY_NAMES.items():
            self.category_combo.addItem(v, k)
        self.category_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                color: #1F2937;
                padding: 2px 6px;
                font-size: 12px;
            }
        """)
        control_row.addWidget(self.category_combo)
        
        # 状态筛选
        status_label = QLabel("状态:")
        status_label.setStyleSheet("color: #374151;")
        control_row.addWidget(status_label)
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", None)
        self.status_combo.addItem("未使用", 0)
        self.status_combo.addItem("已使用", 1)
        self.status_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                color: #1F2937;
                padding: 2px 6px;
                font-size: 12px;
            }
        """)
        control_row.addWidget(self.status_combo)
        
        filter_btn = QPushButton("筛选")
        filter_btn.setStyleSheet("""
            QPushButton {
                background: #E5E7EB;
                color: #374151;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #D1D5DB;
            }
        """)
        filter_btn.clicked.connect(self._apply_filter)
        control_row.addWidget(filter_btn)
        
        layout.addLayout(control_row)
        
        # 搜索栏
        search_row = QHBoxLayout()
        
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("color: #374151;")
        search_row.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("关键词搜索...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                color: #1F2937;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
            }
        """)
        search_row.addWidget(self.search_edit)
        
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem("关键词", "keyword")
        self.search_type_combo.addItem("语义搜索", "semantic")
        self.search_type_combo.addItem("混合搜索", "hybrid")
        self.search_type_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                color: #1F2937;
                padding: 2px 6px;
                font-size: 12px;
            }
        """)
        search_row.addWidget(self.search_type_combo)
        
        search_btn = QPushButton("🔍 搜索")
        search_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2563EB;
            }
        """)
        search_btn.clicked.connect(self._search)
        search_row.addWidget(search_btn)
        
        layout.addLayout(search_row)
        
        # 结果列表
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setStyleSheet("QScrollArea { border: none; background: #F9FAFB; }")
        
        self.results_widget = QWidget()
        self.results_widget.setStyleSheet("background: #F9FAFB;")
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(8)
        self.results_layout.setAlignment(Qt.AlignTop)
        
        self.results_area.setWidget(self.results_widget)
        layout.addWidget(self.results_area)
        
        self._load_inspirations()
    
    def _load_inspirations(self):
        """加载灵感列表"""
        self._clear_results()
        
        inspirations = self.db.get_all_inspirations()
        for insp in inspirations:
            card = InspirationCard(insp)
            card.edit_requested.connect(self._edit_inspiration)
            card.delete_requested.connect(self._delete_inspiration)
            card.mark_used_requested.connect(self._mark_used)
            card.convert_to_event_requested.connect(self.convert_to_event.emit)
            self.results_layout.addWidget(card)
    
    def _clear_results(self):
        """清空结果"""
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _apply_filter(self):
        """应用筛选"""
        category = self.category_combo.currentData()
        status = self.status_combo.currentData()
        
        self._clear_results()
        
        if category is None and status is None:
            inspirations = self.db.get_all_inspirations()
        elif category is not None and status is None:
            inspirations = self.db.get_inspirations_by_category(category)
        elif category is None and status is not None:
            inspirations = self.db.get_all_inspirations()
            inspirations = [i for i in inspirations if i.get('is_used') == status]
        else:
            inspirations = self.db.get_inspirations_by_category(category)
            inspirations = [i for i in inspirations if i.get('is_used') == status]
        
        for insp in inspirations:
            card = InspirationCard(insp)
            card.edit_requested.connect(self._edit_inspiration)
            card.delete_requested.connect(self._delete_inspiration)
            card.mark_used_requested.connect(self._mark_used)
            card.convert_to_event_requested.connect(self.convert_to_event.emit)
            self.results_layout.addWidget(card)
    
    def _search(self):
        """执行搜索"""
        query = self.search_edit.text().strip()
        if not query:
            self._apply_filter()
            return
        
        search_type = self.search_type_combo.currentData()
        
        self._clear_results()
        
        if search_type == 'keyword':
            results = self.db.search_inspirations_keyword(query)
        elif search_type == 'semantic':
            results = self.semantic_searcher.semantic_search(query)
        else:
            results = self.semantic_searcher.hybrid_search(query)
        
        for res in results:
            insp = self.db.get_inspiration(res['id'])
            if insp:
                card = InspirationCard(insp)
                card.edit_requested.connect(self._edit_inspiration)
                card.delete_requested.connect(self._delete_inspiration)
                card.mark_used_requested.connect(self._mark_used)
                card.convert_to_event_requested.connect(self.convert_to_event.emit)
                self.results_layout.addWidget(card)
    
    def _show_quick_add(self):
        """显示快速添加对话框"""
        dialog = QuickInspirationDialog(self.db, self.semantic_searcher, self)
        if dialog.exec() == QDialog.Accepted:
            self._apply_filter()
    
    def _edit_inspiration(self, insp_id):
        """编辑灵感"""
        from dialogs import EditInspirationDialog
        dialog = EditInspirationDialog(self.db, insp_id, self)
        if dialog.exec() == QDialog.Accepted:
            self._apply_filter()
    
    def _delete_inspiration(self, insp_id):
        """删除灵感"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该灵感吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_inspiration(insp_id)
            self._apply_filter()
    
    def _mark_used(self, insp_id):
        """标记为已使用"""
        self.db.update_inspiration(insp_id, is_used=1)
        self._apply_filter()
    
    def refresh(self):
        """刷新面板"""
        self._apply_filter()


class GlobalSearchDialog(QDialog):
    """全局搜索对话框"""
    
    event_found = Signal(int)
    
    def __init__(self, db_manager, semantic_searcher, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.semantic_searcher = semantic_searcher
        self.setStyleSheet(APP_STYLESHEET)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🔍 全局搜索")
        self.resize(600, 450)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 搜索框
        search_row = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词或描述...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #1F2937;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
                outline: none;
            }
        """)
        search_row.addWidget(self.search_edit)
        
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem("全部", "all")
        self.search_type_combo.addItem("灵感", "inspiration")
        self.search_type_combo.addItem("事件", "event")
        self.search_type_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #1F2937;
                padding: 6px;
                font-size: 13px;
            }
        """)
        search_row.addWidget(self.search_type_combo)
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #2563EB;
            }
        """)
        search_row.addWidget(self.search_btn)
        
        layout.addLayout(search_row)
        
        # 搜索结果区域
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #1F2937;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #E5E7EB;
            }
            QListWidget::item:hover {
                background: #F3F4F6;
            }
        """)
        layout.addWidget(self.results_list)
        
        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #E5E7EB;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #D1D5DB;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)
        
        self.search_btn.clicked.connect(self._search)
        self.search_edit.returnPressed.connect(self._search)
        self.results_list.itemDoubleClicked.connect(self._on_item_clicked)
    
    def _search(self):
        """执行全局搜索"""
        query = self.search_edit.text().strip()
        if not query:
            return
        
        search_type = self.search_type_combo.currentData()
        
        self.results_list.clear()
        
        results = []
        
        if search_type in ('all', 'inspiration'):
            insp_results = self.semantic_searcher.hybrid_search(query)
            for res in insp_results:
                results.append({
                    'type': 'inspiration',
                    'id': res['id'],
                    'title': res['category_name'],
                    'content': res['content'],
                    'similarity': res['similarity'],
                })
        
        if search_type in ('all', 'event'):
            event_results = self.semantic_searcher.search_events(query)
            for res in event_results:
                results.append({
                    'type': 'event',
                    'id': res['id'],
                    'title': res['timestamp'],
                    'content': res['title'],
                    'similarity': res['similarity'],
                })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        for res in results[:10]:
            icon = "✨" if res['type'] == 'inspiration' else "📅"
            sim_str = f"{res['similarity']:.2f}"
            item_text = f"{icon} [{sim_str}] {res['title']} - {res['content'][:50]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, res)
            self.results_list.addItem(item)
    
    def _on_item_clicked(self, item):
        """点击搜索结果"""
        data = item.data(Qt.UserRole)
        if data['type'] == 'event':
            self.event_found.emit(data['id'])
            self.close()