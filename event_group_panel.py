"""事件组管理面板"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QProgressBar, QTextEdit, QScrollArea, QAbstractItemView,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from constants import APP_STYLESHEET

EVENT_GROUP_STATUS_OPTIONS = [
    ("规划中", 0),
    ("进行中", 1),
    ("已完成", 2),
    ("已暂停", 3),
]

EVENT_GROUP_RELATION_TYPES = [
    ("起因", 0),
    ("发展", 1),
    ("高潮", 2),
    ("结局", 3),
    ("分支", 4),
]

RELATION_COLORS = {
    0: "#8B5CF6",
    1: "#3B82F6",
    2: "#EF4444",
    3: "#10B981",
    4: "#F59E0B",
}


class EventGroupCard(QFrame):
    """事件组卡片"""
    
    group_clicked = Signal(int)
    group_edit_requested = Signal(int)
    
    def __init__(self, group_data, parent=None):
        super().__init__(parent)
        self.group_data = group_data
        
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
            }
            QFrame:hover {
                border-color: #8B5CF6;
                background-color: #F9FAFB;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 标题和状态
        header_layout = QHBoxLayout()
        
        color_dot = QLabel()
        color_dot.setFixedSize(12, 12)
        color_dot.setStyleSheet(f"background-color: {group_data.get('color', '#8B5CF6')}; border-radius: 6px;")
        header_layout.addWidget(color_dot)
        
        title_label = QLabel(group_data['name'])
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setStyleSheet("color: #1F2937;")
        header_layout.addWidget(title_label)
        
        status_name = EVENT_GROUP_STATUS_OPTIONS[group_data.get('status', 0)][0]
        status_label = QLabel(f"[{status_name}]")
        status_label.setStyleSheet("font-size: 11px; color: #6B7280;")
        header_layout.addWidget(status_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(group_data.get('progress', 0))
        progress_bar.setFixedHeight(8)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #E5E7EB;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: #8B5CF6;
            }
        """)
        progress_layout.addWidget(progress_bar)
        
        progress_label = QLabel(f"{group_data.get('progress', 0)}%")
        progress_label.setStyleSheet("font-size: 11px; color: #6B7280;")
        progress_label.setFixedWidth(40)
        progress_layout.addWidget(progress_label)
        layout.addLayout(progress_layout)
        
        # 描述
        if group_data.get('description'):
            desc_label = QLabel(group_data['description'])
            desc_label.setStyleSheet("font-size: 11px; color: #4B5563;")
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(40)
            layout.addWidget(desc_label)
        
        # 事件数量
        event_count = group_data.get('event_count', 0)
        count_label = QLabel(f"包含 {event_count} 个事件")
        count_label.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        layout.addWidget(count_label)
        
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.group_clicked.emit(self.group_data['id'])
        elif event.button() == Qt.RightButton:
            self.group_edit_requested.emit(self.group_data['id'])
        super().mousePressEvent(event)


