"""对话框模块"""

import re
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QTextEdit, QGridLayout,
    QMessageBox, QAbstractItemView, QSpinBox, QComboBox, QHBoxLayout,
    QVBoxLayout, QListWidget, QListWidgetItem, QCheckBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from constants import COLOR_OPTIONS, EVENT_TYPE_OPTIONS, EVENT_TYPE_ICONS, APP_STYLESHEET
from timeline_canvas import EVENT_TYPE_BIRTH, EVENT_TYPE_DEATH
from database import parse_time_to_value


class StyledDialog(QDialog):
    """统一样式对话框基类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(APP_STYLESHEET)


class ExportOptionsDialog(StyledDialog):
    """导出选项对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出选项")
        self.resize(600, 600)
        self.db = db_manager
        self.result = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.tabs = QTabWidget()
        
        self.tab_org_char = QWidget()
        self._setup_org_char_tab()
        self.tabs.addTab(self.tab_org_char, "📦👤 组织/人物筛选")
        
        self.tab_events = QWidget()
        self._setup_events_tab()
        self.tabs.addTab(self.tab_events, "📍 事件筛选")
        
        self.tab_time = QWidget()
        self._setup_time_tab()
        self.tabs.addTab(self.tab_time, "⏰ 时间范围")

        layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定导出")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        ok_btn.clicked.connect(self._accept)
        cancel_btn.clicked.connect(self.reject)
        
        self._load_data()
    
    def _setup_org_char_tab(self):
        layout = QVBoxLayout(self.tab_org_char)
        
        org_label = QLabel("📦 选择组织（可选，不选则导出所有组织）")
        org_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(org_label)
        
        self.org_list = QListWidget()
        self.org_list.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.org_list)
        
        org_btn_layout = QHBoxLayout()
        self.select_all_orgs = QPushButton("全选组织")
        self.clear_all_orgs = QPushButton("清空组织")
        self.select_all_orgs.clicked.connect(self._select_all_orgs)
        self.clear_all_orgs.clicked.connect(self._clear_all_orgs)
        org_btn_layout.addWidget(self.select_all_orgs)
        org_btn_layout.addWidget(self.clear_all_orgs)
        org_btn_layout.addStretch()
        layout.addLayout(org_btn_layout)
        
        layout.addWidget(QLabel(""))

        char_label = QLabel("👤 选择人物（可选，不选则导出所有人物）")
        char_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(char_label)
        
        self.char_list = QListWidget()
        self.char_list.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.char_list)
        
        char_btn_layout = QHBoxLayout()
        self.select_all_chars = QPushButton("全选人物")
        self.clear_all_chars = QPushButton("清空人物")
        self.select_all_chars.clicked.connect(self._select_all_chars)
        self.clear_all_chars.clicked.connect(self._clear_all_chars)
        char_btn_layout.addWidget(self.select_all_chars)
        char_btn_layout.addWidget(self.clear_all_chars)
        char_btn_layout.addStretch()
        layout.addLayout(char_btn_layout)
    
    def _setup_events_tab(self):
        layout = QVBoxLayout(self.tab_events)
        
        event_label = QLabel("📍 选择具体事件（可选，不选则根据其他条件导出）")
        event_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(event_label)
        
        type_label = QLabel("📌 事件类型筛选")
        type_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(type_label)
        
        self.type_checkboxes = []
        type_layout = QHBoxLayout()
        for name, value in EVENT_TYPE_OPTIONS:
            checkbox = QCheckBox(name)
            checkbox.setChecked(True)
            checkbox.setProperty('type_value', value)
            self.type_checkboxes.append(checkbox)
            type_layout.addWidget(checkbox)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        layout.addWidget(QLabel("具体事件列表："))
        
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.event_list)
        
        event_btn_layout = QHBoxLayout()
        self.select_all_events = QPushButton("全选事件")
        self.clear_all_events = QPushButton("清空事件")
        self.select_all_events.clicked.connect(self._select_all_events)
        self.clear_all_events.clicked.connect(self._clear_all_events)
        event_btn_layout.addWidget(self.select_all_events)
        event_btn_layout.addWidget(self.clear_all_events)
        event_btn_layout.addStretch()
        layout.addLayout(event_btn_layout)
    
    def _setup_time_tab(self):
        layout = QVBoxLayout(self.tab_time)
        
        time_label = QLabel("⏰ 设置时间范围筛选（可选，不设置则导出所有时间）")
        time_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(time_label)
        
        time_grid = QGridLayout()
        
        time_grid.addWidget(QLabel("开始时间:"), 0, 0)
        self.start_year = QSpinBox()
        self.start_year.setRange(1, 99999)
        self.start_year.setValue(1)
        self.start_year.setPrefix("第")
        self.start_year.setSuffix("年")
        self.start_month = QSpinBox()
        self.start_month.setRange(1, 12)
        self.start_month.setValue(1)
        self.start_month.setSuffix("月")
        self.start_day = QSpinBox()
        self.start_day.setRange(1, 31)
        self.start_day.setValue(1)
        self.start_day.setSuffix("日")
        start_layout = QHBoxLayout()
        start_layout.addWidget(self.start_year)
        start_layout.addWidget(self.start_month)
        start_layout.addWidget(self.start_day)
        time_grid.addLayout(start_layout, 0, 1)
        
        time_grid.addWidget(QLabel("结束时间:"), 1, 0)
        self.end_year = QSpinBox()
        self.end_year.setRange(1, 99999)
        self.end_year.setValue(99999)
        self.end_year.setPrefix("第")
        self.end_year.setSuffix("年")
        self.end_month = QSpinBox()
        self.end_month.setRange(1, 12)
        self.end_month.setValue(12)
        self.end_month.setSuffix("月")
        self.end_day = QSpinBox()
        self.end_day.setRange(1, 31)
        self.end_day.setValue(31)
        self.end_day.setSuffix("日")
        end_layout = QHBoxLayout()
        end_layout.addWidget(self.end_year)
        end_layout.addWidget(self.end_month)
        end_layout.addWidget(self.end_day)
        time_grid.addLayout(end_layout, 1, 1)
        
        self.enable_time_filter = QCheckBox("启用时间范围筛选")
        self.enable_time_filter.setChecked(False)
        time_grid.addWidget(self.enable_time_filter, 2, 0, 1, 2)
        
        layout.addLayout(time_grid)
        layout.addStretch()
    
    def _load_data(self):
        self.org_list.clear()
        orgs = self.db.get_all_organizations()
        for org in orgs:
            item = QListWidgetItem(f"🏛️ {org['name']}")
            item.setData(Qt.UserRole, {'id': org['id'], 'name': org['name']})
            self.org_list.addItem(item)
        
        no_org_item = QListWidgetItem("🏛️ 无组织人物")
        no_org_item.setData(Qt.UserRole, {'id': 0, 'name': '无组织人物'})
        self.org_list.addItem(no_org_item)

        self.char_list.clear()
        chars = self.db.get_all_characters()
        for ch in chars:
            org_id = ch.get('organization_id')
            org_name = ""
            if org_id:
                org = self.db.get_organization(org_id)
                if org:
                    org_name = f" [{org['name']}]"
            item = QListWidgetItem(f"👤 {ch['name']}{org_name}")
            item.setData(Qt.UserRole, {'id': ch['id'], 'name': ch['name'], 'organization_id': org_id})
            self.char_list.addItem(item)
        
        self.event_list.clear()
        chars = self.db.get_all_characters()
        for ch in chars:
            events = self.db.get_events_by_character(ch['id'])
            for ev in events:
                type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
                item = QListWidgetItem(f"{type_icon} [{ev['timestamp']}] {ch['name']}: {ev['title']}")
                item.setData(Qt.UserRole, {'id': ev['id'], 'char_id': ch['id'], 'char_name': ch['name']})
                self.event_list.addItem(item)
    
    def _select_all_orgs(self):
        for i in range(self.org_list.count()):
            self.org_list.item(i).setSelected(True)
    
    def _clear_all_orgs(self):
        self.org_list.clearSelection()
    
    def _select_all_chars(self):
        for i in range(self.char_list.count()):
            self.char_list.item(i).setSelected(True)
    
    def _clear_all_chars(self):
        self.char_list.clearSelection()
    
    def _select_all_events(self):
        for i in range(self.event_list.count()):
            self.event_list.item(i).setSelected(True)
    
    def _clear_all_events(self):
        self.event_list.clearSelection()
    
    def _accept(self):
        selected_orgs = []
        for item in self.org_list.selectedItems():
            org_data = item.data(Qt.UserRole)
            selected_orgs.append(org_data['id'])
        
        selected_chars = []
        for item in self.char_list.selectedItems():
            char_data = item.data(Qt.UserRole)
            selected_chars.append(char_data['id'])
        
        selected_events = []
        for item in self.event_list.selectedItems():
            event_data = item.data(Qt.UserRole)
            selected_events.append(event_data['id'])
        
        selected_types = []
        for checkbox in self.type_checkboxes:
            if checkbox.isChecked():
                selected_types.append(checkbox.property('type_value'))
        
        start_time = None
        end_time = None
        if self.enable_time_filter.isChecked():
            start_time = f"第{self.start_year.value()}年{self.start_month.value()}月{self.start_day.value()}日"
            end_time = f"第{self.end_year.value()}年{self.end_month.value()}月{self.end_day.value()}日"
        
        self.result = {
            'org_ids': selected_orgs,
            'char_ids': selected_chars,
            'event_ids': selected_events,
            'event_types': selected_types,
            'start_time': start_time,
            'end_time': end_time
        }
        self.accept()


