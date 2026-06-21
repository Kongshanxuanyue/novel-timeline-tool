from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QStyleOptionGraphicsItem
from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QWheelEvent, QFont, QFontMetrics
import re

# 事件类型常量
EVENT_TYPE_NORMAL = 0
EVENT_TYPE_SPECIAL = 1
EVENT_TYPE_BIRTH = 2
EVENT_TYPE_DEATH = 3


def parse_time_to_value(time_str):
    """将年月日格式字符串转换为数值用于时间轴定位"""
    if not time_str:
        return 0
    # 匹配格式: 第N年M月D日 或 N年M月D日
    match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(time_str))
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return year * 10000 + month * 100 + day
    # 如果是数字格式，尝试直接转换
    try:
        return float(time_str) * 10000
    except:
        return 0


def format_time_label(time_str):
    """格式化时间标签显示"""
    if not time_str:
        return ""
    match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(time_str))
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3)
        return f"第{year}年{month}月{day}日"
    return str(time_str)


class EventNodeItem(QGraphicsItem):
    """时间信息在上，事件标题在下，支持章节标签和写作状态"""
    
    # 写作状态颜色
    WRITING_STATUS_COLORS = {
        0: "#9CA3AF",  # 未写 - 灰色
        1: "#F59E0B",  # 草稿中 - 黄色
        2: "#10B981",  # 已完成 - 绿色
        3: "#3B82F6",  # 已发布 - 蓝色
    }
    
    def __init__(self, event_data, y_pos):
        super().__init__()
        self.data = event_data
        self.y_pos = y_pos

        timestamp = event_data['timestamp']
        if 'base_x' in event_data:
            self.x_pos = event_data['base_x']
        elif isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', timestamp):
            self.x_pos = parse_time_to_value(timestamp) * 0.0025
        else:
            self.x_pos = float(timestamp) * 25.0
        self.setPos(self.x_pos, self.y_pos)

        self.event_type = event_data.get('type', 0)
        self.is_special = (self.event_type == EVENT_TYPE_SPECIAL)
        self.is_birth = (self.event_type == EVENT_TYPE_BIRTH)
        self.is_death = (self.event_type == EVENT_TYPE_DEATH)
        self.color = QColor(event_data.get('color', '#10B981'))
        self.title_text = event_data['title']
        self.timestamp_text = format_time_label(timestamp)
        
        # 章节相关
        self.chapter_number = event_data.get('chapter_number')
        self.chapter_title = event_data.get('chapter_title')
        self.writing_status = event_data.get('writing_status', 0)
        
        # 状态边框颜色
        self.status_color = QColor(self.WRITING_STATUS_COLORS.get(self.writing_status, "#9CA3AF"))

        self.font = QFont("Microsoft YaHei", 10)
        self.small_font = QFont("Microsoft YaHei", 8)
        self.chapter_font = QFont("Microsoft YaHei", 7)

        fm = QFontMetrics(self.font)
        self.title_width = fm.horizontalHeader() if hasattr(fm, 'horizontalHeader') else fm.boundingRect(self.title_text).width()
        self.title_height = fm.height()

        fm_small = QFontMetrics(self.small_font)
        self.timestamp_width = fm_small.horizontalHeader() if hasattr(fm_small, 'horizontalHeader') else fm_small.boundingRect(self.timestamp_text).width()
        self.timestamp_height = fm_small.height()
        
        # 章节标签宽度
        if self.chapter_number:
            self.chapter_label = f"Ch.{self.chapter_number}"
            fm_ch = QFontMetrics(self.chapter_font)
            self.chapter_width = fm_ch.boundingRect(self.chapter_label).width()
        else:
            self.chapter_label = ""
            self.chapter_width = 0

        self.max_text_width = max(self.title_width, self.timestamp_width, self.chapter_width + 10)

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def boundingRect(self):
        half_w = max(15, self.max_text_width / 2 + 6)
        total_height = self.timestamp_height + 4 + self.title_height + 8
        if self.chapter_number:
            total_height += 12  # 章节标签高度
        return QRectF(-half_w, -self.timestamp_height - 8 - (12 if self.chapter_number else 0), half_w * 2, total_height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        half_w = max(15, self.max_text_width / 2 + 6)
        
        # 计算起始Y位置（考虑章节标签）
        start_y_offset = 12 if self.chapter_number else 0

        # 1. 绘制选中状态或写作状态边框
        if self.isSelected():
            painter.setPen(QPen(QColor("#2563EB"), 2, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(37, 99, 235, 15)))
        elif self.writing_status > 0:
            # 写作状态边框
            painter.setPen(QPen(self.status_color, 1.5, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)
        
        total_height = self.timestamp_height + 4 + self.title_height + 8 + start_y_offset
        if self.isSelected() or self.writing_status > 0:
            painter.drawRoundedRect(-half_w, -self.timestamp_height - 8 - start_y_offset, half_w * 2, total_height, 6, 6)

        # 2. 绘制章节标签（左上角）
        if self.chapter_number:
            painter.setFont(self.chapter_font)
            painter.setPen(QPen(self.status_color))
            painter.drawText(-half_w + 4, -self.timestamp_height - start_y_offset, self.chapter_label)

        # 3. 绘制核心节点（留在轴线上）
        painter.setBrush(QBrush(self.color))
        if self.is_birth:
            points = [QPointF(0, -10), QPointF(8, 2), QPointF(-8, 2)]
            painter.drawPolygon(points)
        elif self.is_death:
            points = [QPointF(0, 10), QPointF(8, -2), QPointF(-8, -2)]
            painter.drawPolygon(points)
        elif self.is_special:
            points = [QPointF(0, -8), QPointF(8, 0), QPointF(0, 8), QPointF(-8, 0)]
            painter.drawPolygon(points)
        else:
            painter.drawEllipse(-6, -6, 12, 12)

        # 4. 绘制时间信息（上方）
        painter.setFont(self.small_font)
        painter.setPen(QPen(QColor("#6B7280")))
        time_x = -(self.timestamp_width / 2)
        time_y = -8
        painter.drawText(time_x, time_y, self.timestamp_text)

        # 4. 绘制事件标题（下方）
        painter.setFont(self.font)
        if self.isSelected():
            painter.setPen(QPen(QColor("#1E40AF")))
        else:
            painter.setPen(QPen(QColor("#374151")))
        title_x = -(self.title_width / 2)
        title_y = 12 + self.title_height / 2
        painter.drawText(title_x, title_y, self.title_text)

class VirtualTimelineCanvas(QGraphicsView):
    node_selected = Signal(dict)
    character_selected = Signal(int, str)  # character_id, character_name
    node_edit_requested = Signal(dict)  # 右键编辑事件
    character_edit_requested = Signal(int, str)  # 右键编辑人物

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)

        self.scale_factor = 1.0
        self.all_nodes = []
        self.character_lines = {}
        self.character_name_items = {}
        self.organization_boxes = {}
        self.chapter_dividers = {}
        self.next_y_offset = 100

        # 时间轴左侧留白（给人物名字）
        self.LINE_START_X = 150

        # 对齐相关
        self.align_events = True  # 默认启用对齐
        self.TIMESTAMP_SCALE = 25.0
        self.NODE_SPACING = 20  # 同时间节点之间的水平间距

        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.context_menu_node = None
        self.context_menu_char_id = None

        # 缩放相关
        self.min_scale = 0.25
        self.max_scale = 1.5
        
        # 框选相关
        self.rubber_band_active = False
        self.selected_event_ids = []

    def load_timeline_data(self, characters_with_events: list):
        self.scene.clear()
        self.all_nodes.clear()
        self.character_lines.clear()
        self.character_name_items.clear()
        self.organization_boxes = {}

        all_time_values = []
        for ch in characters_with_events:
            birth_time = ch.get('birth_time')
            death_time = ch.get('death_time')
            if birth_time:
                all_time_values.append(parse_time_to_value(birth_time))
            if death_time:
                all_time_values.append(parse_time_to_value(death_time))
            for ev in ch['events']:
                timestamp = ev.get('timestamp', 0)
                if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', str(timestamp)):
                    all_time_values.append(parse_time_to_value(timestamp))
                else:
                    all_time_values.append(float(timestamp) * 10000)

        if all_time_values:
            self.min_time_value = min(all_time_values)
            self.max_time_value = max(all_time_values)
            time_range = self.max_time_value - self.min_time_value
            # 只扩展右侧，左侧保持最早时间位置（避免负数偏移）
            self.max_time_value += time_range * 0.15
        else:
            self.min_time_value = 0
            self.max_time_value = 1000000

        from collections import defaultdict
        org_groups = defaultdict(list)
        for ch in characters_with_events:
            org_id = ch.get('org_id', 0)
            org_groups[org_id].append(ch)

        self.next_y_offset = 100
        for org_id, org_chars in org_groups.items():
            org_color = None
            if org_chars[0].get('org_color'):
                org_color = org_chars[0]['org_color']

            org_start_y = self.next_y_offset

            for ch in org_chars:
                ch_id = ch.get('id', len(self.character_lines) + 1)
                birth_time = ch.get('birth_time')
                death_time = ch.get('death_time')
                self._add_character_to_scene(ch_id, ch['name'], self.next_y_offset, birth_time, death_time, org_color)

                for ev in ch['events']:
                    ev = dict(ev)
                    ev['character_id'] = ch_id
                    timestamp = ev.get('timestamp', 0)
                    if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', str(timestamp)):
                        time_value = parse_time_to_value(timestamp)
                        ev['base_x'] = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
                    else:
                        time_value = float(timestamp) * 10000
                        ev['base_x'] = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
                    node = EventNodeItem(ev, self.next_y_offset)
                    self.scene.addItem(node)
                    self.all_nodes.append(node)

                self.next_y_offset += 160

            org_end_y = self.next_y_offset - 160

            if org_color and len(org_chars) > 1:
                org_box_pen = QPen(QColor(org_color), 1.5, Qt.DashLine)
                org_box_rect = self.scene.addRect(
                    10, org_start_y - 40,
                    140, org_end_y - org_start_y + 80,
                    org_box_pen
                )
                org_box_rect.setZValue(-15)
                self.organization_boxes[org_id] = org_box_rect

        # 绘制章节分隔线
        self._draw_chapter_dividers()

        if self.align_events:
            self.align_synchronized_events()

        # 设置场景矩形（确保时间轴正确显示，1.2倍时间轴）
        scene_width = self.LINE_START_X + (self.max_time_value - self.min_time_value) * 0.0025 + 200
        scene_height = max(self.next_y_offset + 100, 800)
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

        self.update_viewport_virtualization()
    
    def _draw_chapter_dividers(self):
        """绘制章节分隔线"""
        self.chapter_dividers.clear()
        
        # 收集所有事件的章节信息
        chapter_times = {}
        for node in self.all_nodes:
            ch_num = node.data.get('chapter_number')
            if ch_num:
                timestamp = node.data.get('timestamp', 0)
                if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', timestamp):
                    time_value = parse_time_to_value(timestamp)
                else:
                    time_value = float(timestamp) * 10000
                
                if ch_num not in chapter_times:
                    chapter_times[ch_num] = {'min': time_value, 'max': time_value, 'title': node.data.get('chapter_title', '')}
                else:
                    chapter_times[ch_num]['min'] = min(chapter_times[ch_num]['min'], time_value)
                    chapter_times[ch_num]['max'] = max(chapter_times[ch_num]['max'], time_value)
        
        # 按章节号排序绘制分隔线
        for ch_num in sorted(chapter_times.keys()):
            ch_info = chapter_times[ch_num]
            # 在章节开始位置绘制分隔线
            x_pos = self.LINE_START_X + (ch_info['min'] - self.min_time_value) * 0.0025
            
            # 绘制垂直虚线
            divider_pen = QPen(QColor("#4B5563"), 2, Qt.DashLine)
            line_item = self.scene.addLine(x_pos, 50, x_pos, self.next_y_offset + 50, divider_pen)
            line_item.setZValue(-20)
            
            # 添加章节标签
            label_text = f"第{ch_num}章"
            if ch_info['title']:
                label_text += f" {ch_info['title'][:10]}"
            label_item = self.scene.addText(label_text, QFont("Microsoft YaHei", 9, QFont.Bold))
            label_item.setDefaultTextColor(QColor("#374151"))
            label_item.setPos(x_pos + 5, 30)
            label_item.setZValue(5)
            
            self.chapter_dividers[ch_num] = {'line': line_item, 'label': label_item, 'x_pos': x_pos}

    def align_synchronized_events(self):
        """将相同时间戳的事件竖向对齐"""
        from collections import defaultdict

        timestamp_groups = defaultdict(list)
        for node in self.all_nodes:
            ts = node.data.get('timestamp', 0)
            timestamp_groups[ts].append(node)

        for ts, nodes in timestamp_groups.items():
            if isinstance(ts, str) and re.match(r'第?\d+年\d+月\d+日', ts):
                time_value = parse_time_to_value(ts)
            else:
                try:
                    time_value = float(ts) * 10000
                except:
                    time_value = 0

            center_x = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025

            if len(nodes) <= 1:
                for node in nodes:
                    node.x_pos = center_x
                    node.setPos(center_x, node.y_pos)
            else:
                total_width = (len(nodes) - 1) * self.NODE_SPACING
                start_x = center_x - total_width / 2

                for i, node in enumerate(nodes):
                    node.x_pos = start_x + i * self.NODE_SPACING
                    node.setPos(node.x_pos, node.y_pos)

    def set_align_events(self, enabled: bool):
        """设置是否启用事件对齐"""
        self.align_events = enabled
        if enabled:
            self.align_synchronized_events()
        else:
            # 恢复原始位置
            for node in self.all_nodes:
                timestamp = node.data.get('timestamp', 0)
                if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', str(timestamp)):
                    time_value = parse_time_to_value(timestamp)
                    base_x = node.data.get('base_x', self.LINE_START_X + (time_value - self.min_time_value) * 0.0025)
                else:
                    base_x = node.data.get('base_x', self.LINE_START_X + float(timestamp) * self.TIMESTAMP_SCALE)
                node.x_pos = base_x
                node.setPos(base_x, node.y_pos)
        self.update_viewport_virtualization()

    def _add_character_to_scene(self, character_id, name, y_offset, birth_time=None, death_time=None, org_color=None):
        # 人物图标和名字固定在左边（时间轴左侧固定区域）
        name_item = self.scene.addText(f"👤 {name}", QFont("Microsoft YaHei", 10, QFont.Bold))
        name_item.setDefaultTextColor(QColor("#1F2937"))
        name_item.setPos(10, y_offset - 32)
        name_item.setZValue(10)

        # 绘制时间线（从 150 开始，给左侧留出名字空间）
        line_start_x = 150
        # 根据最大时间值动态计算线条结束位置（1.2倍时间轴）
        line_end_x = line_start_x + (self.max_time_value - self.min_time_value) * 0.0025 + 100
        line_item = self.scene.addLine(line_start_x, y_offset, line_end_x, y_offset, QPen(QColor("#E5E7EB"), 2, Qt.SolidLine))
        line_item.setZValue(-10)

        char_info = {
            'line': line_item,
            'y_pos': y_offset,
            'name': name,
            'birth_time': birth_time,
            'death_time': death_time,
            'org_color': org_color
        }

        # 绘制生命线（出生到死亡之间的高亮）
        if birth_time is not None and death_time is not None:
            birth_value = parse_time_to_value(birth_time)
            death_value = parse_time_to_value(death_time)
            life_line = self.scene.addLine(
                line_start_x + (birth_value - self.min_time_value) * 0.0025, y_offset,
                line_start_x + (death_value - self.min_time_value) * 0.0025, y_offset,
                QPen(QColor("#10B981"), 3, Qt.SolidLine)
            )
            life_line.setZValue(-5)
            char_info['life_line'] = life_line

        self.character_lines[character_id] = char_info
        self.character_name_items[character_id] = name_item

        # 更新事件节点的 X 起始位置
        self.LINE_START_X = line_start_x

    def add_character(self, character_id, name, birth_time=None, death_time=None, org_color=None):
        if character_id in self.character_lines:
            return

        self._add_character_to_scene(character_id, name, self.next_y_offset, birth_time, death_time, org_color)
        self.next_y_offset += 160
        self.update_viewport_virtualization()

    def add_event(self, character_id, event_data):
        if character_id not in self.character_lines:
            return

        y_offset = self.character_lines[character_id]['y_pos']
        event_data = dict(event_data)
        event_data['character_id'] = character_id
        
        timestamp = event_data.get('timestamp', 0)
        if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', timestamp):
            time_value = parse_time_to_value(timestamp)
            event_data['base_x'] = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
        else:
            time_value = float(timestamp) * 10000
            event_data['base_x'] = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
        
        node = EventNodeItem(event_data, y_offset)
        self.scene.addItem(node)
        self.all_nodes.append(node)

        if self.align_events:
            self.align_synchronized_events()

        self.update_viewport_virtualization()

    def get_character_y_offset(self, character_id):
        if character_id in self.character_lines:
            return self.character_lines[character_id]['y_pos']
        return None

    def select_event(self, event_id):
        """选中指定事件节点"""
        for node in self.all_nodes:
            if node.data.get('id') == event_id:
                # 清除其他选中状态
                for n in self.all_nodes:
                    n.setSelected(False)
                node.setSelected(True)
                # 居中显示
                self.centerOn(node.x_pos, node.y_pos)
                return True
        return False

    def remove_event(self, event_id):
        """从画布中移除指定事件节点"""
        for node in self.all_nodes:
            if node.data.get('id') == event_id:
                self.scene.removeItem(node)
                self.all_nodes.remove(node)
                if self.align_events:
                    self.align_synchronized_events()
                self.update_viewport_virtualization()
                return True
        return False

    def remove_character(self, character_id):
        """从画布中移除指定人物及其所有事件节点"""
        if character_id not in self.character_lines:
            return False

        char_info = self.character_lines[character_id]

        # 移除该人物的所有事件节点
        nodes_to_remove = [node for node in self.all_nodes if node.data.get('character_id') == character_id]
        for node in nodes_to_remove:
            self.scene.removeItem(node)
            if node in self.all_nodes:
                self.all_nodes.remove(node)

        # 移除轴线
        self.scene.removeItem(char_info['line'])

        # 移除生命线
        if 'life_line' in char_info:
            self.scene.removeItem(char_info['life_line'])

        # 移除名字
        self.scene.removeItem(self.character_name_items[character_id])

        # 清理字典
        del self.character_lines[character_id]
        del self.character_name_items[character_id]

        if self.align_events:
            self.align_synchronized_events()

        self.update_viewport_virtualization()
        return True

    def append_character_timeline(self, character_data):
        """追加人物时间轴（不清空现有内容）"""
        ch_id = character_data.get('id')
        if ch_id in self.character_lines:
            return False

        ch_name = character_data.get('name', '')
        birth_time = character_data.get('birth_time')
        death_time = character_data.get('death_time')
        org_color = character_data.get('org_color')

        # 更新时间范围
        new_time_values = []
        if birth_time:
            new_time_values.append(parse_time_to_value(birth_time))
        if death_time:
            new_time_values.append(parse_time_to_value(death_time))
        for ev in character_data.get('events', []):
            timestamp = ev.get('timestamp', 0)
            if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', str(timestamp)):
                new_time_values.append(parse_time_to_value(timestamp))
            else:
                new_time_values.append(float(timestamp) * 10000)

        if new_time_values:
            if hasattr(self, 'min_time_value'):
                self.min_time_value = min(self.min_time_value, min(new_time_values))
                self.max_time_value = max(self.max_time_value, max(new_time_values))
            else:
                self.min_time_value = min(new_time_values)
                self.max_time_value = max(new_time_values)

            time_range = self.max_time_value - self.min_time_value
            # 只扩展右侧，左侧保持最早时间位置（避免负数偏移）
            self.max_time_value += time_range * 0.15

        # 添加人物到场景
        self._add_character_to_scene(ch_id, ch_name, self.next_y_offset, birth_time, death_time, org_color)

        # 添加事件节点
        for ev in character_data.get('events', []):
            ev = dict(ev)
            ev['character_id'] = ch_id
            timestamp = ev.get('timestamp', 0)
            if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', str(timestamp)):
                time_value = parse_time_to_value(timestamp)
                ev['base_x'] = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
            else:
                time_value = float(timestamp) * 10000
                ev['base_x'] = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
            node = EventNodeItem(ev, self.next_y_offset)
            self.scene.addItem(node)
            self.all_nodes.append(node)

        self.next_y_offset += 160

        # 更新场景矩形
        scene_width = self.LINE_START_X + (self.max_time_value - self.min_time_value) * 0.0025 + 200
        scene_height = max(self.next_y_offset + 100, 800)
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

        # 更新已有线条的长度
        for char_id, char_info in self.character_lines.items():
            line_item = char_info['line']
            line_end_x = self.LINE_START_X + (self.max_time_value - self.min_time_value) * 0.0025 + 100
            line_item.setLine(self.LINE_START_X, char_info['y_pos'], line_end_x, char_info['y_pos'])

            if 'life_line' in char_info:
                birth_value = parse_time_to_value(char_info['birth_time'])
                death_value = parse_time_to_value(char_info['death_time'])
                char_info['life_line'].setLine(
                    self.LINE_START_X + (birth_value - self.min_time_value) * 0.0025, char_info['y_pos'],
                    self.LINE_START_X + (death_value - self.min_time_value) * 0.0025, char_info['y_pos']
                )

        # 更新已有节点位置
        for node in self.all_nodes:
            timestamp = node.data.get('timestamp', 0)
            if isinstance(timestamp, str) and re.match(r'第?\d+年\d+月\d+日', str(timestamp)):
                time_value = parse_time_to_value(timestamp)
                new_x = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
            else:
                time_value = float(timestamp) * 10000
                new_x = self.LINE_START_X + (time_value - self.min_time_value) * 0.0025
            node.setPos(new_x, node.y_pos)
            node.x_pos = new_x

        if self.align_events:
            self.align_synchronized_events()

        self.update_viewport_virtualization()
        return True

    def mousePressEvent(self, event):
        """处理鼠标点击事件：点击节点或人物轴线时发出选择信号"""
        pos = self.mapToScene(event.pos())
        items = self.scene.items(pos)

        # 优先查找 EventNodeItem
        for item in items:
            if isinstance(item, EventNodeItem):
                # 清除其他选中状态
                for node in self.all_nodes:
                    node.setSelected(False)
                item.setSelected(True)
                self.node_selected.emit(item.data)
                super().mousePressEvent(event)
                return

        # 如果没有点击到节点，检查是否点击到人物轴线区域
        for char_id, char_info in self.character_lines.items():
            y_pos = char_info['y_pos']
            if abs(pos.y() - y_pos) < 20:
                self.character_selected.emit(char_id, char_info['name'])
                super().mousePressEvent(event)
                return

        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        """显示右键菜单"""
        from PySide6.QtWidgets import QMenu

        pos_scene = self.mapToScene(pos)
        items = self.scene.items(pos_scene)

        menu = QMenu()

        # 检查是否点击到事件节点
        for item in items:
            if isinstance(item, EventNodeItem):
                self.context_menu_node = item.data
                edit_action = menu.addAction("编辑此事件")
                edit_action.triggered.connect(lambda: self.node_edit_requested.emit(self.context_menu_node))
                delete_action = menu.addAction("删除此事件")
                delete_action.triggered.connect(lambda: self._delete_event_node(self.context_menu_node))
                menu.exec_(self.mapToGlobal(pos))
                return

        # 检查是否点击到人物轴线
        for char_id, char_info in self.character_lines.items():
            y_pos = char_info['y_pos']
            if abs(pos_scene.y() - y_pos) < 20:
                self.context_menu_char_id = char_id
                edit_action = menu.addAction(f"编辑人物「{char_info['name']}」")
                edit_action.triggered.connect(lambda: self.character_edit_requested.emit(char_id, char_info['name']))
                menu.exec_(self.mapToGlobal(pos))
                return

        # 空菜单（没有选中任何元素）
        add_event_action = menu.addAction("添加事件...")
        add_event_action.triggered.connect(self._add_event_at_position)
        menu.exec_(self.mapToGlobal(pos))

    def _delete_event_node(self, event_data):
        """删除事件节点"""
        event_id = event_data.get('id')
        if event_id:
            self.scene.removeItem([n for n in self.all_nodes if n.data.get('id') == event_id][0])
            self.all_nodes = [n for n in self.all_nodes if n.data.get('id') != event_id]
            if self.align_events:
                self.align_synchronized_events()
            self.update_viewport_virtualization()

    def _add_event_at_position(self):
        """在空白区域右键添加事件"""
        pass  # 由主窗口处理

    def wheelEvent(self, event: QWheelEvent):
        # Ctrl + 滚轮：缩放
        if event.modifiers() & Qt.ControlModifier:
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor

            if event.angleDelta().y() > 0:
                if self.scale_factor * zoom_in_factor <= self.max_scale:
                    self.scale(zoom_in_factor, 1.0)
                    self.scale_factor *= zoom_in_factor
            else:
                if self.scale_factor * zoom_out_factor >= self.min_scale:
                    self.scale(zoom_out_factor, 1.0)
                    self.scale_factor *= zoom_out_factor

            self.update_viewport_virtualization()
            event.accept()
        else:
            # 纯滚轮：左右滑动
            delta = event.angleDelta().x() if event.angleDelta().x() != 0 else event.angleDelta().y()
            scroll_amount = -delta * 3
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() + scroll_amount
            )
            event.accept()

    def set_scale(self, target_scale: float):
        """设置目标缩放级别"""
        target_scale = max(self.min_scale, min(self.max_scale, target_scale))
        if self.scale_factor == 0:
            self.scale_factor = 1.0
        scale_factor = target_scale / self.scale_factor
        self.scale(scale_factor, 1.0)
        self.scale_factor = target_scale
        self.update_viewport_virtualization()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.update_viewport_virtualization()

    def update_viewport_virtualization(self):
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        buffer_zone = 500
        left_bound = visible_rect.left() - buffer_zone
        right_bound = visible_rect.right() + buffer_zone
        
        for node in self.all_nodes:
            if left_bound <= node.x_pos <= right_bound:
                node.setVisible(True)
            else:
                node.setVisible(False)