class EventGroupDetailPanel(QWidget):
    """事件组详情面板"""
    
    event_selected = Signal(int)
    edit_requested = Signal(int)
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.group_id = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.empty_label = QLabel("选择一个事件组查看详情")
        self.empty_label.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setMinimumHeight(200)
        layout.addWidget(self.empty_label)
        
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_layout.setSpacing(10)
        self.detail_widget.hide()
        layout.addWidget(self.detail_widget)
        
        # 标题区域
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background-color: #FFFFFF; padding: 12px; border-radius: 8px;")
        self.header_layout = QVBoxLayout(self.header_frame)
        
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #1F2937;")
        self.header_layout.addWidget(self.title_label)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        self.header_layout.addWidget(self.status_label)
        
        self.detail_layout.addWidget(self.header_frame)
        
        # 进度条
        self.progress_layout = QHBoxLayout()
        self.progress_layout.addWidget(QLabel("整体进度:"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                background-color: #F3F4F6;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background-color: #8B5CF6;
            }
        """)
        self.progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        self.progress_label.setFixedWidth(50)
        self.progress_layout.addWidget(self.progress_label)
        
        self.detail_layout.addLayout(self.progress_layout)
        
        # 描述
        self.desc_edit = QTextEdit()
        self.desc_edit.setReadOnly(True)
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                color: #4B5563;
            }
        """)
        self.detail_layout.addWidget(self.desc_edit)
        
        # 事件列表标题
        events_header_layout = QHBoxLayout()
        events_header_layout.addWidget(QLabel("事件进程"))
        events_header_layout.addStretch()
        self.detail_layout.addLayout(events_header_layout)
        
        # 事件流程图
        self.event_flow_scroll = QScrollArea()
        self.event_flow_scroll.setWidgetResizable(True)
        self.event_flow_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.event_flow_widget = QWidget()
        self.event_flow_layout = QVBoxLayout(self.event_flow_widget)
        self.event_flow_layout.setSpacing(0)
        self.event_flow_layout.setContentsMargins(0, 0, 0, 0)
        
        self.event_flow_scroll.setWidget(self.event_flow_widget)
        self.detail_layout.addWidget(self.event_flow_scroll)
    
    def load_group(self, group_id):
        self.group_id = group_id
        group_data = self.db.get_event_group_with_events(group_id)
        
        if not group_data:
            self.empty_label.show()
            self.detail_widget.hide()
            return
        
        self.empty_label.hide()
        self.detail_widget.show()
        
        # 更新基本信息
        self.title_label.setText(group_data['name'])
        
        status_name = EVENT_GROUP_STATUS_OPTIONS[group_data.get('status', 0)][0]
        color = group_data.get('color', '#8B5CF6')
        self.status_label.setText(f"{status_name} · {len(group_data.get('events', []))} 个事件")
        
        self.progress_bar.setValue(group_data.get('progress', 0))
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {color};
                border-radius: 6px;
                background-color: #F3F4F6;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background-color: {color};
            }}
        """)
        self.progress_label.setText(f"{group_data.get('progress', 0)}%")
        
        self.desc_edit.setText(group_data.get('description', '') or "暂无描述")
        
        # 清空事件流
        while self.event_flow_layout.count():
            child = self.event_flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 构建事件流程
        events = group_data.get('events', [])
        if not events:
            no_event_label = QLabel("暂无关联事件")
            no_event_label.setStyleSheet("color: #9CA3AF; padding: 10px;")
            self.event_flow_layout.addWidget(no_event_label)
            return
        
        # 按时间排序
        events.sort(key=lambda x: x['timestamp'])
        
        for i, ev in enumerate(events):
            event_item = EventFlowItem(ev, i == len(events) - 1, self)
            event_item.clicked.connect(self._on_event_clicked)
            event_item.edit_requested.connect(self._on_edit_requested)
            self.event_flow_layout.addWidget(event_item)
    
    def _on_event_clicked(self, event_id):
        self.event_selected.emit(event_id)
    
    def _on_edit_requested(self, event_id):
        self.edit_requested.emit(event_id)


class EventFlowItem(QFrame):
    """事件流程项"""
    
    clicked = Signal(int)
    edit_requested = Signal(int)
    
    def __init__(self, event_data, is_last, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-left: 3px solid #8B5CF6;
                margin-bottom: 0;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #F9FAFB;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # 关系类型标签
        rel_type = event_data.get('relation_type', 0)
        rel_name = EVENT_GROUP_RELATION_TYPES[rel_type][0]
        rel_color = RELATION_COLORS.get(rel_type, '#8B5CF6')
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-left: 3px solid {rel_color};
                margin-bottom: 0;
                padding: 10px;
            }}
            QFrame:hover {{
                background-color: #F9FAFB;
            }}
        """)
        
        # 时间和关系类型
        top_layout = QHBoxLayout()
        
        time_label = QLabel(f"⏰ {event_data['timestamp']}")
        time_label.setStyleSheet("font-size: 11px; color: #6B7280;")
        top_layout.addWidget(time_label)
        
        rel_label = QLabel(f"🏷️ {rel_name}")
        rel_label.setStyleSheet(f"font-size: 11px; color: {rel_color};")
        top_layout.addWidget(rel_label)
        
        ch_name = event_data.get('character_name', '')
        if ch_name:
            ch_label = QLabel(f"👤 {ch_name}")
            ch_label.setStyleSheet("font-size: 11px; color: #6B7280;")
            top_layout.addWidget(ch_label)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 标题
        title_label = QLabel(event_data['title'])
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setStyleSheet("color: #1F2937;")
        layout.addWidget(title_label)
        
        # 内容预览
        content = event_data.get('content', '')
        if content:
            preview = content[:100] + "..." if len(content) > 100 else content
            content_label = QLabel(preview)
            content_label.setStyleSheet("font-size: 11px; color: #4B5563;")
            content_label.setWordWrap(True)
            content_label.setMaximumHeight(40)
            layout.addWidget(content_label)
        
        # 状态
        writing_status = event_data.get('writing_status', 0)
        status_names = ["未写", "草稿中", "已完成", "已发布"]
        status_colors = ["#9CA3AF", "#F59E0B", "#10B981", "#3B82F6"]
        
        status_label = QLabel(status_names[writing_status])
        status_label.setStyleSheet(f"font-size: 11px; color: {status_colors[writing_status]};")
        layout.addWidget(status_label)
        
        # 连接线（如果不是最后一项）
        if not is_last:
            line_layout = QHBoxLayout()
            line_layout.addSpacing(8)
            line = QFrame()
            line.setFixedSize(2, 15)
            line.setStyleSheet(f"background-color: {rel_color};")
            line_layout.addWidget(line)
            line_layout.addStretch()
            layout.addLayout(line_layout)
        
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.event_data['id'])
        elif event.button() == Qt.RightButton:
            self.edit_requested.emit(self.event_data['id'])
        super().mousePressEvent(event)