class AddCharacterDialog(QDialog):
    """添加人物对话框"""
    
    def __init__(self, db_manager, parent=None, org=None):
        super().__init__(parent)
        self.db = db_manager
        self.org = org
        
        self.setWindowTitle("添加人物")
        self.resize(400, 420)
        
        layout = QGridLayout(self)

        layout.addWidget(QLabel("人物名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入人物名称")
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("别名:"), 1, 0)
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("人物别名（可选）")
        layout.addWidget(self.alias_edit, 1, 1)

        layout.addWidget(QLabel("出生时间:"), 2, 0)
        self.birth_year = QSpinBox()
        self.birth_year.setRange(1, 99999)
        self.birth_year.setValue(1)
        self.birth_year.setPrefix("第")
        self.birth_year.setSuffix("年")
        self.birth_month = QSpinBox()
        self.birth_month.setRange(1, 12)
        self.birth_month.setValue(1)
        self.birth_month.setSuffix("月")
        self.birth_day = QSpinBox()
        self.birth_day.setRange(1, 31)
        self.birth_day.setValue(1)
        self.birth_day.setSuffix("日")
        birth_layout = QHBoxLayout()
        birth_layout.addWidget(self.birth_year)
        birth_layout.addWidget(self.birth_month)
        birth_layout.addWidget(self.birth_day)
        layout.addLayout(birth_layout, 2, 1)

        layout.addWidget(QLabel("死亡时间:"), 3, 0)
        self.death_year = QSpinBox()
        self.death_year.setRange(1, 99999)
        self.death_year.setValue(100)
        self.death_year.setPrefix("第")
        self.death_year.setSuffix("年")
        self.death_month = QSpinBox()
        self.death_month.setRange(1, 12)
        self.death_month.setValue(1)
        self.death_month.setSuffix("月")
        self.death_day = QSpinBox()
        self.death_day.setRange(1, 31)
        self.death_day.setValue(1)
        self.death_day.setSuffix("日")
        death_layout = QHBoxLayout()
        death_layout.addWidget(self.death_year)
        death_layout.addWidget(self.death_month)
        death_layout.addWidget(self.death_day)
        layout.addLayout(death_layout, 3, 1)

        layout.addWidget(QLabel("所属组织:"), 4, 0)
        self.org_combo = QComboBox()
        self.org_combo.addItem("无", None)
        for org_item in self.db.get_all_organizations():
            self.org_combo.addItem(org_item['name'], org_item['id'])
        if org:
            self.org_combo.setCurrentIndex(self.org_combo.findData(org['id']))
        layout.addWidget(self.org_combo, 4, 1)

        layout.addWidget(QLabel("描述:"), 5, 0)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("人物描述（可选）")
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit, 5, 1)

        layout.addWidget(QLabel("代表颜色:"), 6, 0)
        self.color_combo = QComboBox()
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        layout.addWidget(self.color_combo, 6, 1)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 7, 0, 1, 2)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def get_character_data(self):
        """获取人物数据"""
        name = self.name_edit.text().strip()
        alias = self.alias_edit.text().strip() or None
        description = self.desc_edit.toPlainText().strip() or None
        org_id = self.org_combo.currentData()
        color = self.color_combo.currentData()
        birth_time = f"第{self.birth_year.value()}年{self.birth_month.value()}月{self.birth_day.value()}日"
        death_time = f"第{self.death_year.value()}年{self.death_month.value()}月{self.death_day.value()}日" if self.death_year.value() > self.birth_year.value() else None
        
        return {
            'name': name,
            'alias': alias,
            'description': description,
            'organization_id': org_id,
            'color': color,
            'birth_time': birth_time,
            'death_time': death_time
        }


class AddEventDialog(QDialog):
    """添加事件对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        characters = self.db.get_all_characters()
        if not characters:
            QMessageBox.warning(parent, "提示", "请先创建人物")
            self.reject()
            return
        
        self.setWindowTitle("添加事件")
        self.resize(450, 350)
        
        layout = QGridLayout(self)
        
        layout.addWidget(QLabel("所属人物:"), 0, 0)
        self.ch_combo = QComboBox()
        for ch in characters:
            self.ch_combo.addItem(ch['name'], ch['id'])
        layout.addWidget(self.ch_combo, 0, 1)
        
        layout.addWidget(QLabel("事件标题:"), 1, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("请输入事件标题")
        layout.addWidget(self.title_edit, 1, 1)
        
        layout.addWidget(QLabel("时间节点:"), 2, 0)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1, 99999)
        self.year_spin.setValue(1)
        self.year_spin.setPrefix("第")
        self.year_spin.setSuffix("年")
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(1)
        self.month_spin.setSuffix("月")
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(1)
        self.day_spin.setSuffix("日")
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.year_spin)
        time_layout.addWidget(self.month_spin)
        time_layout.addWidget(self.day_spin)
        layout.addLayout(time_layout, 2, 1)
        
        layout.addWidget(QLabel("事件类型:"), 3, 0)
        self.type_combo = QComboBox()
        for name, value in EVENT_TYPE_OPTIONS:
            self.type_combo.addItem(name, value)
        layout.addWidget(self.type_combo, 3, 1)
        
        layout.addWidget(QLabel("事件颜色:"), 4, 0)
        self.color_combo = QComboBox()
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        layout.addWidget(self.color_combo, 4, 1)
        
        layout.addWidget(QLabel("事件内容:"), 5, 0)
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("事件详细内容（可选）")
        self.content_edit.setMaximumHeight(80)
        layout.addWidget(self.content_edit, 5, 1)
        
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 6, 0, 1, 2)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def get_event_data(self):
        """获取事件数据"""
        title = self.title_edit.text().strip()
        character_id = self.ch_combo.currentData()
        year = self.year_spin.value()
        month = self.month_spin.value()
        day = self.day_spin.value()
        timestamp = f"第{year}年{month}月{day}日"
        event_type = self.type_combo.currentData()
        color = self.color_combo.currentData()
        content = self.content_edit.toPlainText().strip() or None
        
        return {
            'title': title,
            'character_id': character_id,
            'timestamp': timestamp,
            'type': event_type,
            'color': color,
            'content': content
        }


class EditEventDialog(QDialog):
    """编辑事件对话框"""
    
    def __init__(self, db_manager, event_data, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.event_data = event_data
        
        self.setWindowTitle("编辑事件")
        self.resize(450, 380)

        layout = QGridLayout(self)

        layout.addWidget(QLabel("事件标题:"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setText(event_data.get('title', ''))
        layout.addWidget(self.title_edit, 0, 1)

        # 解析时间
        time_str = event_data.get('timestamp', '第1年1月1日')
        match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(time_str))
        if match:
            default_year, default_month, default_day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        else:
            default_year, default_month, default_day = 1, 1, 1

        layout.addWidget(QLabel("时间节点:"), 1, 0)
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1, 99999)
        self.year_spin.setValue(default_year)
        self.year_spin.setPrefix("第")
        self.year_spin.setSuffix("年")
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(default_month)
        self.month_spin.setSuffix("月")
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(default_day)
        self.day_spin.setSuffix("日")
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.year_spin)
        time_layout.addWidget(self.month_spin)
        time_layout.addWidget(self.day_spin)
        layout.addLayout(time_layout, 1, 1)

        layout.addWidget(QLabel("事件类型:"), 2, 0)
        self.type_combo = QComboBox()
        for name, value in EVENT_TYPE_OPTIONS:
            self.type_combo.addItem(name, value)
        self.type_combo.setCurrentIndex(self.type_combo.findData(event_data.get('type', 0)))
        layout.addWidget(self.type_combo, 2, 1)

        layout.addWidget(QLabel("事件颜色:"), 3, 0)
        self.color_combo = QComboBox()
        current_color = event_data.get('color', '#10B981')
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
            if hex_code.lower() == current_color.lower():
                self.color_combo.setCurrentIndex(self.color_combo.count() - 1)
        layout.addWidget(self.color_combo, 3, 1)

        layout.addWidget(QLabel("事件内容:"), 4, 0)
        self.content_edit = QTextEdit()
        self.content_edit.setText(event_data.get('content', ''))
        self.content_edit.setMaximumHeight(80)
        layout.addWidget(self.content_edit, 4, 1)

        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 5, 0, 1, 2)

        self.save_btn.clicked.connect(self.accept)
        self.delete_btn.clicked.connect(self._on_delete)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.delete_requested = False
    
    def _on_delete(self):
        self.delete_requested = True
        self.accept()
    
    def get_event_data(self):
        """获取事件数据"""
        title = self.title_edit.text().strip()
        timestamp = f"第{self.year_spin.value()}年{self.month_spin.value()}月{self.day_spin.value()}日"
        event_type = self.type_combo.currentData()
        color = self.color_combo.currentData()
        content = self.content_edit.toPlainText().strip() or None
        
        return {
            'title': title,
            'timestamp': timestamp,
            'type': event_type,
            'color': color,
            'content': content,
            'delete_requested': self.delete_requested
        }


class EditCharacterDialog(StyledDialog):
    """编辑人物对话框"""
    
    def __init__(self, db_manager, character_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.character_id = character_id
        
        ch = self.db.get_character(character_id)
        if not ch:
            self.reject()
            return
        
        self.ch = ch
        self.setWindowTitle("编辑人物")
        self.resize(400, 420)

        layout = QGridLayout(self)

        layout.addWidget(QLabel("人物名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setText(ch['name'])
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("别名:"), 1, 0)
        self.alias_edit = QLineEdit()
        self.alias_edit.setText(ch.get('alias', '') or '')
        layout.addWidget(self.alias_edit, 1, 1)

        # 出生时间
        birth_time = ch.get('birth_time', '第1年1月1日')
        match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(birth_time))
        if match:
            b_year, b_month, b_day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        else:
            b_year, b_month, b_day = 1, 1, 1

        layout.addWidget(QLabel("出生时间:"), 2, 0)
        self.birth_year = QSpinBox()
        self.birth_year.setRange(1, 99999)
        self.birth_year.setValue(b_year)
        self.birth_year.setPrefix("第")
        self.birth_year.setSuffix("年")
        self.birth_month = QSpinBox()
        self.birth_month.setRange(1, 12)
        self.birth_month.setValue(b_month)
        self.birth_month.setSuffix("月")
        self.birth_day = QSpinBox()
        self.birth_day.setRange(1, 31)
        self.birth_day.setValue(b_day)
        self.birth_day.setSuffix("日")
        birth_layout = QHBoxLayout()
        birth_layout.addWidget(self.birth_year)
        birth_layout.addWidget(self.birth_month)
        birth_layout.addWidget(self.birth_day)
        layout.addLayout(birth_layout, 2, 1)

        # 死亡时间
        death_time = ch.get('death_time')
        if death_time:
            match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(death_time))
            if match:
                d_year, d_month, d_day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            else:
                d_year, d_month, d_day = 100, 1, 1
        else:
            d_year, d_month, d_day = 100, 1, 1

        layout.addWidget(QLabel("死亡时间:"), 3, 0)
        self.death_year = QSpinBox()
        self.death_year.setRange(1, 99999)
        self.death_year.setValue(d_year)
        self.death_year.setPrefix("第")
        self.death_year.setSuffix("年")
        self.death_month = QSpinBox()
        self.death_month.setRange(1, 12)
        self.death_month.setValue(d_month)
        self.death_month.setSuffix("月")
        self.death_day = QSpinBox()
        self.death_day.setRange(1, 31)
        self.death_day.setValue(d_day)
        self.death_day.setSuffix("日")
        death_layout = QHBoxLayout()
        death_layout.addWidget(self.death_year)
        death_layout.addWidget(self.death_month)
        death_layout.addWidget(self.death_day)
        layout.addLayout(death_layout, 3, 1)

        layout.addWidget(QLabel("所属组织:"), 4, 0)
        self.org_combo = QComboBox()
        self.org_combo.addItem("无", None)
        for org in self.db.get_all_organizations():
            self.org_combo.addItem(org['name'], org['id'])
        if ch.get('organization_id'):
            self.org_combo.setCurrentIndex(self.org_combo.findData(ch['organization_id']))
        layout.addWidget(self.org_combo, 4, 1)

        layout.addWidget(QLabel("描述:"), 5, 0)
        self.desc_edit = QTextEdit()
        self.desc_edit.setText(ch.get('description', '') or '')
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit, 5, 1)

        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 6, 0, 1, 2)

        self.save_btn.clicked.connect(self.accept)
        self.delete_btn.clicked.connect(self._on_delete)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.delete_requested = False
    
    def _on_delete(self):
        self.delete_requested = True
        self.accept()
    
    def get_character_data(self):
        """获取人物数据"""
        name = self.name_edit.text().strip()
        birth_time = f"第{self.birth_year.value()}年{self.birth_month.value()}月{self.birth_day.value()}日"
        death_time = f"第{self.death_year.value()}年{self.death_month.value()}月{self.death_day.value()}日" if self.death_year.value() > self.birth_year.value() else None
        
        return {
            'name': name,
            'alias': self.alias_edit.text().strip() or None,
            'description': self.desc_edit.toPlainText().strip() or None,
            'organization_id': self.org_combo.currentData(),
            'birth_time': birth_time,
            'death_time': death_time,
            'delete_requested': self.delete_requested
        }


class AddOrganizationDialog(QDialog):
    """添加组织对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("添加组织")
        self.resize(400, 300)

        layout = QGridLayout(self)

        layout.addWidget(QLabel("组织名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入组织名称")
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("描述:"), 1, 0)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("组织描述（可选）")
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit, 1, 1)

        layout.addWidget(QLabel("组织颜色:"), 2, 0)
        self.color_combo = QComboBox()
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        layout.addWidget(self.color_combo, 2, 1)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 3, 0, 1, 2)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def get_organization_data(self):
        """获取组织数据"""
        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip() or None
        color = self.color_combo.currentData()
        
        return {
            'name': name,
            'description': description,
            'color': color
        }


