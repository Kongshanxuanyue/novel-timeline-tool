"""情节线索/伏笔管理面板"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QGridLayout, QComboBox, QMessageBox, QMenu, QTextEdit,
    QListWidget, QListWidgetItem, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QAction

from database import DatabaseManager

# 线索类别
THREAD_CATEGORY_NAMES = {
    0: "伏笔",
    1: "主线线索",
    2: "支线线索",
    3: "悬念",
}

# 线索状态
THREAD_STATUS_NAMES = {
    0: "待埋设",
    1: "已埋设",
    2: "待回收",
    3: "已回收",
    4: "已废弃",
}

THREAD_STATUS_COLORS = {
    0: "#9CA3AF",  # 待埋设 - 灰色
    1: "#3B82F6",  # 已埋设 - 蓝色
    2: "#F59E0B",  # 待回收 - 橙色
    3: "#10B981",  # 已回收 - 绿色
    4: "#EF4444",  # 已废弃 - 红色
}

# 关系类型
RELATION_TYPE_NAMES = {
    0: "埋设",
    1: "推进",
    2: "回收",
    3: "提及",
}


class ThreadCard(QFrame):
    """线索卡片"""
    
    clicked = Signal(int)  # thread_id
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    
    def __init__(self, thread_data, event_count):
        super().__init__()
        self.thread_data = thread_data
        self.event_count = event_count
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
        self.setCursor(Qt.PointingHandCursor)
        
        # 根据重要性设置背景色渐变（红=最重要）
        importance = thread_data.get('importance', 3)
        base_color = self._get_importance_color(importance)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {base_color};
                border-radius: 8px;
                border: 2px solid {THREAD_STATUS_COLORS.get(thread_data.get('status', 0), '#9CA3AF')};
            }}
            QFrame:hover {{
                border: 3px solid #FBBF24;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        
        # 名称
        name_label = QLabel(thread_data.get('name', '未命名'))
        name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        name_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(name_label)
        
        # 类别和状态
        info_row = QHBoxLayout()
        category = THREAD_CATEGORY_NAMES.get(thread_data.get('category', 0), "伏笔")
        status = THREAD_STATUS_NAMES.get(thread_data.get('status', 0), "待埋设")
        status_color = THREAD_STATUS_COLORS.get(thread_data.get('status', 0), '#9CA3AF')
        
        cat_label = QLabel(f"[{category}]")
        cat_label.setStyleSheet("color: #E5E7EB; font-size: 11px;")
        info_row.addWidget(cat_label)
        
        status_label = QLabel(status)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 11px; font-weight: bold;")
        info_row.addWidget(status_label)
        
        info_row.addStretch()
        layout.addLayout(info_row)
        
        # 重要性星级
        stars = "★" * importance + "☆" * (5 - importance)
        stars_label = QLabel(f"重要性: {stars}")
        stars_label.setStyleSheet("color: #FBBF24; font-size: 11px;")
        layout.addWidget(stars_label)
        
        # 关联事件数
        events_label = QLabel(f"关联事件: {event_count}")
        events_label.setStyleSheet("color: #E5E7EB; font-size: 10px;")
        layout.addWidget(events_label)
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _get_importance_color(self, importance):
        """根据重要性返回背景色"""
        colors = {
            5: "#B91C1C",  # 最重要 - 深红
            4: "#DC2626",  # 重要 - 红
            3: "#F97316",  # 中等 - 橙
            2: "#FBBF24",  # 一般 - 黄
            1: "#6B7280",  # 不重要 - 灰
        }
        return colors.get(importance, "#F97316")
    
    def _show_context_menu(self, pos):
        menu = QMenu()
        edit_action = menu.addAction("编辑线索")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.thread_data['id']))
        
        delete_action = menu.addAction("删除线索")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.thread_data['id']))
        
        menu.exec_(self.mapToGlobal(pos))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.thread_data['id'])
        super().mousePressEvent(event)


class ThreadColumn(QWidget):
    """线索状态列"""
    
    thread_clicked = Signal(int)
    thread_edit_requested = Signal(int)
    thread_delete_requested = Signal(int)
    
    def __init__(self, status, db_manager):
        super().__init__()
        self.status = status
        self.db = db_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 列标题
        status_name = THREAD_STATUS_NAMES.get(status, "未知")
        status_color = THREAD_STATUS_COLORS.get(status, '#9CA3AF')
        header = QLabel(f"📋 {status_name}")
        header.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        header.setStyleSheet(f"color: {status_color}; padding: 4px;")
        layout.addWidget(header)
        
        # 卡片滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.cards_widget)
        layout.addWidget(scroll)
        
        self._load_threads()
    
    def _load_threads(self):
        """加载该状态的线索"""
        # 清空现有卡片
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        threads = self.db.get_plot_threads_by_status(self.status)
        for thread in threads:
            event_count = self.db.get_thread_event_count(thread['id'])
            card = ThreadCard(thread, event_count)
            card.clicked.connect(self.thread_clicked.emit)
            card.edit_requested.connect(self.thread_edit_requested.emit)
            card.delete_requested.connect(self.thread_delete_requested.emit)
            self.cards_layout.addWidget(card)
        
        # 统计数量
        count_label = QLabel(f"共 {len(threads)} 条")
        count_label.setStyleSheet("color: #9CA3AF; font-size: 10px;")
        self.cards_layout.addWidget(count_label)
    
    def refresh(self):
        self._load_threads()


class ThreadDetailPanel(QWidget):
    """线索详情面板"""
    
    event_link_requested = Signal(int, int, int)  # thread_id, event_id, relation_type
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.current_thread_id = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # 标题
        self.title_label = QLabel("线索详情")
        self.title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #E5E7EB;")
        layout.addWidget(self.title_label)
        
        # 基本信息
        self.info_group = QGroupBox("基本信息")
        self.info_group.setStyleSheet("QGroupBox { color: #E5E7EB; font-weight: bold; }")
        info_layout = QVBoxLayout(self.info_group)
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet("color: #FFFFFF; font-size: 12px;")
        info_layout.addWidget(self.name_label)
        
        self.category_label = QLabel()
        self.category_label.setStyleSheet("color: #E5E7EB;")
        info_layout.addWidget(self.category_label)
        
        self.status_label = QLabel()
        info_layout.addWidget(self.status_label)
        
        self.importance_label = QLabel()
        self.importance_label.setStyleSheet("color: #FBBF24;")
        info_layout.addWidget(self.importance_label)
        
        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(80)
        self.desc_text.setStyleSheet("color: #E5E7EB; background: #1F2937; border: none;")
        info_layout.addWidget(self.desc_text)
        
        layout.addWidget(self.info_group)
        
        # 关联事件
        self.events_group = QGroupBox("关联事件时间线")
        self.events_group.setStyleSheet("QGroupBox { color: #E5E7EB; font-weight: bold; }")
        events_layout = QVBoxLayout(self.events_group)
        
        self.events_list = QListWidget()
        self.events_list.setStyleSheet("""
            QListWidget { background: #1F2937; border: none; color: #E5E7EB; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #374151; }
            QListWidget::item:selected { background: #3B82F6; }
        """)
        events_layout.addWidget(self.events_list)
        
        # 添加关联按钮
        add_event_btn = QPushButton("➕ 添加关联事件")
        add_event_btn.clicked.connect(self._add_event_link)
        events_layout.addWidget(add_event_btn)
        
        layout.addWidget(self.events_group)
        
        # 操作按钮
        btn_row = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ 编辑")
        btn_row.addWidget(self.edit_btn)
        
        self.change_status_btn = QPushButton("🔄 更改状态")
        btn_row.addWidget(self.change_status_btn)
        
        self.export_btn = QPushButton("📄 导出")
        btn_row.addWidget(self.export_btn)
        
        layout.addLayout(btn_row)
    
    def load_thread(self, thread_id):
        """加载线索详情"""
        self.current_thread_id = thread_id
        thread = self.db.get_plot_thread(thread_id)
        if not thread:
            return
        
        self.title_label.setText(f"线索详情: {thread['name']}")
        self.name_label.setText(f"名称: {thread['name']}")
        
        category = THREAD_CATEGORY_NAMES.get(thread.get('category', 0), "伏笔")
        self.category_label.setText(f"类别: {category}")
        
        status = THREAD_STATUS_NAMES.get(thread.get('status', 0), "待埋设")
        status_color = THREAD_STATUS_COLORS.get(thread.get('status', 0), '#9CA3AF')
        self.status_label.setText(f"状态: {status}")
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        
        importance = thread.get('importance', 3)
        stars = "★" * importance + "☆" * (5 - importance)
        self.importance_label.setText(f"重要性: {stars}")
        
        self.desc_text.setPlainText(thread.get('description', '暂无描述'))
        
        # 加载关联事件
        self._load_events(thread_id)
    
    def _load_events(self, thread_id):
        """加载关联事件"""
        self.events_list.clear()
        events = self.db.get_thread_events(thread_id)
        
        for ev in events:
            rel_type = RELATION_TYPE_NAMES.get(ev.get('relation_type', 0), "埋设")
            timestamp = ev.get('timestamp', '')
            title = ev.get('title', '')
            char_name = ev.get('character_name', '')
            
            item_text = f"[{rel_type}] {timestamp} - {title} ({char_name})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ev['event_id'])
            self.events_list.addItem(item)
    
    def _add_event_link(self):
        """添加关联事件"""
        if not self.current_thread_id:
            return
        
        from dialogs import LinkEventToThreadDialog
        dialog = LinkEventToThreadDialog(self.db, self.current_thread_id, self)
        if dialog.exec() == QDialog.Accepted:
            self._load_events(self.current_thread_id)
    
    def clear(self):
        """清空详情"""
        self.current_thread_id = None
        self.title_label.setText("线索详情")
        self.name_label.setText("")
        self.category_label.setText("")
        self.status_label.setText("")
        self.importance_label.setText("")
        self.desc_text.setPlainText("")
        self.events_list.clear()


class PlotThreadBoard(QWidget):
    """线索看板面板"""
    
    thread_selected = Signal(int)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 顶部控制栏
        control_row = QHBoxLayout()
        
        control_row.addWidget(QLabel("线索管理:"))
        
        add_btn = QPushButton("➕ 新建线索")
        add_btn.clicked.connect(self._add_thread)
        control_row.addWidget(add_btn)
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh)
        control_row.addWidget(refresh_btn)
        
        export_btn = QPushButton("📄 导出清单")
        export_btn.clicked.connect(self._export_threads)
        control_row.addWidget(export_btn)
        
        control_row.addStretch()
        
        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #F59E0B; font-size: 11px;")
        control_row.addWidget(self.stats_label)
        
        layout.addLayout(control_row)
        
        # 提醒区域
        self.alert_label = QLabel()
        self.alert_label.setStyleSheet("color: #EF4444; font-size: 11px; padding: 4px;")
        self.alert_label.setVisible(False)
        layout.addWidget(self.alert_label)
        
        # 看板区域（竖向排列）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.columns_widget = QWidget()
        columns_layout = QVBoxLayout(self.columns_widget)
        columns_layout.setContentsMargins(8, 8, 8, 8)
        columns_layout.setSpacing(12)
        
        self.columns = {}
        for status in [0, 1, 2, 3, 4]:
            column = ThreadColumn(status, self.db)
            column.thread_clicked.connect(self._on_thread_clicked)
            column.thread_edit_requested.connect(self._edit_thread)
            column.thread_delete_requested.connect(self._delete_thread)
            columns_layout.addWidget(column)
            self.columns[status] = column
        
        scroll.setWidget(self.columns_widget)
        layout.addWidget(scroll)
        
        self._update_stats()
        self._check_overdue()
    
    def _update_stats(self):
        """更新统计信息"""
        stats = self.db.get_unresolved_threads_stats()
        if stats:
            total = sum(s['count'] for s in stats)
            self.stats_label.setText(f"未回收线索: {total} 条")
        else:
            self.stats_label.setText("未回收线索: 0 条")
    
    def _check_overdue(self):
        """检查超期线索"""
        overdue = self.db.get_overdue_threads(10)
        if overdue:
            names = [t['name'] for t in overdue[:3]]
            alert_text = f"⚠️ 超期未回收: {', '.join(names)}..."
            self.alert_label.setText(alert_text)
            self.alert_label.setVisible(True)
        else:
            self.alert_label.setVisible(False)
    
    def _on_thread_clicked(self, thread_id):
        self.thread_selected.emit(thread_id)
    
    def _add_thread(self):
        from dialogs import AddPlotThreadDialog
        dialog = AddPlotThreadDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
    
    def _edit_thread(self, thread_id):
        from dialogs import EditPlotThreadDialog
        dialog = EditPlotThreadDialog(self.db, thread_id, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
    
    def _delete_thread(self, thread_id):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该线索吗？\n关联的事件也会解除关联。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_plot_thread(thread_id)
            self.refresh()
    
    def _export_threads(self):
        """导出伏笔清单"""
        threads = self.db.get_all_plot_threads()
        if not threads:
            QMessageBox.information(self, "提示", "暂无线索可导出")
            return
        
        md = "# 伏笔/线索清单\n\n"
        
        for status in [0, 1, 2, 3, 4]:
            status_threads = [t for t in threads if t.get('status') == status]
            if status_threads:
                status_name = THREAD_STATUS_NAMES.get(status, "未知")
                md += f"## {status_name}\n\n"
                for t in status_threads:
                    importance = t.get('importance', 3)
                    stars = "★" * importance + "☆" * (5 - importance)
                    category = THREAD_CATEGORY_NAMES.get(t.get('category', 0), "伏笔")
                    
                    md += f"### {t['name']}\n\n"
                    md += f"- **类别**: {category}\n"
                    md += f"- **重要性**: {stars}\n"
                    if t.get('description'):
                        md += f"- **描述**: {t['description']}\n"
                    
                    # 关联事件
                    events = self.db.get_thread_events(t['id'])
                    if events:
                        md += f"- **关联事件**:\n"
                        for ev in events:
                            rel_type = RELATION_TYPE_NAMES.get(ev.get('relation_type', 0), "埋设")
                            md += f"  - [{rel_type}] {ev.get('timestamp', '')} - {ev.get('title', '')}\n"
                    md += "\n"
        
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "导出伏笔清单", "", "Markdown (*.md)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md)
            QMessageBox.information(self, "导出成功", f"已保存到:\n{file_path}")
    
    def refresh(self):
        """刷新看板"""
        for column in self.columns.values():
            column.refresh()
        self._update_stats()
        self._check_overdue()
    
    def link_event_to_thread(self, event_id, thread_id=None):
        """将事件关联到线索"""
        if thread_id:
            self.db.link_event_to_thread(thread_id, event_id, relation_type=0)
            self.refresh()
        else:
            # 让用户选择线索
            from dialogs import SelectThreadDialog
            dialog = SelectThreadDialog(self.db, self)
            if dialog.exec() == QDialog.Accepted:
                selected_id = dialog.get_selected_thread_id()
                if selected_id:
                    self.db.link_event_to_thread(selected_id, event_id, relation_type=0)
                    self.refresh()