class EventGroupPanel(QWidget):
    """事件组管理主面板"""
    
    group_selected = Signal(int)
    event_selected = Signal(int)
    group_edit_requested = Signal(int)
    event_edit_requested = Signal(int)
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setStyleSheet(APP_STYLESHEET)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧事件组列表
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #F3F4F6;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)
        left_panel.setMinimumWidth(280)
        
        # 标题和操作按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("📦 事件组")
        title_label.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        title_label.setStyleSheet("color: #1F2937;")
        header_layout.addWidget(title_label)
        
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(28, 28)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #7C3AED;
            }
        """)
        header_layout.addWidget(self.add_btn)
        
        header_layout.addStretch()
        left_layout.addLayout(header_layout)
        
        # 事件组列表
        self.group_scroll = QScrollArea()
        self.group_scroll.setWidgetResizable(True)
        self.group_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.group_list_widget = QWidget()
        self.group_list_layout = QVBoxLayout(self.group_list_widget)
        self.group_list_layout.setSpacing(6)
        self.group_list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.group_scroll.setWidget(self.group_list_widget)
        left_layout.addWidget(self.group_scroll)
        
        layout.addWidget(left_panel)
        
        # 右侧详情面板
        self.detail_panel = EventGroupDetailPanel(db_manager)
        self.detail_panel.setStyleSheet("background-color: #FFFFFF;")
        layout.addWidget(self.detail_panel)
        
        # 连接信号
        self.add_btn.clicked.connect(self._on_add_group)
        
        # 刷新列表
        self.refresh()
    
    def refresh(self):
        """刷新事件组列表"""
        while self.group_list_layout.count():
            child = self.group_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        groups = self.db.get_all_event_groups()
        if not groups:
            empty_label = QLabel("暂无事件组")
            empty_label.setStyleSheet("color: #9CA3AF; padding: 20px; text-align: center;")
            self.group_list_layout.addWidget(empty_label)
            return
        
        for group in groups:
            group_with_events = self.db.get_event_group_with_events(group['id'])
            group['event_count'] = len(group_with_events.get('events', []))
            
            card = EventGroupCard(group)
            card.group_clicked.connect(self._on_group_clicked)
            card.group_edit_requested.connect(self._on_group_edit_requested)
            self.group_list_layout.addWidget(card)
        
        self.group_list_layout.addStretch()
    
    def _on_add_group(self):
        self.group_edit_requested.emit(0)
    
    def _on_group_clicked(self, group_id):
        self.group_selected.emit(group_id)
        self.detail_panel.load_group(group_id)
    
    def _on_group_edit_requested(self, group_id):
        self.group_edit_requested.emit(group_id)
    
    def select_group(self, group_id):
        """选择指定事件组"""
        self._on_group_clicked(group_id)