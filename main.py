"""主程序入口"""

import sys
import re
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTreeView, QSplitter, QStatusBar, QMenuBar, QLabel, QTextEdit,
    QAbstractItemView, QMessageBox, QMenu, QTabWidget, QDialog, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor

from database import DatabaseManager
from timeline_canvas import VirtualTimelineCanvas, EVENT_TYPE_BIRTH, EVENT_TYPE_DEATH
from constants import COLOR_OPTIONS, EVENT_TYPE_OPTIONS, EVENT_TYPE_NAMES, APP_STYLESHEET
from dialogs import (
    ExportOptionsDialog, AddCharacterDialog, AddEventDialog,
    EditEventDialog, EditCharacterDialog, AddOrganizationDialog,
    ManageOrganizationsDialog, DeleteCharacterDialog, DeleteEventDialog,
    AddChapterDialog, EditChapterDialog, ManageChaptersDialog, BindEventToChapterDialog,
    AddRelationDialog, ManageRelationTypesDialog,
    AddEventGroupDialog, EditEventGroupDialog
)
from tree_model import OrgTreeModel
from export_utils import export_to_json, export_to_markdown, export_to_csv
from action_log import ActionLogManager
from import_utils import import_from_json, export_all_to_json
from chapter_board import ChapterBoardPanel
from org_relation_graph import OrgRelationGraphPanel
from char_relation_graph import CharRelationGraphPanel
from plot_thread_panel import PlotThreadBoard
from semantic_search import SemanticSearcher
from inspiration_panel import InspirationPanel, GlobalSearchDialog
from event_group_panel import EventGroupPanel


class NovelTimelineMainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网文写作时间轴管理工具")
        self.resize(1280, 720)
        
        # 应用全局样式
        self.setStyleSheet(APP_STYLESHEET)
        
        # 初始化后端存储
        self.db = DatabaseManager()
        
        # 初始化语义搜索器
        self.semantic_searcher = SemanticSearcher(self.db)
        
        self.init_menu_bar()
        self.init_ui_layout()
        
        # 初始化操作日志管理器（最多保存10条）
        self.action_log = ActionLogManager(max_size=10)
        self.action_log.set_db(self.db)
        self.action_log.action_undone.connect(self._on_action_undone)
        
        # 绑定 Ctrl+Z 撤销快捷键
        from PySide6.QtGui import QKeySequence, QShortcut
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._undo_last_action)
        
        # 模拟加载一些种子测试数据
        self.load_mock_data()

    def init_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        edit_menu = menubar.addMenu("编辑")
        view_menu = menubar.addMenu("视图")
        chapter_menu = menubar.addMenu("章节")
        export_menu = menubar.addMenu("导出")
        
        # 文件菜单
        import_action = QAction("导入数据...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.show_import_data)
        file_menu.addAction(import_action)
        
        export_all_action = QAction("导出完整备份...", self)
        export_all_action.triggered.connect(self.show_export_all)
        file_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 搜索菜单
        search_menu = menubar.addMenu("搜索")
        
        global_search_action = QAction("全局搜索...", self)
        global_search_action.setShortcut("Ctrl+F")
        global_search_action.triggered.connect(self.show_global_search)
        search_menu.addAction(global_search_action)
        
        inspiration_search_action = QAction("搜索灵感...", self)
        inspiration_search_action.triggered.connect(self.show_inspiration_search)
        search_menu.addAction(inspiration_search_action)

        add_character_action = QAction("添加人物...", self)
        add_character_action.setShortcut("Ctrl+1")
        add_character_action.triggered.connect(self.show_add_character_dialog)
        edit_menu.addAction(add_character_action)

        add_event_action = QAction("添加事件...", self)
        add_event_action.setShortcut("Ctrl+2")
        add_event_action.triggered.connect(self.show_add_event_dialog)
        edit_menu.addAction(add_event_action)

        edit_menu.addSeparator()

        add_org_action = QAction("添加组织...", self)
        add_org_action.setShortcut("Ctrl+3")
        add_org_action.triggered.connect(self.show_add_organization_dialog)
        edit_menu.addAction(add_org_action)

        manage_org_action = QAction("管理组织...", self)
        manage_org_action.setShortcut("Ctrl+4")
        manage_org_action.triggered.connect(self.show_manage_organizations_dialog)
        edit_menu.addAction(manage_org_action)

        edit_menu.addSeparator()

        # 组织关系管理
        add_relation_action = QAction("添加组织关系...", self)
        add_relation_action.triggered.connect(self.show_add_relation_dialog)
        edit_menu.addAction(add_relation_action)

        manage_rel_types_action = QAction("管理关系类型...", self)
        manage_rel_types_action.triggered.connect(self.show_manage_relation_types_dialog)
        edit_menu.addAction(manage_rel_types_action)

        edit_menu.addSeparator()

        # 角色关系管理
        add_char_relation_action = QAction("添加角色关系...", self)
        add_char_relation_action.triggered.connect(self.show_add_char_relation_dialog)
        edit_menu.addAction(add_char_relation_action)

        manage_char_rel_types_action = QAction("管理角色关系类型...", self)
        manage_char_rel_types_action.triggered.connect(self.show_manage_char_relation_types_dialog)
        edit_menu.addAction(manage_char_rel_types_action)

        export_char_rel_action = QAction("导出人物关系卡...", self)
        export_char_rel_action.triggered.connect(self.show_export_char_relations_markdown)
        edit_menu.addAction(export_char_rel_action)

        edit_menu.addSeparator()

        del_character_action = QAction("删除人物...", self)
        del_character_action.triggered.connect(self.show_delete_character_dialog)
        edit_menu.addAction(del_character_action)

        del_event_action = QAction("删除事件...", self)
        del_event_action.triggered.connect(self.show_delete_event_dialog)
        edit_menu.addAction(del_event_action)

        # 章节菜单
        add_chapter_action = QAction("添加章节...", self)
        add_chapter_action.setShortcut("Ctrl+5")
        add_chapter_action.triggered.connect(self.show_add_chapter_dialog)
        chapter_menu.addAction(add_chapter_action)

        manage_chapter_action = QAction("管理章节...", self)
        manage_chapter_action.triggered.connect(self.show_manage_chapters_dialog)
        chapter_menu.addAction(manage_chapter_action)

        chapter_menu.addSeparator()

        show_chapter_board_action = QAction("显示章节看板", self, checkable=True)
        show_chapter_board_action.setChecked(True)
        show_chapter_board_action.triggered.connect(self.toggle_chapter_board)
        chapter_menu.addAction(show_chapter_board_action)
        self.show_chapter_board_action = show_chapter_board_action
        
        # 线索菜单
        plot_menu = menubar.addMenu("线索")
        
        add_thread_action = QAction("新建线索...", self)
        add_thread_action.setShortcut("Ctrl+6")
        add_thread_action.triggered.connect(self.show_add_thread_dialog)
        plot_menu.addAction(add_thread_action)
        
        manage_thread_action = QAction("管理线索...", self)
        manage_thread_action.triggered.connect(self.show_manage_threads_dialog)
        plot_menu.addAction(manage_thread_action)
        
        plot_menu.addSeparator()
        
        export_thread_action = QAction("导出伏笔清单...", self)
        export_thread_action.triggered.connect(self.export_thread_list)
        plot_menu.addAction(export_thread_action)
        
        # 灵感菜单
        insp_menu = menubar.addMenu("灵感")
        
        quick_add_action = QAction("快速记录...", self)
        quick_add_action.setShortcut("Ctrl+Shift+N")
        quick_add_action.triggered.connect(self.show_quick_inspiration)
        insp_menu.addAction(quick_add_action)
        
        manage_insp_action = QAction("管理灵感...", self)
        manage_insp_action.triggered.connect(self.show_inspiration_panel)
        insp_menu.addAction(manage_insp_action)
        
        # 事件组菜单
        group_menu = menubar.addMenu("事件组")
        
        add_group_action = QAction("新建事件组...", self)
        add_group_action.setShortcut("Ctrl+7")
        add_group_action.triggered.connect(self.show_add_event_group_dialog)
        group_menu.addAction(add_group_action)
        
        manage_group_action = QAction("管理事件组...", self)
        manage_group_action.triggered.connect(self.show_manage_event_groups_dialog)
        group_menu.addAction(manage_group_action)

        self.align_action = QAction("事件对齐", self, checkable=True)
        self.align_action.setChecked(True)
        self.align_action.triggered.connect(self.toggle_event_alignment)
        view_menu.addAction(self.align_action)

        view_menu.addSeparator()

        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("重置缩放", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)

        view_menu.addSeparator()

        zoom_menu = view_menu.addMenu("缩放级别")
        zoom_levels = [25, 50, 75, 100, 125, 150]
        for level in zoom_levels:
            zoom_action = QAction(f"{level}%", self, checkable=True)
            zoom_action.triggered.connect(lambda checked, l=level: self.set_zoom_level(l))
            zoom_menu.addAction(zoom_action)

        view_menu.addSeparator()

        clear_canvas_action = QAction("清空时间轴", self)
        clear_canvas_action.triggered.connect(self.clear_timeline)
        view_menu.addAction(clear_canvas_action)

        ai_export_action = QAction("AI API 格式导出...", self)
        ai_export_action.triggered.connect(self.export_ai_format)
        export_menu.addAction(ai_export_action)

        json_export_action = QAction("导出为 JSON...", self)
        json_export_action.triggered.connect(self.export_json)
        export_menu.addAction(json_export_action)

        markdown_export_action = QAction("导出为 Markdown...", self)
        markdown_export_action.triggered.connect(self.export_markdown)
        export_menu.addAction(markdown_export_action)

        csv_export_action = QAction("导出事件为 CSV...", self)
        csv_export_action.triggered.connect(self.export_csv)
        export_menu.addAction(csv_export_action)

    def init_ui_layout(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # 1. 左侧组织/人物树形列表
        self.org_tree = QTreeView()
        self.org_tree.setHeaderHidden(True)
        self.org_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.org_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.org_tree.setMinimumWidth(180)
        self.org_tree.setMaximumWidth(280)
        self.org_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        
        self.org_tree_model = OrgTreeModel(self.db)
        self.org_tree.setModel(self.org_tree_model)
        
        self.org_tree.selectionModel().selectionChanged.connect(self.on_tree_selection_changed)
        self.org_tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        self.org_tree.expandAll()
        
        splitter.addWidget(self.org_tree)
        
        # 2. 中间虚拟化时间轴主画布
        self.canvas = VirtualTimelineCanvas()
        self.canvas.node_selected.connect(self.on_canvas_node_selected)
        self.canvas.character_selected.connect(self.on_canvas_character_selected)
        self.canvas.node_edit_requested.connect(self.show_edit_event_dialog)
        self.canvas.character_edit_requested.connect(self.show_edit_character_dialog)
        splitter.addWidget(self.canvas)
        
        # 3. 右侧面板（TabWidget：详情 + 章节看板）
        self.right_panel = QTabWidget()
        self.right_panel.setMinimumWidth(300)
        self.right_panel.setMaximumWidth(500)
        
        # 详情面板
        self.detail_panel = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_panel)
        self.detail_layout.setContentsMargins(16, 16, 16, 16)
        self.detail_layout.setSpacing(12)
        
        self.detail_title = QLabel("选择人物查看详情")
        self.detail_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1F2937;")
        self.detail_layout.addWidget(self.detail_title)
        
        self.detail_info = QTextEdit()
        self.detail_info.setReadOnly(True)
        self.detail_info.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 8px;")
        self.detail_layout.addWidget(self.detail_info)
        
        self.detail_events_label = QLabel("事件列表")
        self.detail_events_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #4B5563;")
        self.detail_layout.addWidget(self.detail_events_label)
        
        self.detail_events = QTextEdit()
        self.detail_events.setReadOnly(True)
        self.detail_events.setMaximumHeight(200)
        self.detail_events.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 8px;")
        self.detail_layout.addWidget(self.detail_events)
        
        self.right_panel.addTab(self.detail_panel, "📝 详情")
        
        # 章节看板面板
        self.chapter_board = ChapterBoardPanel(self.db)
        self.chapter_board.chapter_selected.connect(self.on_chapter_selected)
        self.chapter_board.chapter_edit_requested.connect(self.show_edit_chapter_dialog)
        self.chapter_board.create_chapter_from_events.connect(self.create_chapter_from_events)
        self.right_panel.addTab(self.chapter_board, "📚 章节")
        
        # 势力关系图面板
        self.org_relation_graph = OrgRelationGraphPanel(self.db)
        self.org_relation_graph.org_selected.connect(self.on_org_selected_from_graph)
        self.right_panel.addTab(self.org_relation_graph, "🔗 势力")
        
        # 角色关系图面板
        self.char_relation_graph = CharRelationGraphPanel(self.db)
        self.char_relation_graph.char_selected.connect(self.on_char_selected_from_graph)
        self.right_panel.addTab(self.char_relation_graph, "👥 角色")
        
        # 线索看板面板
        self.plot_thread_board = PlotThreadBoard(self.db)
        self.plot_thread_board.thread_selected.connect(self.on_thread_selected)
        self.right_panel.addTab(self.plot_thread_board, "📖 线索")
        
        # 灵感管理面板
        self.inspiration_panel = InspirationPanel(self.db, self.semantic_searcher)
        self.inspiration_panel.convert_to_event.connect(self.create_event_from_inspiration)
        self.right_panel.addTab(self.inspiration_panel, "✨ 灵感")
        
        # 事件组管理面板
        self.event_group_panel = EventGroupPanel(self.db)
        self.event_group_panel.event_selected.connect(self.on_event_group_event_selected)
        self.event_group_panel.group_edit_requested.connect(self.show_edit_event_group_dialog)
        self.event_group_panel.event_edit_requested.connect(self.show_edit_event_dialog)
        self.right_panel.addTab(self.event_group_panel, "📦 事件组")
        
        splitter.addWidget(self.right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪 | 数据库连接正常")

    def load_mock_data(self):
        """载入演示数据（写入数据库但不加载到画布）"""
        # 创建演示组织
        existing_orgs = {org['name']: org['id'] for org in self.db.get_all_organizations()}
        if "天斗帝国" not in existing_orgs:
            org1_id = self.db.create_organization("天斗帝国", "斗罗大陆两大帝国之一", "#8B5CF6")
        else:
            org1_id = existing_orgs["天斗帝国"]

        # 创建演示人物（同一组织内颜色渐变）
        mock_data = [
            {
                "name": "林枫",
                "org_id": org1_id,
                "color": "#10B981",
                "birth_time": "第1年1月1日",
                "death_time": "第200年1月1日",
                "events": [
                    {"title": "出生", "timestamp": "第1年1月1日", "type": EVENT_TYPE_BIRTH, "color": "#10B981"},
                    {"title": "家族大比被废", "timestamp": "第10年6月15日", "type": 1, "color": "#EF4444"},
                    {"title": "遭遇退婚", "timestamp": "第15年3月20日", "type": 0, "color": "#10B981"},
                    {"title": "发现悬崖金手指", "timestamp": "第50年9月1日", "type": 1, "color": "#F59E0B"},
                    {"title": "死亡", "timestamp": "第200年1月1日", "type": EVENT_TYPE_DEATH, "color": "#EF4444"}
                ]
            },
            {
                "name": "纳兰嫣然",
                "org_id": org1_id,
                "color": "#8B5CF6",
                "birth_time": "第1年1月1日",
                "death_time": "第180年1月1日",
                "events": [
                    {"title": "出生", "timestamp": "第1年1月1日", "type": EVENT_TYPE_BIRTH, "color": "#8B5CF6"},
                    {"title": "突破大斗师", "timestamp": "第5年12月30日", "type": 0, "color": "#8B5CF6"},
                    {"title": "前往林家退婚", "timestamp": "第15年3月20日", "type": 1, "color": "#EF4444"},
                    {"title": "闭关生死门", "timestamp": "第80年5月1日", "type": 0, "color": "#10B981"},
                    {"title": "死亡", "timestamp": "第180年1月1日", "type": EVENT_TYPE_DEATH, "color": "#EF4444"}
                ]
            }
        ]

        existing_chars = {ch['name']: ch['id'] for ch in self.db.get_all_characters()}

        for ch in mock_data:
            if ch['name'] in existing_chars:
                ch_id = existing_chars[ch['name']]
            else:
                ch_id = self.db.create_character(ch['name'], organization_id=ch['org_id'], color=ch['color'], birth_time=ch['birth_time'], death_time=ch['death_time'])

            existing_events = {ev['title']: ev['id'] for ev in self.db.get_events_by_character(ch_id)}
            for ev in ch['events']:
                if ev['title'] not in existing_events:
                    self.db.create_event(
                        character_id=ch_id,
                        timestamp=ev['timestamp'],
                        title=ev['title'],
                        type=ev['type'],
                        color=ev['color'],
                        tags=None,
                        core_changes=None,
                        is_public=1
                    )

        # 初始化时画布保持空白，点击人物才加载

    def show_add_character_dialog(self):
        dialog = AddCharacterDialog(self.db, self)
        if dialog.exec() == AddCharacterDialog.Accepted:
            data = dialog.get_character_data()
            if not data['name']:
                QMessageBox.warning(self, "提示", "请输入人物名称")
                return
            
            # 如果选择了组织，计算人物颜色
            org_id = data['organization_id']
            color = data['color']
            if org_id and not color:
                org = self.db.get_organization(org_id)
                if org and org.get('color'):
                    org_color = QColor(org['color'])
                    h, s, l, a = org_color.hslHsl()
                    org_members = self.db.get_characters_by_organization(org_id)
                    index = len(org_members)
                    lightness = min(95, 50 + index * 10)
                    saturation = max(20, 70 - index * 10)
                    lighter_color = QColor.fromHsl(h, saturation, lightness, a)
                    color = lighter_color.name()
            
            ch_id = self.db.create_character(
                data['name'], data['alias'], data['description'],
                organization_id=org_id, color=color,
                birth_time=data['birth_time'], death_time=data['death_time']
            )
            self.action_log.record('add', 'character', ch_id)
            self.canvas.add_character(ch_id, data['name'], data['birth_time'], data['death_time'], color)
            self.org_tree_model.refresh()
            self.status_bar.showMessage(f"已创建人物：{data['name']} (出生:{data['birth_time']})")

    def show_add_event_dialog(self):
        dialog = AddEventDialog(self.db, self)
        if dialog.exec() == AddEventDialog.Accepted:
            data = dialog.get_event_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事件标题")
                return
            
            ev_id = self.db.create_event(
                character_id=data['character_id'],
                timestamp=data['timestamp'],
                title=data['title'],
                content=data['content'],
                type=data['type'],
                color=data['color'],
                tags=None,
                core_changes=None,
                is_public=1
            )
            self.action_log.record('add', 'event', ev_id)
            
            event_data = {
                'id': ev_id,
                'character_id': data['character_id'],
                'timestamp': data['timestamp'],
                'title': data['title'],
                'content': data['content'],
                'type': data['type'],
                'color': data['color'],
                'tags': None,
                'core_changes': None,
                'is_public': 1
            }
            
            self.canvas.add_event(data['character_id'], event_data)
            ch_name = self.db.get_character(data['character_id'])['name']
            self.status_bar.showMessage(f"已为 {ch_name} 创建事件：{data['title']}")

    def show_delete_character_dialog(self):
        dialog = DeleteCharacterDialog(self.db, self)
        if dialog.exec() == DeleteCharacterDialog.Accepted:
            data = dialog.get_selected_character()
            
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除人物「{data['name']}」吗？\n该人物的所有事件也会被一并删除。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                old_char = self.db.get_character_with_events(data['id'])
                self.db.delete_character(data['id'])
                self.action_log.record('delete', 'character', data['id'], old_data=old_char)
                self.canvas.remove_character(data['id'])
                self.org_tree_model.refresh()
                self.detail_title.setText("选择人物查看详情")
                self.detail_info.setText("")
                self.detail_events.setText("")
                self.status_bar.showMessage(f"已删除人物：{data['name']}")

    def show_delete_event_dialog(self):
        dialog = DeleteEventDialog(self.db, self)
        if dialog.exec() == DeleteEventDialog.Accepted:
            data = dialog.get_selected_event()
            if data is None:
                QMessageBox.information(self, "提示", "该人物没有可删除的事件")
                return

            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除事件「{data['label']}」吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                old_event = self.db.get_event(data['id'])
                self.db.delete_event(data['id'])
                self.action_log.record('delete', 'event', data['id'], old_data=old_event)
                self.canvas.remove_event(data['id'])
                self.status_bar.showMessage(f"已删除事件：{data['label']}")

    def toggle_event_alignment(self, checked: bool):
        """切换事件对齐功能"""
        self.canvas.set_align_events(checked)
        self.status_bar.showMessage(f"事件对齐{'已启用' if checked else '已禁用'}")

    def zoom_in(self):
        """放大时间轴"""
        current_scale = self.canvas.scale_factor
        new_scale = min(1.5, current_scale * 1.2)
        self.canvas.set_scale(new_scale)
        self.status_bar.showMessage(f"缩放: {int(new_scale * 100)}%")

    def zoom_out(self):
        """缩小时间轴"""
        current_scale = self.canvas.scale_factor
        new_scale = max(0.25, current_scale / 1.2)
        self.canvas.set_scale(new_scale)
        self.status_bar.showMessage(f"缩放: {int(new_scale * 100)}%")

    def reset_zoom(self):
        """重置缩放为100%"""
        self.canvas.set_scale(1.0)
        self.status_bar.showMessage("缩放: 100%")

    def clear_timeline(self):
        """清空时间轴视图"""
        self.canvas.scene.clear()
        self.canvas.all_nodes.clear()
        self.canvas.character_lines.clear()
        self.canvas.character_name_items.clear()
        self.canvas.organization_boxes.clear()
        self.canvas.next_y_offset = 100
        self.status_bar.showMessage("时间轴已清空")

    def set_zoom_level(self, level: int):
        """设置指定缩放级别"""
        scale = level / 100.0
        self.canvas.set_scale(scale)
        self.status_bar.showMessage(f"缩放: {level}%")

    def show_add_organization_dialog(self):
        dialog = AddOrganizationDialog(self.db, self)
        if dialog.exec() == AddOrganizationDialog.Accepted:
            data = dialog.get_organization_data()
            if not data['name']:
                QMessageBox.warning(self, "提示", "请输入组织名称")
                return
            
            org_id = self.db.create_organization(data['name'], data['description'], data['color'])
            self.action_log.record('add', 'organization', org_id)
            self.status_bar.showMessage(f"已创建组织：{data['name']}")
            self.org_tree_model.refresh()

    def show_manage_organizations_dialog(self):
        dialog = ManageOrganizationsDialog(self.db, parent=self)
        dialog.exec()
        self.org_tree_model.refresh()
        self.reload_canvas()

    def _load_character_timeline(self, character_id):
        """加载指定人物的时间轴到画布（追加模式）"""
        ch = self.db.get_character(character_id)
        if not ch:
            return
        
        ch_with_events = self.db.get_character_with_events(character_id)
        if ch_with_events:
            ch_with_events['birth_time'] = ch.get('birth_time')
            ch_with_events['death_time'] = ch.get('death_time')
            ch_with_events['org_id'] = ch.get('organization_id')
            org = self.db.get_organization(ch.get('organization_id'))
            ch_with_events['org_color'] = org['color'] if org else None
            
            if self.canvas.append_character_timeline(ch_with_events):
                self.status_bar.showMessage(f"已添加人物 {ch['name']} 的时间轴")
            else:
                self.status_bar.showMessage(f"人物 {ch['name']} 的时间轴已在视图中")

    def on_tree_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            self.detail_title.setText("选择人物查看详情")
            self.detail_info.setText("")
            self.detail_events.setText("")
            return

        index = indexes[0]
        item_data = index.data(Qt.UserRole)
        if not item_data:
            return

        item_type = item_data.get('type')
        item_id = item_data.get('id')

        if item_type == 'org':
            org_id = item_id
            if org_id == 0:
                self.detail_title.setText("🏛️ 无组织人物")
                self.detail_info.setText("未归属于任何组织的独立人物")
                chars = [ch for ch in self.db.get_all_characters() if ch.get('organization_id') is None]
                if chars:
                    events_text = "\n".join([f"👤 {ch['name']}" for ch in chars])
                else:
                    events_text = "暂无成员"
                self.detail_events.setText(events_text)
            else:
                org = self.db.get_organization(org_id)
                self.detail_title.setText(f"🏛️ {org['name']}")
                info_text = f"组织名称：{org['name']}\n"
                if org.get('description'):
                    info_text += f"描述：{org['description']}\n"
                info_text += f"颜色：{org.get('color', '#8B5CF6')}"
                self.detail_info.setText(info_text)
                
                chars = self.db.get_characters_by_organization(org_id)
                if chars:
                    events_text = "\n".join([f"👤 {ch['name']}" for ch in chars])
                else:
                    events_text = "暂无成员"
                self.detail_events.setText(events_text)
        elif item_type == 'char':
            ch = self.db.get_character(item_id)
            if ch:
                self.detail_title.setText(f"👤 {ch['name']}")
                info_text = f"姓名：{ch['name']}\n"
                if ch.get('alias'):
                    info_text += f"别名：{ch['alias']}\n"
                if ch.get('description'):
                    info_text += f"描述：{ch['description']}\n"
                if ch.get('birth_time'):
                    info_text += f"出生时间：{ch['birth_time']}\n"
                if ch.get('death_time'):
                    info_text += f"死亡时间：{ch['death_time']}\n"
                if ch.get('organization_id'):
                    org = self.db.get_organization(ch['organization_id'])
                    if org:
                        info_text += f"所属组织：{org['name']}"
                self.detail_info.setText(info_text)
                
                events = self.db.get_events_by_character(item_id)
                if events:
                    events_text = "\n".join([f"[{ev['timestamp']}] {ev['title']}" for ev in events])
                else:
                    events_text = "暂无事件"
                self.detail_events.setText(events_text)
                
                # 加载该人物的时间轴到画布
                self._load_character_timeline(item_id)
        elif item_type == 'event':
            # 点击事件时，选中画布上的对应节点
            ev = self.db.get_event(item_id)
            if ev:
                self.canvas.select_event(item_id)

    def on_tree_context_menu(self, pos):
        """左侧树形列表右键菜单"""
        index = self.org_tree.indexAt(pos)
        if not index.isValid():
            return

        item_data = index.data(Qt.UserRole)
        if not item_data:
            return

        menu = QMenu()
        item_type = item_data.get('type')
        item_id = item_data.get('id')

        if item_type == 'org':
            if item_id != 0:
                edit_org_action = menu.addAction("编辑组织")
                edit_org_action.triggered.connect(lambda: self._edit_organization(item_id))
                delete_org_action = menu.addAction("删除组织")
                delete_org_action.triggered.connect(lambda: self._delete_organization(item_id, item_data.get('name')))
            add_char_action = menu.addAction("添加人物")
            add_char_action.triggered.connect(lambda: self._add_character_to_org(item_id))
        elif item_type == 'char':
            edit_char_action = menu.addAction("编辑人物")
            edit_char_action.triggered.connect(lambda: self.show_edit_character_dialog(item_id, item_data.get('name')))
            delete_char_action = menu.addAction("删除人物")
            delete_char_action.triggered.connect(lambda: self._delete_character(item_id, item_data.get('name')))

        menu.exec_(self.org_tree.viewport().mapToGlobal(pos))

    def _edit_organization(self, org_id):
        """编辑组织（通过管理组织对话框定位到指定组织）"""
        dialog = ManageOrganizationsDialog(self.db, selected_org_id=org_id, parent=self)
        dialog.exec()
        self.org_tree_model.refresh()
        self.reload_canvas()

    def _delete_organization(self, org_id, org_name):
        """删除组织"""
        reply = QMessageBox.question(self, "确认删除", f"确定要删除组织「{org_name}」吗？\n该操作不会删除组织内的人物，只会解除关联。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            old_org = self.db.get_organization(org_id)
            self.db.delete_organization(org_id)
            self.action_log.record('delete', 'organization', org_id, old_data=old_org)
            self.org_tree_model.refresh()
            self.reload_canvas()
            self.status_bar.showMessage(f"已删除组织：{org_name}")

    def _add_character_to_org(self, org_id):
        """添加人物到指定组织"""
        org = self.db.get_organization(org_id) if org_id else None
        dialog = AddCharacterDialog(self.db, self, org)
        if dialog.exec() == AddCharacterDialog.Accepted:
            data = dialog.get_character_data()
            if not data['name']:
                QMessageBox.warning(self, "提示", "请输入人物名称")
                return
            
            org_id = data['organization_id']
            color = data['color']
            if org_id and not color:
                org_obj = self.db.get_organization(org_id)
                if org_obj and org_obj.get('color'):
                    org_color = QColor(org_obj['color'])
                    h, s, l, a = org_color.hslHsl()
                    org_members = self.db.get_characters_by_organization(org_id)
                    index = len(org_members)
                    lightness = min(95, 50 + index * 10)
                    saturation = max(20, 70 - index * 10)
                    lighter_color = QColor.fromHsl(h, saturation, lightness, a)
                    color = lighter_color.name()

            ch_id = self.db.create_character(
                data['name'], data['alias'], data['description'],
                organization_id=org_id, color=color,
                birth_time=data['birth_time'], death_time=data['death_time']
            )
            self.org_tree_model.refresh()
            self.reload_canvas()
            self.status_bar.showMessage(f"已创建人物：{data['name']} (出生:{data['birth_time']})")

    def _delete_character(self, character_id, character_name):
        """删除人物"""
        reply = QMessageBox.question(self, "确认删除", f"确定要删除人物「{character_name}」吗？\n该人物的所有事件也会被一并删除。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            old_char = self.db.get_character_with_events(character_id)
            self.db.delete_character(character_id)
            self.action_log.record('delete', 'character', character_id, old_data=old_char)
            self.org_tree_model.refresh()
            self.reload_canvas()
            self.status_bar.showMessage(f"已删除人物：{character_name}")

    def on_canvas_node_selected(self, event_data: dict):
        """点击画布上的事件节点时更新右侧详情面板"""
        self.detail_title.setText(f"📍 {event_data['title']}")
        
        info_text = f"事件标题：{event_data['title']}\n"
        info_text += f"时间节点：{event_data.get('timestamp', '')}\n"
        
        event_type = event_data.get('type', 0)
        info_text += f"事件类型：{EVENT_TYPE_NAMES.get(event_type, '普通')}\n"
        info_text += f"颜色：{event_data.get('color', '#10B981')}"
        
        self.detail_info.setText(info_text)
        
        content = event_data.get('content', '')
        if content:
            self.detail_events.setText(f"详细内容：\n{content}")
        else:
            self.detail_events.setText("暂无详细内容")
        
        # 更新关系图到该时间点
        timestamp = event_data.get('timestamp')
        if timestamp:
            self.org_relation_graph.set_time_from_timestamp(timestamp)

    def on_canvas_character_selected(self, character_id: int, character_name: str):
        """点击画布上的人物轴线时更新右侧详情面板"""
        ch = self.db.get_character(character_id)
        if ch:
            self.detail_title.setText(f"👤 {ch['name']}")
            info_text = f"姓名：{ch['name']}\n"
            if ch.get('alias'):
                info_text += f"别名：{ch['alias']}\n"
            if ch.get('description'):
                info_text += f"描述：{ch['description']}\n"
            if ch.get('birth_time'):
                info_text += f"出生时间：{ch['birth_time']}\n"
            if ch.get('death_time'):
                info_text += f"死亡时间：{ch['death_time']}\n"
            if ch.get('organization_id'):
                org = self.db.get_organization(ch['organization_id'])
                if org:
                    info_text += f"所属组织：{org['name']}"
            self.detail_info.setText(info_text)
            
            events = self.db.get_events_by_character(character_id)
            if events:
                events_text = "\n".join([f"[{ev['timestamp']}] {ev['title']}" for ev in events])
            else:
                events_text = "暂无事件"
            self.detail_events.setText(events_text)

    def show_edit_event_dialog(self, event_data: dict):
        """编辑事件对话框"""
        dialog = EditEventDialog(self.db, event_data, self)
        if dialog.exec() == EditEventDialog.Accepted:
            data = dialog.get_event_data()
            if data['delete_requested']:
                reply = QMessageBox.question(self, "确认删除", f"确定要删除事件「{event_data['title']}」吗？", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    old_event = self.db.get_event(event_data['id'])
                    self.db.delete_event(event_data['id'])
                    self.action_log.record('delete', 'event', event_data['id'], old_data=old_event)
                    self.status_bar.showMessage(f"已删除事件：{event_data['title']}")
                    self.reload_canvas()
            else:
                if not data['title']:
                    QMessageBox.warning(self, "提示", "请输入事件标题")
                    return
                old_event = self.db.get_event(event_data['id'])
                self.db.update_event(
                    event_data['id'],
                    title=data['title'],
                    timestamp=data['timestamp'],
                    type=data['type'],
                    color=data['color'],
                    content=data['content']
                )
                self.action_log.record('update', 'event', event_data['id'], old_data=old_event)
                self.status_bar.showMessage(f"已保存事件：{data['title']}")
                self.reload_canvas()

    def show_edit_character_dialog(self, character_id: int, character_name: str):
        """编辑人物对话框"""
        dialog = EditCharacterDialog(self.db, character_id, self)
        if dialog.exec() == EditCharacterDialog.Accepted:
            data = dialog.get_character_data()
            if data['delete_requested']:
                reply = QMessageBox.question(self, "确认删除", f"确定要删除人物「{self.db.get_character(character_id)['name']}」吗？\n该人物的所有事件也会被一并删除。", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    old_char = self.db.get_character_with_events(character_id)
                    self.db.delete_character(character_id)
                    self.action_log.record('delete', 'character', character_id, old_data=old_char)
                    self.status_bar.showMessage(f"已删除人物：{self.db.get_character(character_id)['name']}")
                    self.reload_canvas()
                    self.org_tree_model.refresh()
            else:
                if not data['name']:
                    QMessageBox.warning(self, "提示", "请输入人物名称")
                    return
                old_char = self.db.get_character(character_id)
                self.db.update_character(
                    character_id,
                    name=data['name'],
                    alias=data['alias'],
                    description=data['description'],
                    organization_id=data['organization_id'],
                    birth_time=data['birth_time'],
                    death_time=data['death_time']
                )
                self.action_log.record('update', 'character', character_id, old_data=old_char)
                self.status_bar.showMessage(f"已保存人物：{data['name']}")
                self.reload_canvas()
                self.org_tree_model.refresh()

    def reload_canvas(self):
        """重新加载画布数据（只重新加载当前画布上已有的人物）"""
        current_char_ids = list(self.canvas.character_lines.keys())
        if not current_char_ids:
            return

        canvas_data = []
        for char_id in current_char_ids:
            ch = self.db.get_character(char_id)
            if not ch:
                continue
            ch_with_events = self.db.get_character_with_events(char_id)
            if ch_with_events:
                org = self.db.get_organization(ch['organization_id']) if ch.get('organization_id') else None
                ch_with_events['org_id'] = ch.get('organization_id', 0)
                ch_with_events['org_color'] = org['color'] if org else None
                canvas_data.append(ch_with_events)

        if canvas_data:
            self.canvas.load_timeline_data(canvas_data)
        else:
            self.canvas.scene.clear()
            self.canvas.all_nodes.clear()
            self.canvas.character_lines.clear()
            self.canvas.character_name_items.clear()
        
        self.org_relation_graph.refresh_graph()
        self.char_relation_graph.refresh_graph()
        self.plot_thread_board.refresh()

    # ==================== 撤销功能 ====================
    def _undo_last_action(self):
        """撤销最近一条操作（Ctrl+Z）"""
        if not self.action_log.can_undo():
            self.status_bar.showMessage("没有可撤销的操作")
            return
        desc = self.action_log.get_undo_description()
        entity_type = self.action_log.undo()
        if entity_type:
            self.status_bar.showMessage(f"已{desc}")
            self._refresh_after_undo(entity_type)
        else:
            self.status_bar.showMessage("撤销失败")

    def _on_action_undone(self, entity_type):
        """撤销完成后的回调"""
        pass

    def _refresh_after_undo(self, entity_type):
        """根据撤销的实体类型刷新对应界面"""
        self.reload_canvas()
        self.org_tree_model.refresh()
        self.org_relation_graph.refresh_graph()
        self.char_relation_graph.refresh_graph()
        self.plot_thread_board.refresh()
        self.chapter_board.refresh()
        self.inspiration_panel.refresh()
        if hasattr(self, 'event_group_panel'):
            self.event_group_panel.refresh()

    # ==================== 导出功能 ====================
    def _show_export_options(self):
        """显示导出选项对话框"""
        dialog = ExportOptionsDialog(self.db, self)
        if dialog.exec() == ExportOptionsDialog.Accepted:
            return dialog.result
        return None

    def export_ai_format(self):
        """导出为 AI API 格式"""
        options = self._show_export_options()
        if not options:
            return
        
        file_path = export_to_json(self, self.db, options, "导出 AI API 格式")
        if file_path:
            self.status_bar.showMessage(f"已导出 AI API 格式到：{file_path}")

    def export_json(self):
        """导出为标准 JSON 格式"""
        options = self._show_export_options()
        if not options:
            return
        
        file_path = export_to_json(self, self.db, options, "导出 JSON")
        if file_path:
            self.status_bar.showMessage(f"已导出 JSON 到：{file_path}")

    def export_markdown(self):
        """导出为 Markdown 格式"""
        options = self._show_export_options()
        if not options:
            return
        
        file_path = export_to_markdown(self, self.db, options)
        if file_path:
            self.status_bar.showMessage(f"已导出 Markdown 到：{file_path}")

    def export_csv(self):
        """导出事件为 CSV 格式"""
        options = self._show_export_options()
        if not options:
            return
        
        file_path = export_to_csv(self, self.db, options)
        if file_path:
            self.status_bar.showMessage(f"已导出 CSV 到：{file_path}")

    # ==================== 章节功能 ====================
    def show_add_chapter_dialog(self):
        """显示添加章节对话框"""
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
            self.action_log.record('add', 'chapter', chapter_id)
            
            for ev_id in data['event_ids']:
                self.db.bind_event_to_chapter(ev_id, data['number'], data['title'])
            
            self.chapter_board.refresh()
            self.reload_canvas()
            self.status_bar.showMessage(f"已创建第{data['number']}章：{data['title']}")

    def show_manage_chapters_dialog(self):
        """显示管理章节对话框"""
        dialog = ManageChaptersDialog(self.db, self)
        dialog.exec()
        self.chapter_board.refresh()
        self.reload_canvas()

    def show_edit_chapter_dialog(self, chapter_id):
        """显示编辑章节对话框"""
        dialog = EditChapterDialog(self.db, chapter_id, self)
        if dialog.exec() == EditChapterDialog.Accepted:
            data = dialog.get_chapter_data()
            if data['delete_requested']:
                old_chapter = self.db.get_chapter(chapter_id)
                self.db.delete_chapter(chapter_id)
                self.action_log.record('delete', 'chapter', chapter_id, old_data=old_chapter)
                self.status_bar.showMessage("章节已删除")
            else:
                old_chapter = self.db.get_chapter(chapter_id)
                self.db.update_chapter(
                    chapter_id,
                    number=data['number'],
                    title=data['title'],
                    summary=data['summary'],
                    word_count=data['word_count'],
                    status=data['status']
                )
                self.action_log.record('update', 'chapter', chapter_id, old_data=old_chapter)
                self.status_bar.showMessage(f"已保存第{data['number']}章")
            self.chapter_board.refresh()
            self.reload_canvas()

    def toggle_chapter_board(self, visible):
        """切换章节看板显示"""
        if visible:
            self.right_panel.addTab(self.chapter_board, "📚 章节")
        else:
            index = self.right_panel.indexOf(self.chapter_board)
            if index >= 0:
                self.right_panel.removeTab(index)

    def on_chapter_selected(self, chapter_id):
        """选中章节时更新详情面板"""
        chapter = self.db.get_chapter(chapter_id)
        if chapter:
            self.detail_title.setText(f"📚 第{chapter['number']}章 {chapter['title']}")
            
            status_names = {0: "规划中", 1: "写作中", 2: "已完成"}
            info_text = f"章节编号：{chapter['number']}\n"
            info_text += f"标题：{chapter['title']}\n"
            info_text += f"状态：{status_names.get(chapter.get('status', 0), '规划中')}\n"
            info_text += f"字数：{chapter.get('word_count', 0)}\n"
            if chapter.get('summary'):
                info_text += f"摘要：{chapter['summary']}"
            self.detail_info.setText(info_text)
            
            events = self.db.get_events_by_chapter(chapter['number'])
            if events:
                events_text = "\n".join([f"[{ev['timestamp']}] {ev.get('character_name', '')}: {ev['title']}" for ev in events])
            else:
                events_text = "暂无事件"
            self.detail_events.setText(events_text)
            
            # 切换到详情面板
            self.right_panel.setCurrentIndex(0)

    def create_chapter_from_events(self, event_ids):
        """从选中事件创建章节"""
        dialog = AddChapterDialog(self.db, self, event_ids)
        if dialog.exec() == AddChapterDialog.Accepted:
            data = dialog.get_chapter_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入章节标题")
                return
            
            chapter_id = self.db.create_chapter(
                data['number'], data['title'], data['summary'],
                data['word_count'], data['status']
            )
            self.action_log.record('add', 'chapter', chapter_id)
            
            for ev_id in data['event_ids']:
                self.db.bind_event_to_chapter(ev_id, data['number'], data['title'])
            
            self.chapter_board.refresh()
            self.chapter_board.set_selected_events([])
            self.reload_canvas()
            self.status_bar.showMessage(f"已创建第{data['number']}章，包含 {len(event_ids)} 个事件")

    def bind_event_to_chapter(self, event_id):
        """绑定事件到章节"""
        dialog = BindEventToChapterDialog(self.db, event_id, self)
        if dialog.exec() == BindEventToChapterDialog.Accepted:
            data = dialog.get_binding_data()
            if data['chapter_number'] is None:
                self.db.unbind_event_from_chapter(event_id)
                self.status_bar.showMessage("已解除事件绑定")
            else:
                self.db.bind_event_to_chapter(event_id, data['chapter_number'])
                self.db.update_event_writing_status(event_id, data['writing_status'])
                self.status_bar.showMessage(f"已绑定事件到第{data['chapter_number']}章")
            self.chapter_board.refresh()
            self.reload_canvas()
    
    # ==================== 势力关系功能 ====================
    def show_add_relation_dialog(self):
        """显示添加关系对话框"""
        dialog = AddRelationDialog(self.db, None, self)
        if dialog.exec() == AddRelationDialog.Accepted:
            self.org_relation_graph.refresh_graph()
            self.status_bar.showMessage("组织关系已创建")
    
    def show_manage_relation_types_dialog(self):
        """显示管理关系类型对话框"""
        dialog = ManageRelationTypesDialog(self.db, self)
        dialog.exec()
        self.org_relation_graph.refresh_graph()
    
    def show_add_char_relation_dialog(self):
        """显示添加角色关系对话框"""
        from dialogs import AddCharRelationDialog
        dialog = AddCharRelationDialog(self.db, None, self)
        if dialog.exec() == QDialog.Accepted:
            self.char_relation_graph.refresh_graph()
            self.status_bar.showMessage("角色关系已创建")
    
    def show_manage_char_relation_types_dialog(self):
        """显示管理角色关系类型对话框"""
        from dialogs import ManageCharRelationTypesDialog
        dialog = ManageCharRelationTypesDialog(self.db, self)
        dialog.exec()
        self.char_relation_graph.refresh_graph()
    
    def show_export_char_relations_markdown(self):
        """导出人物关系卡"""
        self.char_relation_graph.export_relations_markdown()
    
    def on_org_selected_from_graph(self, org_id):
        """从关系图选中组织"""
        org = self.db.get_organization(org_id)
        if org:
            self.detail_title.setText(f"🏛️ {org['name']}")
            info_text = f"组织名称：{org['name']}\n"
            if org.get('description'):
                info_text += f"描述：{org['description']}\n"
            info_text += f"颜色：{org.get('color', '#8B5CF6')}\n"
            
            # 成员数量
            member_count = self.db.get_org_member_count(org_id)
            info_text += f"成员数量：{member_count}\n"
            
            # 关系摘要
            rel_summary = self.db.get_org_relationship_summary(org_id)
            if rel_summary:
                rel_text = ", ".join([f"{r['name']}: {r['count']}" for r in rel_summary])
                info_text += f"关系：{rel_text}"
            
            self.detail_info.setText(info_text)
            
            # 关键人物
            key_chars = self.db.get_org_key_characters(org_id, 5)
            if key_chars:
                chars_text = "关键人物：\n" + "\n".join([f"• {ch['name']} ({ch['event_count']}事件)" for ch in key_chars])
            else:
                chars_text = "暂无成员"
            self.detail_events.setText(chars_text)
            
            # 切换到详情面板
            self.right_panel.setCurrentIndex(0)
    
    def on_char_selected_from_graph(self, char_id):
        """从角色关系图选中人物"""
        char = self.db.get_character(char_id)
        if char:
            self.detail_title.setText(f"👤 {char['name']}")
            info_text = f"人物名称：{char['name']}\n"
            if char.get('alias'):
                info_text += f"别名：{char['alias']}\n"
            if char.get('description'):
                info_text += f"描述：{char['description']}\n"
            info_text += f"颜色：{char.get('color', '#8B5CF6')}\n"
            
            # 事件数量
            event_count = self.db.get_character_event_count(char_id)
            info_text += f"事件数量：{event_count}\n"
            
            # 关系摘要
            rels = self.db.get_character_relationships_by_character(char_id)
            if rels:
                rel_types = {}
                for r in rels:
                    name = r['relationship_name']
                    rel_types[name] = rel_types.get(name, 0) + 1
                rel_text = ", ".join([f"{k}: {v}" for k, v in rel_types.items()])
                info_text += f"关系：{rel_text}"
            
            self.detail_info.setText(info_text)
            
            # 小传内容
            biography = char.get('biography', '')
            if biography:
                self.detail_events.setText(f"小传：\n{biography}")
            else:
                self.detail_events.setText("暂无小传")
            
            # 切换到详情面板
            self.right_panel.setCurrentIndex(0)
    
    def on_thread_selected(self, thread_id):
        """从线索看板选中线索"""
        thread = self.db.get_plot_thread(thread_id)
        if thread:
            self.detail_title.setText(f"📖 {thread['name']}")
            
            from plot_thread_panel import THREAD_CATEGORY_NAMES, THREAD_STATUS_NAMES, THREAD_STATUS_COLORS
            
            category = THREAD_CATEGORY_NAMES.get(thread.get('category', 0), "伏笔")
            status = THREAD_STATUS_NAMES.get(thread.get('status', 0), "待埋设")
            status_color = THREAD_STATUS_COLORS.get(thread.get('status', 0), '#9CA3AF')
            
            info_text = f"线索名称：{thread['name']}\n"
            info_text += f"类别：{category}\n"
            info_text += f"状态：{status}\n"
            
            importance = thread.get('importance', 3)
            stars = "★" * importance + "☆" * (5 - importance)
            info_text += f"重要性：{stars}\n"
            
            if thread.get('description'):
                info_text += f"描述：{thread['description']}\n"
            
            event_count = self.db.get_thread_event_count(thread_id)
            info_text += f"关联事件数：{event_count}"
            
            self.detail_info.setText(info_text)
            
            # 关联事件列表
            events = self.db.get_thread_events(thread_id)
            if events:
                events_text = "关联事件：\n"
                from plot_thread_panel import RELATION_TYPE_NAMES
                for ev in events:
                    rel_type = RELATION_TYPE_NAMES.get(ev.get('relation_type', 0), "埋设")
                    events_text += f"• [{rel_type}] {ev.get('timestamp', '')} - {ev.get('title', '')}\n"
                self.detail_events.setText(events_text)
            else:
                self.detail_events.setText("暂无关联事件")
            
            # 切换到详情面板
            self.right_panel.setCurrentIndex(0)
    
    def show_add_thread_dialog(self):
        """显示新建线索对话框"""
        from dialogs import AddPlotThreadDialog
        dialog = AddPlotThreadDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            threads = self.db.get_all_plot_threads()
            if threads:
                thread_id = max(t['id'] for t in threads)
                self.action_log.record('add', 'plot_thread', thread_id)
            self.plot_thread_board.refresh()
            self.status_bar.showMessage("线索已创建")
    
    def show_manage_threads_dialog(self):
        """显示管理线索对话框"""
        # 切换到线索看板标签页
        self.right_panel.setCurrentWidget(self.plot_thread_board)
    
    def export_thread_list(self):
        """导出伏笔清单"""
        self.plot_thread_board._export_threads()
    
    def link_event_to_thread(self, event_id):
        """将事件关联到线索"""
        from dialogs import SelectThreadDialog
        dialog = SelectThreadDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            thread_id = dialog.get_selected_thread_id()
            if thread_id:
                self.db.link_event_to_thread(thread_id, event_id, relation_type=0)
                self.plot_thread_board.refresh()
                self.status_bar.showMessage("事件已关联到线索")
    
    def show_quick_inspiration(self):
        """显示快速灵感记录对话框"""
        from inspiration_panel import QuickInspirationDialog
        dialog = QuickInspirationDialog(self.db, self.semantic_searcher, self)
        dialog.move(self.geometry().center() - dialog.rect().center())
        if dialog.exec() == QDialog.Accepted:
            self.inspiration_panel.refresh()
            self.status_bar.showMessage("灵感已记录")
    
    def show_inspiration_panel(self):
        """切换到灵感面板"""
        self.right_panel.setCurrentWidget(self.inspiration_panel)
    
    def create_event_from_inspiration(self, insp_id):
        """从灵感创建事件"""
        insp = self.db.get_inspiration(insp_id)
        if not insp:
            return
        
        from dialogs import AddEventDialog
        dialog = AddEventDialog(self.db, self)
        dialog.title_edit.setText(insp.get('content', '')[:50])
        dialog.content_edit.setPlainText(insp.get('content', ''))
        
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_event_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事件标题")
                return
            
            ev_id = self.db.create_event(
                character_id=data['character_id'],
                timestamp=data['timestamp'],
                title=data['title'],
                content=data['content'],
                type=data['type'],
                color=data['color'],
                tags=None,
                core_changes=None,
                is_public=1
            )
            self.action_log.record('add', 'event', ev_id)
            
            # 标记灵感为已使用
            self.db.update_inspiration(insp_id, is_used=1)
            self.inspiration_panel.refresh()
            self.status_bar.showMessage("已从灵感创建事件")
    
    def on_search_event_found(self, event_id):
        """搜索到事件后的处理"""
        self.canvas.select_event(event_id)
        self.status_bar.showMessage(f"已定位到事件 ID: {event_id}")
    
    def show_global_search(self):
        """显示全局搜索对话框"""
        from inspiration_panel import GlobalSearchDialog
        dialog = GlobalSearchDialog(self.db, self.semantic_searcher, self)
        dialog.exec()
    
    def show_inspiration_search(self):
        """切换到灵感面板并聚焦搜索"""
        self.right_panel.setCurrentWidget(self.inspiration_panel)
        self.inspiration_panel.search_edit.setFocus()
    
    # ==================== 事件组相关方法 ====================
    def show_add_event_group_dialog(self):
        """显示添加事件组对话框"""
        dialog = AddEventGroupDialog(self.db, self)
        if dialog.exec() == AddEventGroupDialog.Accepted:
            groups = self.db.get_all_event_groups()
            if groups:
                group_id = max(g['id'] for g in groups)
                self.action_log.record('add', 'event_group', group_id)
            self.event_group_panel.refresh()
            self.status_bar.showMessage("事件组已创建")
    
    def show_manage_event_groups_dialog(self):
        """显示管理事件组对话框"""
        groups = self.db.get_all_event_groups()
        if not groups:
            QMessageBox.information(self, "提示", "暂无事件组，点击「新建事件组」创建")
            return
        
        group_ids = [g['id'] for g in groups]
        group_names = [g['name'] for g in groups]
        
        from PySide6.QtWidgets import QInputDialog
        selected_name, ok = QInputDialog.getItem(self, "管理事件组", "选择要编辑的事件组:", group_names, 0, False)
        if ok and selected_name:
            idx = group_names.index(selected_name)
            self.show_edit_event_group_dialog(group_ids[idx])
    
    def show_edit_event_group_dialog(self, group_id):
        """显示编辑事件组对话框"""
        if group_id == 0:
            dialog = AddEventGroupDialog(self.db, self)
        else:
            dialog = EditEventGroupDialog(self.db, group_id, self)
            old_group = self.db.get_event_group(group_id)
        
        if dialog.exec() == (AddEventGroupDialog.Accepted if group_id == 0 else EditEventGroupDialog.Accepted):
            if group_id == 0:
                groups = self.db.get_all_event_groups()
                if groups:
                    group_id = max(g['id'] for g in groups)
                    self.action_log.record('add', 'event_group', group_id)
            else:
                if dialog.delete_requested:
                    self.action_log.record('delete', 'event_group', group_id, old_data=old_group)
                else:
                    self.action_log.record('update', 'event_group', group_id, old_data=old_group)
            self.event_group_panel.refresh()
            self.status_bar.showMessage("事件组已更新")
    
    def on_event_group_event_selected(self, event_id):
        """事件组中事件被选中时处理"""
        self.canvas.select_event(event_id)
        event = self.db.get_event(event_id)
        if event:
            self.status_bar.showMessage(f"已定位到事件: {event['title']}")
    
    # ==================== 导入导出方法 ====================
    def refresh_all_panels(self):
        """刷新所有面板"""
        # 刷新组织树
        self.org_tree_model.refresh()
        # 刷新章节看板
        if hasattr(self, 'chapter_board'):
            self.chapter_board.refresh()
        # 刷新线索板
        if hasattr(self, 'plot_thread_board'):
            self.plot_thread_board.refresh()
        # 刷新灵感面板
        if hasattr(self, 'inspiration_panel'):
            self.inspiration_panel.refresh()
        # 刷新事件组面板
        if hasattr(self, 'event_group_panel'):
            self.event_group_panel.refresh()
    
    def show_import_data(self):
        """导入数据"""
        result = import_from_json(self, self.db)
        if result:
            self.reload_canvas()
            self.refresh_all_panels()
            self.status_bar.showMessage("数据导入成功，时间轴已刷新")
    
    def show_export_all(self):
        """导出完整数据备份"""
        export_all_to_json(self, self.db)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 启用暗黑/明亮自适应样式（可加自定义 QSS）
    app.setStyle('Fusion') 
    
    window = NovelTimelineMainWindow()
    window.show()
    sys.exit(app.exec())