class ManageOrganizationsDialog(StyledDialog):
    """管理组织对话框"""
    
    def __init__(self, db_manager, selected_org_id=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.selected_org_id = selected_org_id
        
        self.setWindowTitle("管理组织")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 组织列表
        self.org_list = QComboBox()
        layout.addWidget(QLabel("选择组织:"))
        layout.addWidget(self.org_list)

        # 详细信息区域
        info_group = QWidget()
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("名称:"), 0, 0)
        self.name_edit = QLineEdit()
        info_layout.addWidget(self.name_edit, 0, 1)

        info_layout.addWidget(QLabel("描述:"), 1, 0)
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        info_layout.addWidget(self.desc_edit, 1, 1)

        info_layout.addWidget(QLabel("颜色:"), 2, 0)
        self.color_combo = QComboBox()
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        info_layout.addWidget(self.color_combo, 2, 1)

        layout.addWidget(info_group)

        # 按钮区域
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存修改")
        self.del_btn = QPushButton("删除组织")
        self.close_btn = QPushButton("关闭")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.org_list.currentIndexChanged.connect(self._on_org_changed)
        self.save_btn.clicked.connect(self._save_org)
        self.del_btn.clicked.connect(self._delete_org)
        self.close_btn.clicked.connect(self.accept)

        self._refresh_org_list()
    
    def _on_org_changed(self):
        org_id = self.org_list.currentData()
        self._load_org_info(org_id)
    
    def _refresh_org_list(self):
        self.org_list.clear()
        orgs = self.db.get_all_organizations()
        if not orgs:
            self.org_list.addItem("暂无组织", None)
            self._load_org_info(None)
        else:
            for org in orgs:
                member_count = len(self.db.get_characters_by_organization(org['id']))
                self.org_list.addItem(f"{org['name']} ({member_count}人)", org['id'])
            
            # 如果有预选组织，选中它
            if self.selected_org_id:
                for i in range(self.org_list.count()):
                    if self.org_list.itemData(i) == self.selected_org_id:
                        self.org_list.setCurrentIndex(i)
                        break
            else:
                self._load_org_info(self.org_list.currentData())
    
    def _load_org_info(self, org_id):
        if not org_id:
            self.name_edit.clear()
            self.desc_edit.clear()
            self.color_combo.setCurrentIndex(0)
            return
        org = self.db.get_organization(org_id)
        if org:
            self.name_edit.setText(org.get('name', ''))
            self.desc_edit.setPlainText(org.get('description', '') or '')
            # 设置颜色
            color = org.get('color')
            if color:
                found = False
                for i in range(self.color_combo.count()):
                    if self.color_combo.itemData(i) == color:
                        self.color_combo.setCurrentIndex(i)
                        found = True
                        break
                if not found:
                    self.color_combo.setCurrentIndex(0)
            else:
                self.color_combo.setCurrentIndex(0)
    
    def _save_org(self):
        org_id = self.org_list.currentData()
        if not org_id:
            QMessageBox.warning(self, "提示", "请先选择一个组织")
            return
        
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "组织名称不能为空")
            return
        
        description = self.desc_edit.toPlainText().strip() or None
        color = self.color_combo.currentData()
        
        self.db.update_organization(
            org_id,
            name=name,
            description=description,
            color=color
        )
        
        # 刷新列表并保持选中
        current_id = org_id
        self._refresh_org_list()
        for i in range(self.org_list.count()):
            if self.org_list.itemData(i) == current_id:
                self.org_list.setCurrentIndex(i)
                break
        
        QMessageBox.information(self, "完成", "组织信息已保存")
    
    def _delete_org(self):
        org_id = self.org_list.currentData()
        if not org_id:
            return
        org = self.db.get_organization(org_id)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除组织「{org['name']}」吗？\n该操作不会删除组织内的人物，只会解除关联。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_organization(org_id)
            self._refresh_org_list()


class DeleteCharacterDialog(QDialog):
    """删除人物对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        characters = self.db.get_all_characters()
        if not characters:
            QMessageBox.information(parent, "提示", "当前没有可删除的人物")
            self.reject()
            return
        
        self.setWindowTitle("删除人物")
        self.resize(350, 150)

        layout = QGridLayout(self)

        layout.addWidget(QLabel("选择要删除的人物:"), 0, 0)
        self.ch_combo = QComboBox()
        for ch in characters:
            self.ch_combo.addItem(ch['name'], ch['id'])
        layout.addWidget(self.ch_combo, 0, 1)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 1, 0, 1, 2)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def get_selected_character(self):
        """获取选中的人物"""
        return {
            'id': self.ch_combo.currentData(),
            'name': self.ch_combo.currentText()
        }


class DeleteEventDialog(StyledDialog):
    """删除事件对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        characters = self.db.get_all_characters()
        if not characters:
            QMessageBox.information(parent, "提示", "当前没有可删除的事件")
            self.reject()
            return
        
        self.setWindowTitle("删除事件")
        self.resize(450, 220)

        layout = QGridLayout(self)

        layout.addWidget(QLabel("所属人物:"), 0, 0)
        self.ch_combo = QComboBox()
        for ch in characters:
            self.ch_combo.addItem(ch['name'], ch['id'])
        layout.addWidget(self.ch_combo, 0, 1)

        layout.addWidget(QLabel("要删除的事件:"), 1, 0)
        self.ev_combo = QComboBox()
        layout.addWidget(self.ev_combo, 1, 1)

        self.ch_combo.currentIndexChanged.connect(lambda: self._refresh_events(self.ch_combo.currentData()))
        self._refresh_events(self.ch_combo.currentData())

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 2, 0, 1, 2)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _refresh_events(self, ch_id):
        self.ev_combo.clear()
        events = self.db.get_events_by_character(ch_id)
        if not events:
            self.ev_combo.addItem("该人物暂无事件", None)
            return
        for ev in events:
            label = f"[时间 {ev['timestamp']}] {ev['title']}"
            self.ev_combo.addItem(label, ev['id'])
    
    def get_selected_event(self):
        """获取选中的事件"""
        event_id = self.ev_combo.currentData()
        if event_id is None:
            return None
        return {
            'id': event_id,
            'label': self.ev_combo.currentText()
        }


