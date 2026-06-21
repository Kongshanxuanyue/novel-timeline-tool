"""常量定义模块"""

from timeline_canvas import EVENT_TYPE_NORMAL, EVENT_TYPE_SPECIAL, EVENT_TYPE_BIRTH, EVENT_TYPE_DEATH

# 全局明亮主题样式表
APP_STYLESHEET = """
/* 全局字体和基础设置 */
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* 对话框背景 */
QDialog {
    background-color: #FAFBFC;
}

/* 主面板卡片 */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 12px;
}

/* 标签样式 */
QLabel {
    color: #374151;
    background-color: transparent;
}

/* 标题标签 */
QLabel#title {
    font-size: 15px;
    font-weight: bold;
    color: #111827;
}

/* 副标题标签 */
QLabel#subtitle {
    font-size: 12px;
    color: #6B7280;
}

/* 输入框 */
QLineEdit, QTextEdit, QSpinBox, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 8px 12px;
    color: #111827;
    selection-background-color: #8B5CF6;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 2px solid #8B5CF6;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #F3F4F6;
    color: #9CA3AF;
}

/* 按钮 */
QPushButton {
    background-color: #8B5CF6;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: 500;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #7C3AED;
}

QPushButton:pressed {
    background-color: #6D28D9;
}

QPushButton:disabled {
    background-color: #D1D5DB;
    color: #9CA3AF;
}

/* 次要按钮 */
QPushButton#secondary {
    background-color: #F3F4F6;
    color: #374151;
    border: 1px solid #D1D5DB;
}

QPushButton#secondary:hover {
    background-color: #E5E7EB;
    border-color: #9CA3AF;
}

/* 危险按钮（删除等） */
QPushButton#danger {
    background-color: #EF4444;
}

QPushButton#danger:hover {
    background-color: #DC2626;
}

/* 成功按钮 */
QPushButton#success {
    background-color: #10B981;
}

QPushButton#success:hover {
    background-color: #059669;
}

/* 列表 */
QListWidget, QTreeWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 4px;
    alternate-background-color: #F9FAFB;
}

QListWidget::item, QTreeWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
}

QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #EDE9FE;
    color: #6D28D9;
}

QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #F3F4F6;
}

/* 选项卡 */
QTabWidget::pane {
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    background-color: #FFFFFF;
    padding: 12px;
}

QTabBar::tab {
    background-color: #F3F4F6;
    color: #6B7280;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #8B5CF6;
    font-weight: bold;
    border: 1px solid #E5E7EB;
    border-bottom: none;
}

QTabBar::tab:hover:!selected {
    background-color: #E5E7EB;
}

/* 进度条 */
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #E5E7EB;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #8B5CF6;
    border-radius: 4px;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: #F3F4F6;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #D1D5DB;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9CA3AF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #F3F4F6;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #D1D5DB;
    border-radius: 5px;
    min-width: 30px;
}

/* 分隔线 */
QFrame#separator {
    background-color: #E5E7EB;
    max-height: 1px;
}

/* 复选框 */
QCheckBox {
    color: #374151;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #D1D5DB;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #8B5CF6;
    border-color: #8B5CF6;
}

/* 工具提示 */
QToolTip {
    background-color: #1F2937;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
}

/* 菜单 */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #EDE9FE;
    color: #6D28D9;
}

/* 状态栏 */
QStatusBar {
    background-color: #F9FAFB;
    color: #6B7280;
    border-top: 1px solid #E5E7EB;
}

/* 表格 */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    gridline-color: #F3F4F6;
}

QTableWidget::item {
    padding: 10px;
}

QTableWidget::item:selected {
    background-color: #EDE9FE;
}

/* 标题栏按钮 */
QDialog QAbstractButton {
    min-width: 90px;
}
"""

COLOR_OPTIONS = [
    ("绿色", "#10B981"),
    ("蓝色", "#3B82F6"),
    ("红色", "#EF4444"),
    ("橙色", "#F59E0B"),
    ("紫色", "#8B5CF6"),
    ("粉色", "#EC4899"),
    ("青色", "#06B6D4"),
    ("灰色", "#6B7280"),
]

EVENT_TYPE_OPTIONS = [
    ("普通事件", EVENT_TYPE_NORMAL),
    ("特殊事件", EVENT_TYPE_SPECIAL),
    ("出生", EVENT_TYPE_BIRTH),
    ("死亡", EVENT_TYPE_DEATH),
]

EVENT_TYPE_ICONS = {
    EVENT_TYPE_NORMAL: "●",
    EVENT_TYPE_SPECIAL: "◆",
    EVENT_TYPE_BIRTH: "▲",
    EVENT_TYPE_DEATH: "▼",
}

EVENT_TYPE_NAMES = {
    EVENT_TYPE_NORMAL: "普通",
    EVENT_TYPE_SPECIAL: "特殊",
    EVENT_TYPE_BIRTH: "出生",
    EVENT_TYPE_DEATH: "死亡",
}