# ==================== 章节管理对话框 ====================
WRITING_STATUS_OPTIONS = [
    ("未写", 0, "#9CA3AF"),
    ("草稿中", 1, "#F59E0B"),
    ("已完成", 2, "#10B981"),
    ("已发布", 3, "#3B82F6"),
]

CHAPTER_STATUS_OPTIONS = [
    ("规划中", 0),
    ("写作中", 1),
    ("已完成", 2),
]


class AddChapterDialog(StyledDialog):
    """添加章节对话框"""
    
    def __init__(self, db_manager, parent=None, event_ids=None):
        super().__init__(parent)
        self.db = db_manager
        self.event_ids = event_ids or []
        
        self.setWindowTitle("创建章节")
        self.resize(500, 450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("章节编号:"), 0, 0)
        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 9999)
        self.number_spin.setValue(self.db.get_next_chapter_number())
        form_layout.addWidget(self.number_spin, 0, 1)
        
        form_layout.addWidget(QLabel("章节标题:"), 1, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("例如：初入江湖")
        form_layout.addWidget(self.title_edit, 1, 1)
        
        form_layout.addWidget(QLabel("章节摘要:"), 2, 0)
        self.summary_edit = QTextEdit()
        self.summary_edit.setPlaceholderText("简要描述本章内容...")
        self.summary_edit.setMaximumHeight(100)
        form_layout.addWidget(self.summary_edit, 2, 1)
        
        form_layout.addWidget(QLabel("章节状态:"), 3, 0)
        self.status_combo = QComboBox()
        for name, value in CHAPTER_STATUS_OPTIONS:
            self.status_combo.addItem(name, value)
        form_layout.addWidget(self.status_combo, 3, 1)
        
        form_layout.addWidget(QLabel("预计字数:"), 4, 0)
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(0, 1000000)
        self.word_count_spin.setValue(3000)
        self.word_count_spin.setSuffix(" 字")
        form_layout.addWidget(self.word_count_spin, 4, 1)
        
        layout.addLayout(form_layout)
        
        # 显示选中的事件
        if self.event_ids:
            layout.addWidget(QLabel("包含的事件："))
            self.event_list = QListWidget()
            self.event_list.setMaximumHeight(150)
            for ev_id in self.event_ids:
                # 获取事件信息
                events = []
                for ch in self.db.get_all_characters():
                    for ev in self.db.get_events_by_character(ch['id']):
                        if ev['id'] == ev_id:
                            events.append(ev)
                            break
                for ev in events:
                    type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
                    self.event_list.addItem(f"{type_icon} [{ev['timestamp']}] {ev['title']}")
            layout.addWidget(self.event_list)
        
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("创建")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def get_chapter_data(self):
        """获取章节数据"""
        return {
            'number': self.number_spin.value(),
            'title': self.title_edit.text().strip(),
            'summary': self.summary_edit.toPlainText().strip() or None,
            'status': self.status_combo.currentData(),
            'word_count': self.word_count_spin.value(),
            'event_ids': self.event_ids
        }


class EditChapterDialog(QDialog):
    """编辑章节对话框"""
    
    def __init__(self, db_manager, chapter_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.chapter_id = chapter_id
        
        chapter = self.db.get_chapter(chapter_id)
        if not chapter:
            self.reject()
            return
        
        self.chapter = chapter
        self.setWindowTitle(f"编辑章节 - 第{chapter['number']}章")
        self.resize(550, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("章节编号:"), 0, 0)
        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 9999)
        self.number_spin.setValue(chapter['number'])
        form_layout.addWidget(self.number_spin, 0, 1)
        
        form_layout.addWidget(QLabel("章节标题:"), 1, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setText(chapter['title'])
        form_layout.addWidget(self.title_edit, 1, 1)
        
        form_layout.addWidget(QLabel("章节摘要:"), 2, 0)
        self.summary_edit = QTextEdit()
        self.summary_edit.setText(chapter.get('summary', '') or '')
        self.summary_edit.setMaximumHeight(100)
        form_layout.addWidget(self.summary_edit, 2, 1)
        
        form_layout.addWidget(QLabel("章节状态:"), 3, 0)
        self.status_combo = QComboBox()
        for name, value in CHAPTER_STATUS_OPTIONS:
            self.status_combo.addItem(name, value)
        self.status_combo.setCurrentIndex(self.status_combo.findData(chapter.get('status', 0)))
        form_layout.addWidget(self.status_combo, 3, 1)
        
        form_layout.addWidget(QLabel("字数统计:"), 4, 0)
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(0, 1000000)
        self.word_count_spin.setValue(chapter.get('word_count', 0))
        self.word_count_spin.setSuffix(" 字")
        form_layout.addWidget(self.word_count_spin, 4, 1)
        
        layout.addLayout(form_layout)
        
        # 显示章节包含的事件
        layout.addWidget(QLabel("包含的事件："))
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.MultiSelection)
        events = self.db.get_events_by_chapter(chapter['number'])
        for ev in events:
            type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
            status_color = WRITING_STATUS_OPTIONS[ev.get('writing_status', 0)][2]
            item = QListWidgetItem(f"{type_icon} [{ev['timestamp']}] {ev.get('character_name', '')}: {ev['title']}")
            item.setForeground(Qt.GlobalColor(status_color))
            item.setData(Qt.UserRole, ev['id'])
            self.event_list.addItem(item)
        layout.addWidget(self.event_list)
        
        # 事件操作按钮
        event_btn_layout = QHBoxLayout()
        self.unbind_btn = QPushButton("解除选中事件绑定")
        self.bind_btn = QPushButton("添加事件...")
        event_btn_layout.addWidget(self.unbind_btn)
        event_btn_layout.addWidget(self.bind_btn)
        event_btn_layout.addStretch()
        layout.addLayout(event_btn_layout)
        
        self.unbind_btn.clicked.connect(self._unbind_selected)
        self.bind_btn.clicked.connect(self._bind_events)
        
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除章节")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.save_btn.clicked.connect(self.accept)
        self.delete_btn.clicked.connect(self._on_delete)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.delete_requested = False
    
    def _unbind_selected(self):
        """解除选中事件的绑定"""
        selected_items = self.event_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要解除绑定的事件")
            return
        
        for item in selected_items:
            ev_id = item.data(Qt.UserRole)
            self.db.unbind_event_from_chapter(ev_id)
            self.event_list.takeItem(self.event_list.row(item))
        
        QMessageBox.information(self, "完成", f"已解除 {len(selected_items)} 个事件的绑定")
    
    def _bind_events(self):
        """添加事件到章节"""
        dialog = SelectEventsDialog(self.db, self.chapter['number'], self)
        if dialog.exec() == SelectEventsDialog.Accepted:
            selected_ids = dialog.get_selected_event_ids()
            if not selected_ids:
                QMessageBox.information(self, "提示", "请选择要添加的事件")
                return
            
            # 绑定事件到章节
            for ev_id in selected_ids:
                self.db.bind_event_to_chapter(ev_id, self.chapter['number'], self.chapter['title'])
            
            # 更新事件列表显示
            events = self.db.get_events_by_chapter(self.chapter['number'])
            self.event_list.clear()
            for ev in events:
                type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
                status_color = WRITING_STATUS_OPTIONS[ev.get('writing_status', 0)][2]
                item = QListWidgetItem(f"{type_icon} [{ev['timestamp']}] {ev.get('character_name', '')}: {ev['title']}")
                item.setForeground(QColor(status_color))
                item.setData(Qt.UserRole, ev['id'])
                self.event_list.addItem(item)
            
            QMessageBox.information(self, "完成", f"已添加 {len(selected_ids)} 个事件到章节")
    
    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除章节「第{self.chapter['number']}章 {self.chapter['title']}」吗？\n该章节的事件绑定将被解除。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_requested = True
            self.accept()
    
    def get_chapter_data(self):
        """获取章节数据"""
        return {
            'number': self.number_spin.value(),
            'title': self.title_edit.text().strip(),
            'summary': self.summary_edit.toPlainText().strip() or None,
            'status': self.status_combo.currentData(),
            'word_count': self.word_count_spin.value(),
            'delete_requested': self.delete_requested
        }


class ManageChaptersDialog(QDialog):
    """管理章节对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("章节管理")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 章节列表
        layout.addWidget(QLabel("章节列表："))
        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.chapter_list)
        
        self._refresh_chapter_list()
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加章节")
        self.edit_btn = QPushButton("编辑选中")
        self.delete_btn = QPushButton("删除选中")
        self.close_btn = QPushButton("关闭")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.add_btn.clicked.connect(self._add_chapter)
        self.edit_btn.clicked.connect(self._edit_chapter)
        self.delete_btn.clicked.connect(self._delete_chapter)
        self.close_btn.clicked.connect(self.accept)
        
        self.chapter_list.itemDoubleClicked.connect(self._edit_chapter)
    
    def _refresh_chapter_list(self):
        self.chapter_list.clear()
        chapters = self.db.get_all_chapters()
        if not chapters:
            self.chapter_list.addItem("暂无章节，点击「添加章节」创建")
            return
        
        for ch in chapters:
            status_name = CHAPTER_STATUS_OPTIONS[ch.get('status', 0)][0]
            event_count = len(self.db.get_events_by_chapter(ch['number']))
            item_text = f"第{ch['number']}章 {ch['title']} [{status_name}] ({event_count}事件, {ch.get('word_count', 0)}字)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ch['id'])
            self.chapter_list.addItem(item)
    
    def _add_chapter(self):
        dialog = AddChapterDialog(self.db, self)
        if dialog.exec() == AddChapterDialog.Accepted:
            data = dialog.get_chapter_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入章节标题")
                return
            
            chapter_id = self.db.create_chapter(
                data['number'], data['title'], data['summary'],
                data['word_count'], data['status']
            )
            
            # 绑定事件
            for ev_id in data['event_ids']:
                self.db.bind_event_to_chapter(ev_id, data['number'], data['title'])
            
            self._refresh_chapter_list()
            QMessageBox.information(self, "完成", f"已创建第{data['number']}章")
    
    def _edit_chapter(self):
        current_item = self.chapter_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个章节")
            return
        
        chapter_id = current_item.data(Qt.UserRole)
        if chapter_id is None:
            return
        
        dialog = EditChapterDialog(self.db, chapter_id, self)
        if dialog.exec() == EditChapterDialog.Accepted:
            data = dialog.get_chapter_data()
            if data['delete_requested']:
                self.db.delete_chapter(chapter_id)
            else:
                self.db.update_chapter(
                    chapter_id,
                    number=data['number'],
                    title=data['title'],
                    summary=data['summary'],
                    word_count=data['word_count'],
                    status=data['status']
                )
            self._refresh_chapter_list()
    
    def _delete_chapter(self):
        current_item = self.chapter_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个章节")
            return
        
        chapter_id = current_item.data(Qt.UserRole)
        if chapter_id is None:
            return
        
        chapter = self.db.get_chapter(chapter_id)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除章节「第{chapter['number']}章 {chapter['title']}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_chapter(chapter_id)
            self._refresh_chapter_list()


class BindEventToChapterDialog(QDialog):
    """绑定事件到章节对话框"""
    
    def __init__(self, db_manager, event_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.event_id = event_id
        
        self.setWindowTitle("绑定事件到章节")
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("选择要绑定的章节："))
        self.chapter_combo = QComboBox()
        chapters = self.db.get_all_chapters()
        self.chapter_combo.addItem("不绑定（解除绑定）", None)
        for ch in chapters:
            self.chapter_combo.addItem(f"第{ch['number']}章 {ch['title']}", ch['number'])
        layout.addWidget(self.chapter_combo)
        
        layout.addWidget(QLabel("写作状态："))
        self.status_combo = QComboBox()
        for name, value, color in WRITING_STATUS_OPTIONS:
            self.status_combo.addItem(name, value)
        layout.addWidget(self.status_combo)
        
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def get_binding_data(self):
        """获取绑定数据"""
        return {
            'chapter_number': self.chapter_combo.currentData(),
            'writing_status': self.status_combo.currentData()
        }


class SelectEventsDialog(QDialog):
    """选择事件对话框"""
    
    def __init__(self, db_manager, exclude_chapter_number=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.exclude_chapter_number = exclude_chapter_number
        
        self.setWindowTitle("选择事件")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 搜索/筛选区域
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("人物:"))
        self.char_combo = QComboBox()
        self.char_combo.addItem("全部", None)
        for ch in self.db.get_all_characters():
            self.char_combo.addItem(ch['name'], ch['id'])
        filter_layout.addWidget(self.char_combo)
        
        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", None)
        for name, value, color in WRITING_STATUS_OPTIONS:
            self.status_combo.addItem(name, value)
        filter_layout.addWidget(self.status_combo)
        
        layout.addLayout(filter_layout)
        
        # 事件列表
        layout.addWidget(QLabel("选择要添加的事件（多选）："))
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.event_list)
        
        self._refresh_events()
        
        self.char_combo.currentIndexChanged.connect(self._refresh_events)
        self.status_combo.currentIndexChanged.connect(self._refresh_events)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _refresh_events(self):
        self.event_list.clear()
        
        char_id = self.char_combo.currentData()
        status = self.status_combo.currentData()
        
        # 获取所有事件
        all_events = []
        characters = self.db.get_all_characters()
        for ch in characters:
            if char_id is not None and ch['id'] != char_id:
                continue
            events = self.db.get_events_by_character(ch['id'])
            for ev in events:
                # 排除已绑定到当前章节的事件
                if self.exclude_chapter_number and ev.get('chapter_number') == self.exclude_chapter_number:
                    continue
                # 状态筛选
                if status is not None and ev.get('writing_status', 0) != status:
                    continue
                ev['character_name'] = ch['name']
                all_events.append(ev)
        
        if not all_events:
            self.event_list.addItem("没有可选择的事件")
            return
        
        for ev in all_events:
            type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
            ch_name = ev.get('character_name', '')
            ch_num = ev.get('chapter_number')
            ch_label = f" [Ch.{ch_num}]" if ch_num else ""
            item_text = f"{type_icon} [{ev['timestamp']}] {ch_name}{ch_label}: {ev['title']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ev['id'])
            self.event_list.addItem(item)
    
    def get_selected_event_ids(self):
        """获取选中的事件ID列表"""
        ids = []
        for item in self.event_list.selectedItems():
            ev_id = item.data(Qt.UserRole)
            if ev_id:
                ids.append(ev_id)
        return ids


# ==================== 组织关系管理对话框 ====================
LINE_STYLE_OPTIONS = [
    ("实线", "solid"),
    ("虚线", "dashed"),
    ("点线", "dotted"),
]


class AddRelationDialog(QDialog):
    """添加组织关系对话框"""
    
    def __init__(self, db_manager, org_id=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.org_id = org_id
        
        self.setWindowTitle("添加组织关系")
        self.resize(450, 350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("组织A:"), 0, 0)
        self.org1_combo = QComboBox()
        orgs = self.db.get_all_organizations()
        for org in orgs:
            self.org1_combo.addItem(org['name'], org['id'])
        if org_id:
            self.org1_combo.setCurrentIndex(self.org1_combo.findData(org_id))
        form_layout.addWidget(self.org1_combo, 0, 1)
        
        form_layout.addWidget(QLabel("组织B:"), 1, 0)
        self.org2_combo = QComboBox()
        for org in orgs:
            self.org2_combo.addItem(org['name'], org['id'])
        form_layout.addWidget(self.org2_combo, 1, 1)
        
        form_layout.addWidget(QLabel("关系类型:"), 2, 0)
        self.rel_type_combo = QComboBox()
        rel_types = self.db.get_all_relationship_types()
        for rt in rel_types:
            self.rel_type_combo.addItem(rt['name'], rt['id'])
        form_layout.addWidget(self.rel_type_combo, 2, 1)
        
        form_layout.addWidget(QLabel("关系强度:"), 3, 0)
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 10)
        self.strength_spin.setValue(5)
        form_layout.addWidget(self.strength_spin, 3, 1)
        
        form_layout.addWidget(QLabel("开始时间:"), 4, 0)
        self.start_time_edit = QLineEdit()
        self.start_time_edit.setPlaceholderText("例如：第1年1月1日")
        form_layout.addWidget(self.start_time_edit, 4, 1)
        
        form_layout.addWidget(QLabel("结束时间:"), 5, 0)
        self.end_time_edit = QLineEdit()
        self.end_time_edit.setPlaceholderText("例如：第10年12月31日（可选）")
        form_layout.addWidget(self.end_time_edit, 5, 1)
        
        layout.addLayout(form_layout)
        
        layout.addWidget(QLabel("关系描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("描述两个组织之间的关系...")
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit)
        
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("创建")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self._on_create)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _on_create(self):
        org1_id = self.org1_combo.currentData()
        org2_id = self.org2_combo.currentData()
        
        if org1_id == org2_id:
            QMessageBox.warning(self, "提示", "请选择两个不同的组织")
            return
        
        rel_type_id = self.rel_type_combo.currentData()
        strength = self.strength_spin.value()
        start_time = self.start_time_edit.text().strip() or None
        end_time = self.end_time_edit.text().strip() or None
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.create_org_relationship(
            org1_id, org2_id, rel_type_id, strength,
            start_time, end_time, description
        )
        
        QMessageBox.information(self, "完成", "组织关系已创建")
        self.accept()


class EditRelationDialog(StyledDialog):
    """编辑组织关系对话框"""
    
    def __init__(self, db_manager, rel_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.rel_id = rel_id
        
        rel = self.db.get_org_relationship(rel_id)
        if not rel:
            self.reject()
            return
        
        self.rel = rel
        self.setWindowTitle(f"编辑关系 - {rel.get('org1_name', '')} & {rel.get('org2_name', '')}")
        self.resize(450, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 显示当前关系信息
        info_label = QLabel(f"当前关系: {rel.get('org1_name', '')} ↔ {rel.get('org2_name', '')}")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(info_label)
        
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("关系类型:"), 0, 0)
        self.rel_type_combo = QComboBox()
        rel_types = self.db.get_all_relationship_types()
        for rt in rel_types:
            self.rel_type_combo.addItem(rt['name'], rt['id'])
        self.rel_type_combo.setCurrentIndex(self.rel_type_combo.findData(rel['relationship_type_id']))
        form_layout.addWidget(self.rel_type_combo, 0, 1)
        
        form_layout.addWidget(QLabel("关系强度:"), 1, 0)
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 10)
        self.strength_spin.setValue(rel.get('strength', 5))
        form_layout.addWidget(self.strength_spin, 1, 1)
        
        form_layout.addWidget(QLabel("开始时间:"), 2, 0)
        self.start_time_edit = QLineEdit()
        self.start_time_edit.setText(rel.get('start_time', '') or '')
        self.start_time_edit.setPlaceholderText("例如：第1年1月1日")
        form_layout.addWidget(self.start_time_edit, 2, 1)
        
        form_layout.addWidget(QLabel("结束时间:"), 3, 0)
        self.end_time_edit = QLineEdit()
        self.end_time_edit.setText(rel.get('end_time', '') or '')
        self.end_time_edit.setPlaceholderText("例如：第10年12月31日（可选）")
        form_layout.addWidget(self.end_time_edit, 3, 1)
        
        layout.addLayout(form_layout)
        
        layout.addWidget(QLabel("关系描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setText(rel.get('description', '') or '')
        self.desc_edit.setMaximumHeight(100)
        layout.addWidget(self.desc_edit)
        
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除关系")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.delete_requested = False
    
    def _on_save(self):
        rel_type_id = self.rel_type_combo.currentData()
        strength = self.strength_spin.value()
        start_time = self.start_time_edit.text().strip() or None
        end_time = self.end_time_edit.text().strip() or None
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.update_org_relationship(
            self.rel_id,
            relationship_type_id=rel_type_id,
            strength=strength,
            start_time=start_time,
            end_time=end_time,
            description=description
        )
        
        QMessageBox.information(self, "完成", "关系已更新")
        self.accept()
    
    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除「{self.rel.get('org1_name', '')}」与「{self.rel.get('org2_name', '')}」的关系吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_org_relationship(self.rel_id)
            self.delete_requested = True
            self.accept()


class ManageRelationTypesDialog(StyledDialog):
    """管理关系类型对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("关系类型管理")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("关系类型列表："))
        self.type_list = QListWidget()
        layout.addWidget(self.type_list)
        
        self._refresh_type_list()
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加类型")
        self.edit_btn = QPushButton("编辑选中")
        self.delete_btn = QPushButton("删除选中")
        self.close_btn = QPushButton("关闭")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.add_btn.clicked.connect(self._add_type)
        self.edit_btn.clicked.connect(self._edit_type)
        self.delete_btn.clicked.connect(self._delete_type)
        self.close_btn.clicked.connect(self.accept)
        
        self.type_list.itemDoubleClicked.connect(self._edit_type)
    
    def _refresh_type_list(self):
        self.type_list.clear()
        types = self.db.get_all_relationship_types()
        for t in types:
            item_text = f"{t['name']} - 颜色:{t['color']} 线型:{t['line_style']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, t['id'])
            self.type_list.addItem(item)
    
    def _add_type(self):
        dialog = AddRelationTypeDialog(self.db, self)
        if dialog.exec() == AddRelationTypeDialog.Accepted:
            self._refresh_type_list()
    
    def _edit_type(self):
        current_item = self.type_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个关系类型")
            return
        
        type_id = current_item.data(Qt.UserRole)
        dialog = EditRelationTypeDialog(self.db, type_id, self)
        if dialog.exec() == EditRelationTypeDialog.Accepted:
            self._refresh_type_list()
    
    def _delete_type(self):
        current_item = self.type_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个关系类型")
            return
        
        type_id = current_item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该关系类型吗？\n使用该类型的关系也会被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_relationship_type(type_id)
            self._refresh_type_list()


# ==================== 角色关系对话框 ====================

class AddCharRelationDialog(QDialog):
    """添加角色关系对话框"""
    
    def __init__(self, db_manager, default_char1_id=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("添加角色关系")
        self.resize(450, 350)
        
        layout = QVBoxLayout(self)
        
        # 角色1
        char1_layout = QHBoxLayout()
        char1_layout.addWidget(QLabel("角色A:"))
        self.char1_combo = QComboBox()
        char1_layout.addWidget(self.char1_combo)
        layout.addLayout(char1_layout)
        
        # 角色2
        char2_layout = QHBoxLayout()
        char2_layout.addWidget(QLabel("角色B:"))
        self.char2_combo = QComboBox()
        char2_layout.addWidget(self.char2_combo)
        layout.addLayout(char2_layout)
        
        # 关系类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("关系类型:"))
        self.type_combo = QComboBox()
        for rt in self.db.get_all_character_relationship_types():
            self.type_combo.addItem(rt['name'], rt['id'])
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # 关系强度
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("关系强度 (1-10):"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 10)
        self.strength_spin.setValue(5)
        strength_layout.addWidget(self.strength_spin)
        layout.addLayout(strength_layout)
        
        # 关系描述
        layout.addWidget(QLabel("关系描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit)
        
        # 关联事件
        event_layout = QHBoxLayout()
        event_layout.addWidget(QLabel("关联事件 (可选):"))
        self.event_combo = QComboBox()
        self.event_combo.addItem("无", None)
        events = self.db.get_all_events()
        for ev in events:
            label = f"[{ev.get('timestamp', '')}] {ev.get('title', '')}"
            self.event_combo.addItem(label, ev['id'])
        event_layout.addWidget(self.event_combo)
        layout.addLayout(event_layout)
        
        # 冲突提示
        self.conflict_label = QLabel("")
        self.conflict_label.setStyleSheet("color: #EF4444; font-size: 12px;")
        layout.addWidget(self.conflict_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
        
        # 加载角色列表
        self._load_characters(default_char1_id)
        
        # 检查冲突
        self.char1_combo.currentIndexChanged.connect(self._check_conflict)
        self.char2_combo.currentIndexChanged.connect(self._check_conflict)
    
    def _load_characters(self, default_char1_id):
        chars = self.db.get_all_characters()
        for ch in chars:
            self.char1_combo.addItem(ch['name'], ch['id'])
            self.char2_combo.addItem(ch['name'], ch['id'])
        
        if default_char1_id:
            idx = self.char1_combo.findData(default_char1_id)
            if idx >= 0:
                self.char1_combo.setCurrentIndex(idx)
    
    def _check_conflict(self):
        char1_id = self.char1_combo.currentData()
        char2_id = self.char2_combo.currentData()
        if char1_id and char2_id and char1_id != char2_id:
            conflict_count = self.db.check_relationship_conflict(char1_id, char2_id)
            if conflict_count > 0:
                self.conflict_label.setText(f"⚠️ 这两个角色已有 {conflict_count} 种其他关系，请确认是否要添加")
            else:
                self.conflict_label.setText("")
        else:
            self.conflict_label.setText("")
    
    def _save(self):
        char1_id = self.char1_combo.currentData()
        char2_id = self.char2_combo.currentData()
        
        if char1_id == char2_id:
            QMessageBox.warning(self, "错误", "不能选择与角色A相同的角色")
            return
        
        rel_type_id = self.type_combo.currentData()
        strength = self.strength_spin.value()
        description = self.desc_edit.toPlainText().strip() or None
        start_event_id = self.event_combo.currentData()
        
        self.db.create_character_relationship(
            char1_id, char2_id, rel_type_id, strength, description, start_event_id
        )
        self.accept()


class EditCharRelationDialog(StyledDialog):
    """编辑角色关系对话框"""
    
    def __init__(self, db_manager, rel_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.rel_id = rel_id
        self.rel = self.db.get_character_relationship(rel_id)
        
        self.setWindowTitle("编辑角色关系")
        self.resize(450, 350)
        
        layout = QVBoxLayout(self)
        
        # 显示当前关系双方
        rel_info = f"{self.rel['char1_name']} ↔ {self.rel['char2_name']}"
        layout.addWidget(QLabel(f"当前关系: {rel_info}"))
        
        # 关系类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("关系类型:"))
        self.type_combo = QComboBox()
        for rt in self.db.get_all_character_relationship_types():
            self.type_combo.addItem(rt['name'], rt['id'])
        idx = self.type_combo.findData(self.rel['relationship_type_id'])
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # 关系强度
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("关系强度 (1-10):"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 10)
        self.strength_spin.setValue(self.rel.get('strength', 5))
        strength_layout.addWidget(self.strength_spin)
        layout.addLayout(strength_layout)
        
        # 关系描述
        layout.addWidget(QLabel("关系描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlainText(self.rel.get('description', ''))
        layout.addWidget(self.desc_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.delete_btn.clicked.connect(self._delete)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _save(self):
        rel_type_id = self.type_combo.currentData()
        strength = self.strength_spin.value()
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.update_character_relationship(
            self.rel_id, relationship_type_id=rel_type_id,
            strength=strength, description=description
        )
        self.accept()
    
    def _delete(self):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该角色关系吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_character_relationship(self.rel_id)
            self.accept()


class ManageCharRelationTypesDialog(QDialog):
    """管理角色关系类型对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("角色关系类型管理")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("关系类型列表："))
        self.type_list = QListWidget()
        layout.addWidget(self.type_list)
        
        self._refresh_type_list()
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加类型")
        self.edit_btn = QPushButton("编辑选中")
        self.delete_btn = QPushButton("删除选中")
        self.close_btn = QPushButton("关闭")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.add_btn.clicked.connect(self._add_type)
        self.edit_btn.clicked.connect(self._edit_type)
        self.delete_btn.clicked.connect(self._delete_type)
        self.close_btn.clicked.connect(self.accept)
        
        self.type_list.itemDoubleClicked.connect(self._edit_type)
    
    def _refresh_type_list(self):
        self.type_list.clear()
        for t in self.db.get_all_character_relationship_types():
            direction = "双向" if t.get('bidirectional') else "单向"
            item_text = f"{t['name']} - 颜色:{t['color']} [{direction}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, t['id'])
            self.type_list.addItem(item)
    
    def _add_type(self):
        dialog = AddCharRelationTypeDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            self._refresh_type_list()
    
    def _edit_type(self):
        current_item = self.type_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个关系类型")
            return
        type_id = current_item.data(Qt.UserRole)
        dialog = EditCharRelationTypeDialog(self.db, type_id, self)
        if dialog.exec() == QDialog.Accepted:
            self._refresh_type_list()
    
    def _delete_type(self):
        current_item = self.type_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个关系类型")
            return
        type_id = current_item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该关系类型吗？\n使用该类型的关系也会被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_character_relationship_type(type_id)
            self._refresh_type_list()


class AddCharRelationTypeDialog(QDialog):
    """添加角色关系类型对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("添加角色关系类型")
        self.resize(350, 200)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("类型名称:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("颜色:"))
        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        layout.addWidget(self.color_combo)
        
        layout.addWidget(QLabel("方向性:"))
        self.bidirectional_check = QCheckBox("双向关系")
        self.bidirectional_check.setChecked(True)
        layout.addWidget(self.bidirectional_check)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入类型名称")
            return
        
        color = self.color_combo.currentData() or self.color_combo.currentText()
        bidirectional = 1 if self.bidirectional_check.isChecked() else 0
        
        self.db.create_character_relationship_type(name, color, bidirectional)
        self.accept()


class EditCharRelationTypeDialog(QDialog):
    """编辑角色关系类型对话框"""
    
    def __init__(self, db_manager, type_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.type_id = type_id
        self.type_data = self.db.get_character_relationship_type(type_id)
        
        self.setWindowTitle("编辑角色关系类型")
        self.resize(350, 200)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("类型名称:"))
        self.name_edit = QLineEdit(self.type_data['name'])
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("颜色:"))
        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        idx = self.color_combo.findData(self.type_data.get('color'))
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)
        else:
            self.color_combo.setCurrentText(self.type_data.get('color', '#9CA3AF'))
        layout.addWidget(self.color_combo)
        
        layout.addWidget(QLabel("方向性:"))
        self.bidirectional_check = QCheckBox("双向关系")
        self.bidirectional_check.setChecked(bool(self.type_data.get('bidirectional')))
        layout.addWidget(self.bidirectional_check)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入类型名称")
            return
        
        color = self.color_combo.currentData() or self.color_combo.currentText()
        bidirectional = 1 if self.bidirectional_check.isChecked() else 0
        
        self.db.update_character_relationship_type(self.type_id, name, color, bidirectional)
        self.accept()


# ==================== 情节线索对话框 ====================

class AddPlotThreadDialog(StyledDialog):
    """添加线索对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("新建线索")
        self.resize(400, 350)
        
        layout = QVBoxLayout(self)
        
        # 名称
        layout.addWidget(QLabel("线索名称:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        # 类别
        layout.addWidget(QLabel("类别:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("伏笔", 0)
        self.category_combo.addItem("主线线索", 1)
        self.category_combo.addItem("支线线索", 2)
        self.category_combo.addItem("悬念", 3)
        layout.addWidget(self.category_combo)
        
        # 状态
        layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("待埋设", 0)
        self.status_combo.addItem("已埋设", 1)
        self.status_combo.addItem("待回收", 2)
        self.status_combo.addItem("已回收", 3)
        self.status_combo.addItem("已废弃", 4)
        layout.addWidget(self.status_combo)
        
        # 重要性
        layout.addWidget(QLabel("重要性 (1-5):"))
        self.importance_spin = QSpinBox()
        self.importance_spin.setRange(1, 5)
        self.importance_spin.setValue(3)
        layout.addWidget(self.importance_spin)
        
        # 描述
        layout.addWidget(QLabel("描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        layout.addWidget(self.desc_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入线索名称")
            return
        
        category = self.category_combo.currentData()
        status = self.status_combo.currentData()
        importance = self.importance_spin.value()
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.create_plot_thread(name, description, category, status, importance)
        self.accept()


class EditPlotThreadDialog(QDialog):
    """编辑线索对话框"""
    
    def __init__(self, db_manager, thread_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.thread_id = thread_id
        self.thread = self.db.get_plot_thread(thread_id)
        
        self.setWindowTitle("编辑线索")
        self.resize(400, 350)
        
        layout = QVBoxLayout(self)
        
        # 名称
        layout.addWidget(QLabel("线索名称:"))
        self.name_edit = QLineEdit(self.thread['name'])
        layout.addWidget(self.name_edit)
        
        # 类别
        layout.addWidget(QLabel("类别:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("伏笔", 0)
        self.category_combo.addItem("主线线索", 1)
        self.category_combo.addItem("支线线索", 2)
        self.category_combo.addItem("悬念", 3)
        idx = self.category_combo.findData(self.thread.get('category', 0))
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        layout.addWidget(self.category_combo)
        
        # 状态
        layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("待埋设", 0)
        self.status_combo.addItem("已埋设", 1)
        self.status_combo.addItem("待回收", 2)
        self.status_combo.addItem("已回收", 3)
        self.status_combo.addItem("已废弃", 4)
        idx = self.status_combo.findData(self.thread.get('status', 0))
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        layout.addWidget(self.status_combo)
        
        # 重要性
        layout.addWidget(QLabel("重要性 (1-5):"))
        self.importance_spin = QSpinBox()
        self.importance_spin.setRange(1, 5)
        self.importance_spin.setValue(self.thread.get('importance', 3))
        layout.addWidget(self.importance_spin)
        
        # 描述
        layout.addWidget(QLabel("描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlainText(self.thread.get('description', ''))
        layout.addWidget(self.desc_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.delete_btn.clicked.connect(self._delete)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入线索名称")
            return
        
        category = self.category_combo.currentData()
        status = self.status_combo.currentData()
        importance = self.importance_spin.value()
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.update_plot_thread(self.thread_id, name, description, category, status, importance)
        self.accept()
    
    def _delete(self):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该线索吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_plot_thread(self.thread_id)
            self.accept()


class LinkEventToThreadDialog(StyledDialog):
    """关联事件到线索对话框"""
    
    def __init__(self, db_manager, thread_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.thread_id = thread_id
        
        self.setWindowTitle("关联事件")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 选择事件
        layout.addWidget(QLabel("选择要关联的事件:"))
        self.event_list = QListWidget()
        events = self.db.get_all_events()
        for ev in events:
            item = QListWidgetItem(f"[{ev.get('timestamp', '')}] {ev.get('title', '')}")
            item.setData(Qt.UserRole, ev['id'])
            self.event_list.addItem(item)
        layout.addWidget(self.event_list)
        
        # 关系类型
        layout.addWidget(QLabel("关联类型:"))
        self.relation_combo = QComboBox()
        self.relation_combo.addItem("埋设", 0)
        self.relation_combo.addItem("推进", 1)
        self.relation_combo.addItem("回收", 2)
        self.relation_combo.addItem("提及", 3)
        layout.addWidget(self.relation_combo)
        
        # 备注
        layout.addWidget(QLabel("备注:"))
        self.notes_edit = QLineEdit()
        layout.addWidget(self.notes_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.link_btn = QPushButton("关联")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.link_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.link_btn.clicked.connect(self._link)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _link(self):
        current_item = self.event_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "错误", "请选择一个事件")
            return
        
        event_id = current_item.data(Qt.UserRole)
        relation_type = self.relation_combo.currentData()
        notes = self.notes_edit.text().strip() or None
        
        self.db.link_event_to_thread(self.thread_id, event_id, relation_type, notes)
        self.accept()


class SelectThreadDialog(StyledDialog):
    """选择线索对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("选择线索")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("选择要关联的线索:"))
        self.thread_list = QListWidget()
        threads = self.db.get_all_plot_threads()
        for t in threads:
            status_name = {"待埋设": "灰", "已埋设": "蓝", "待回收": "橙", "已回收": "绿", "已废弃": "红"}
            status = {"待埋设": 0, "已埋设": 1, "待回收": 2, "已回收": 3, "已废弃": 4}
            s = status.get(t.get('status', 0), "待埋设")
            item = QListWidgetItem(f"{t['name']} [{s}]")
            item.setData(Qt.UserRole, t['id'])
            self.thread_list.addItem(item)
        layout.addWidget(self.thread_list)
        
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("选择")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.select_btn.clicked.connect(self._select)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _select(self):
        if self.thread_list.currentItem():
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "请选择一个线索")
    
    def get_selected_thread_id(self):
        current_item = self.thread_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None


# ==================== 灵感对话框 ====================

class EditInspirationDialog(QDialog):
    """编辑灵感对话框"""
    
    def __init__(self, db_manager, insp_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.insp_id = insp_id
        self.insp = self.db.get_inspiration(insp_id)
        
        self.setWindowTitle("编辑灵感")
        self.resize(450, 380)
        
        layout = QVBoxLayout(self)
        
        # 内容
        layout.addWidget(QLabel("灵感内容:"))
        self.content_edit = QTextEdit()
        self.content_edit.setMaximumHeight(120)
        self.content_edit.setPlainText(self.insp.get('content', ''))
        layout.addWidget(self.content_edit)
        
        # 分类
        layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        categories = {0: "人物灵感", 1: "情节灵感", 2: "对话灵感", 3: "设定灵感", 4: "其他"}
        for k, v in categories.items():
            self.category_combo.addItem(v, k)
        idx = self.category_combo.findData(self.insp.get('category', 0))
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        layout.addWidget(self.category_combo)
        
        # 来源
        layout.addWidget(QLabel("来源:"))
        sources = ["随手记录", "散步时想到", "梦中", "阅读时", "与人讨论", "其他"]
        self.source_combo = QComboBox()
        self.source_combo.addItems(sources)
        if self.insp.get('source') in sources:
            self.source_combo.setCurrentText(self.insp['source'])
        layout.addWidget(self.source_combo)
        
        # 标签
        layout.addWidget(QLabel("标签:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setText(self.insp.get('tags', ''))
        layout.addWidget(self.tags_edit)
        
        # 是否已使用
        self.is_used_check = QCheckBox("已使用")
        self.is_used_check.setChecked(bool(self.insp.get('is_used', 0)))
        layout.addWidget(self.is_used_check)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self._save)
        self.delete_btn.clicked.connect(self._delete)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _save(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "错误", "请输入灵感内容")
            return
        
        category = self.category_combo.currentData()
        source = self.source_combo.currentText()
        tags = self.tags_edit.text().strip() or None
        is_used = 1 if self.is_used_check.isChecked() else 0
        
        self.db.update_inspiration(self.insp_id, content=content, category=category,
                                   tags=tags, source=source, is_used=is_used)
        self.accept()
    
    def _delete(self):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该灵感吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_inspiration(self.insp_id)
            self.accept()


class AddRelationTypeDialog(QDialog):
    """添加关系类型对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("添加关系类型")
        self.resize(350, 200)
        
        layout = QVBoxLayout(self)
        
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("类型名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：合作、竞争...")
        form_layout.addWidget(self.name_edit, 0, 1)
        
        form_layout.addWidget(QLabel("颜色:"), 1, 0)
        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        for name, color in COLOR_OPTIONS:
            self.color_combo.addItem(name, color)
        form_layout.addWidget(self.color_combo, 1, 1)
        
        form_layout.addWidget(QLabel("线型:"), 2, 0)
        self.line_style_combo = QComboBox()
        for name, value in LINE_STYLE_OPTIONS:
            self.line_style_combo.addItem(name, value)
        form_layout.addWidget(self.line_style_combo, 2, 1)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("创建")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self._on_create)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _on_create(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入类型名称")
            return
        
        color = self.color_combo.currentData() or self.color_combo.currentText()
        line_style = self.line_style_combo.currentData()
        
        self.db.create_relationship_type(name, color, line_style)
        QMessageBox.information(self, "完成", "关系类型已创建")
        self.accept()


class EditRelationTypeDialog(QDialog):
    """编辑关系类型对话框"""
    
    def __init__(self, db_manager, type_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.type_id = type_id
        
        rel_type = self.db.get_relationship_type(type_id)
        if not rel_type:
            self.reject()
            return
        
        self.rel_type = rel_type
        self.setWindowTitle(f"编辑关系类型 - {rel_type['name']}")
        self.resize(350, 200)
        
        layout = QVBoxLayout(self)
        
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("类型名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setText(rel_type['name'])
        form_layout.addWidget(self.name_edit, 0, 1)
        
        form_layout.addWidget(QLabel("颜色:"), 1, 0)
        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        for name, color in COLOR_OPTIONS:
            self.color_combo.addItem(name, color)
        self.color_combo.setCurrentIndex(self.color_combo.findData(rel_type['color']))
        if self.color_combo.currentIndex() < 0:
            self.color_combo.setEditText(rel_type['color'])
        form_layout.addWidget(self.color_combo, 1, 1)
        
        form_layout.addWidget(QLabel("线型:"), 2, 0)
        self.line_style_combo = QComboBox()
        for name, value in LINE_STYLE_OPTIONS:
            self.line_style_combo.addItem(name, value)
        self.line_style_combo.setCurrentIndex(self.line_style_combo.findData(rel_type['line_style']))
        form_layout.addWidget(self.line_style_combo, 2, 1)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入类型名称")
            return
        
        color = self.color_combo.currentData() or self.color_combo.currentText()
        line_style = self.line_style_combo.currentData()
        
        self.db.update_relationship_type(self.type_id, name, color, line_style)
        QMessageBox.information(self, "完成", "关系类型已更新")
        self.accept()


# ==================== 事件组对话框 ====================
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


class AddEventGroupDialog(QDialog):
    """添加事件组对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        self.setWindowTitle("创建事件组")
        self.resize(450, 350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 名称
        layout.addWidget(QLabel("事件组名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：魂师大赛")
        layout.addWidget(self.name_edit)
        
        # 颜色
        layout.addWidget(QLabel("代表颜色:"))
        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        layout.addWidget(self.color_combo)
        
        # 状态
        layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        for name, value in EVENT_GROUP_STATUS_OPTIONS:
            self.status_combo.addItem(name, value)
        layout.addWidget(self.status_combo)
        
        # 描述
        layout.addWidget(QLabel("描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("描述这个事件组的核心内容...")
        self.desc_edit.setMaximumHeight(100)
        layout.addWidget(self.desc_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("创建")
        self.cancel_btn = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入事件组名称")
            return
        
        color = self.color_combo.currentData() or self.color_combo.currentText()
        status = self.status_combo.currentData()
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.create_event_group(name, description, color, status, 0)
        QMessageBox.information(self, "完成", "事件组已创建")
        self.accept()


class EditEventGroupDialog(QDialog):
    """编辑事件组对话框"""
    
    def __init__(self, db_manager, group_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.group_id = group_id
        
        self.group = self.db.get_event_group(group_id)
        if not self.group:
            self.reject()
            return
        
        self.setWindowTitle(f"编辑事件组 - {self.group['name']}")
        self.resize(500, 450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 基本信息
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("事件组名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.group['name'])
        form_layout.addWidget(self.name_edit, 0, 1)
        
        form_layout.addWidget(QLabel("代表颜色:"), 1, 0)
        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        for name, hex_code in COLOR_OPTIONS:
            self.color_combo.addItem(name, hex_code)
        idx = self.color_combo.findData(self.group.get('color'))
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)
        else:
            self.color_combo.setCurrentText(self.group.get('color', '#8B5CF6'))
        form_layout.addWidget(self.color_combo, 1, 1)
        
        form_layout.addWidget(QLabel("状态:"), 2, 0)
        self.status_combo = QComboBox()
        for name, value in EVENT_GROUP_STATUS_OPTIONS:
            self.status_combo.addItem(name, value)
        idx = self.status_combo.findData(self.group.get('status', 0))
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        form_layout.addWidget(self.status_combo, 2, 1)
        
        form_layout.addWidget(QLabel("进度:"), 3, 0)
        self.progress_spin = QSpinBox()
        self.progress_spin.setRange(0, 100)
        self.progress_spin.setValue(self.group.get('progress', 0))
        self.progress_spin.setSuffix("%")
        form_layout.addWidget(self.progress_spin, 3, 1)
        
        layout.addLayout(form_layout)
        
        # 描述
        layout.addWidget(QLabel("描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.group.get('description', ''))
        self.desc_edit.setMaximumHeight(100)
        layout.addWidget(self.desc_edit)
        
        # 关联事件列表
        layout.addWidget(QLabel("关联事件:"))
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self._refresh_event_list()
        layout.addWidget(self.event_list)
        
        # 事件操作按钮
        event_btn_layout = QHBoxLayout()
        self.add_event_btn = QPushButton("添加事件...")
        self.remove_event_btn = QPushButton("移除选中")
        event_btn_layout.addWidget(self.add_event_btn)
        event_btn_layout.addWidget(self.remove_event_btn)
        event_btn_layout.addStretch()
        layout.addLayout(event_btn_layout)
        
        # 确认按钮
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除事件组")
        self.cancel_btn = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.add_event_btn.clicked.connect(self._add_event)
        self.remove_event_btn.clicked.connect(self._remove_event)
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.delete_requested = False
    
    def _refresh_event_list(self):
        self.event_list.clear()
        group_data = self.db.get_event_group_with_events(self.group_id)
        if not group_data or not group_data.get('events'):
            self.event_list.addItem("暂无关联事件")
            return
        
        for ev in group_data['events']:
            relation_name = EVENT_GROUP_RELATION_TYPES[ev.get('relation_type', 0)][0]
            ch_name = ev.get('character_name', '')
            item_text = f"[{ev['timestamp']}] {relation_name}: {ch_name} - {ev['title']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ev['id'])
            item.setData(Qt.UserRole + 1, ev.get('relation_type', 0))
            self.event_list.addItem(item)
    
    def _add_event(self):
        dialog = SelectEventForGroupDialog(self.db, self.group_id, self)
        if dialog.exec() == SelectEventForGroupDialog.Accepted:
            selected_id = dialog.get_selected_event_id()
            relation_type = dialog.get_relation_type()
            if selected_id:
                self.db.add_event_to_group(self.group_id, selected_id, 0, relation_type)
                self.db.recalculate_group_progress(self.group_id)
                self._refresh_event_list()
    
    def _remove_event(self):
        selected_items = self.event_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要移除的事件")
            return
        
        for item in selected_items:
            ev_id = item.data(Qt.UserRole)
            if ev_id:
                self.db.remove_event_from_group(self.group_id, ev_id)
        
        self.db.recalculate_group_progress(self.group_id)
        self._refresh_event_list()
        QMessageBox.information(self, "完成", f"已移除 {len(selected_items)} 个事件")
    
    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入事件组名称")
            return
        
        color = self.color_combo.currentData() or self.color_combo.currentText()
        status = self.status_combo.currentData()
        progress = self.progress_spin.value()
        description = self.desc_edit.toPlainText().strip() or None
        
        self.db.update_event_group(self.group_id, name, description, color, status, progress)
        QMessageBox.information(self, "完成", "事件组已更新")
        self.accept()
    
    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除事件组「{self.group['name']}」吗？\n关联的事件不会被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_requested = True
            self.db.delete_event_group(self.group_id)
            self.accept()


class SelectEventForGroupDialog(StyledDialog):
    """为事件组选择事件的对话框"""
    
    def __init__(self, db_manager, group_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.group_id = group_id
        
        self.setWindowTitle("选择事件")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 事件列表
        layout.addWidget(QLabel("选择要添加的事件:"))
        self.event_list = QListWidget()
        self._load_events()
        layout.addWidget(self.event_list)
        
        # 关联类型
        layout.addWidget(QLabel("关联类型:"))
        self.relation_combo = QComboBox()
        for name, value in EVENT_GROUP_RELATION_TYPES:
            self.relation_combo.addItem(name, value)
        layout.addWidget(self.relation_combo)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("添加")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _load_events(self):
        self.event_list.clear()
        all_chars = self.db.get_all_characters()
        all_events = []
        
        for ch in all_chars:
            events = self.db.get_events_by_character(ch['id'])
            for ev in events:
                ev['character_name'] = ch['name']
                all_events.append(ev)
        
        all_events.sort(key=lambda x: parse_time_to_value(x['timestamp']))
        
        for ev in all_events:
            type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
            item_text = f"{type_icon} [{ev['timestamp']}] {ev['character_name']}: {ev['title']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ev['id'])
            self.event_list.addItem(item)
    
    def _on_ok(self):
        current_item = self.event_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择一个事件")
            return
        self.accept()
    
    def get_selected_event_id(self):
        current_item = self.event_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
    
    def get_relation_type(self):
        return self.relation_combo.currentData()