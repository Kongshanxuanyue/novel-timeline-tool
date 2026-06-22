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

from collections import defaultdict
import re
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPen, QColor, QFont, QWheelEvent

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
        self.NODE_SPACING = 30  # 同一时间多个事件并排时的节点间距

        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.context_menu_node = None
        self.context_menu_char_id = None

        # 缩放相关
        self.min_scale = 0.25
        self.max_scale = 1.5

    # ==================== 核心：动态弹性布局 ====================
    def recalculate_layout(self):
        """重新计算所有节点的X坐标（非线性动态弹性间距），彻底解决重叠与过度留白 [cite: 16]"""
        if not self.all_nodes and not self.character_lines:
            return
            
        time_dict = {}
        
        # 1. 收集所有事件的时间点
        for node in self.all_nodes:
            ts = node.data.get('timestamp', 0)
            if isinstance(ts, str) and re.match(r'第?\d+年\d+月\d+日', ts):
                time_val = parse_time_to_value(ts)
            else:
                try: time_val = float(ts) * 10000
                except: time_val = 0
            
            if time_val not in time_dict:
                time_dict[time_val] = []
            time_dict[time_val].append(node)
            
        # 2. 收集所有人物的出生和死亡时间（确保即使没有事件，线也能画出来）
        for char_info in self.character_lines.values():
            if char_info.get('birth_time'):
                t = parse_time_to_value(char_info['birth_time'])
                if t not in time_dict: time_dict[t] = []
            if char_info.get('death_time'):
                t = parse_time_to_value(char_info['death_time'])
                if t not in time_dict: time_dict[t] = []

        if not time_dict:
            return

        sorted_times = sorted(time_dict.keys())
        
        # 3. 动态计算映射的 X 坐标
        time_x_map = {}
        current_x = self.LINE_START_X + 80  # 初始左侧偏移
        
        MIN_SPACING = 150       # 最小安全间距：保证无论多近的时间，文字框都不会重叠
        MAX_EXTRA_SPACING = 300 # 最大额外留白：哪怕相隔几百年，最多也只增加这么多像素
        
        time_x_map[sorted_times[0]] = current_x
        
        for i in range(1, len(sorted_times)):
            delta_time = sorted_times[i] - sorted_times[i-1]
            # 假设 1年(数值为10000) 增加 20 像素的距离感
            extra_spacing = min(MAX_EXTRA_SPACING, (delta_time / 10000.0) * 20)
            current_x += MIN_SPACING + extra_spacing
            time_x_map[sorted_times[i]] = current_x
            
        # 4. 应用坐标，处理同一时间的节点对齐
        max_x = current_x
        for time_val, nodes in time_dict.items():
            if not nodes: continue
            base_x = time_x_map[time_val]
            
            if len(nodes) <= 1 or not self.align_events:
                # 只有一个节点，或者关闭了对齐功能
                for node in nodes:
                    node.x_pos = base_x
                    node.data['base_x'] = base_x
                    node.setPos(base_x, node.y_pos)
            else:
                # 开启对齐：同一时间的事件错开显示
                total_w = (len(nodes) - 1) * self.NODE_SPACING
                start_x = base_x - total_w / 2
                for i, node in enumerate(nodes):
                    node.x_pos = start_x + i * self.NODE_SPACING
                    node.data['base_x'] = node.x_pos
                    node.setPos(node.x_pos, node.y_pos)
                    max_x = max(max_x, node.x_pos)
                    
        # 5. 统一更新人物背景轴线与生命线
        line_end_x = max_x + 200
        for char_id, char_info in self.character_lines.items():
            line_item = char_info['line']
            line_item.setLine(self.LINE_START_X, char_info['y_pos'], line_end_x, char_info['y_pos'])
            
            if 'life_line' in char_info:
                birth_val = parse_time_to_value(char_info['birth_time'])
                death_val = parse_time_to_value(char_info['death_time'])
                
                # 为出生/死亡进行坐标插值
                birth_x = self._interpolate_x(birth_val, sorted_times, time_x_map)
                death_x = self._interpolate_x(death_val, sorted_times, time_x_map)
                char_info['life_line'].setLine(birth_x, char_info['y_pos'], death_x, char_info['y_pos'])
                
        # 6. 更新章节分割线
        self._update_chapter_dividers(sorted_times, time_x_map)
        
        # 7. 更新画布可视区域
        scene_height = max(self.next_y_offset + 100, 800)
        self.scene.setSceneRect(0, 0, line_end_x, scene_height)

    def _interpolate_x(self, time_val, sorted_times, time_x_map):
        """为没有独立事件的时间点计算插值X坐标 [cite: 16]"""
        if not sorted_times: return self.LINE_START_X
        if time_val in time_x_map: return time_x_map[time_val]
        if time_val <= sorted_times[0]: return self.LINE_START_X + 20
        if time_val >= sorted_times[-1]: return time_x_map[sorted_times[-1]] + 100
        
        for i in range(len(sorted_times) - 1):
            t1, t2 = sorted_times[i], sorted_times[i+1]
            if t1 < time_val < t2:
                x1, x2 = time_x_map[t1], time_x_map[t2]
                ratio = (time_val - t1) / (t2 - t1)
                return x1 + (x2 - x1) * ratio
        return self.LINE_START_X

    def _update_chapter_dividers(self, sorted_times, time_x_map):
        """基于新的动态坐标体系重绘章节分割线 [cite: 16]"""
        for div in self.chapter_dividers.values():
            self.scene.removeItem(div['line'])
            self.scene.removeItem(div['label'])
        self.chapter_dividers.clear()
        
        chapter_times = {}
        for node in self.all_nodes:
            ch_num = node.data.get('chapter_number')
            if ch_num:
                ts = node.data.get('timestamp', 0)
                if isinstance(ts, str) and re.match(r'第?\d+年\d+月\d+日', ts):
                    time_val = parse_time_to_value(ts)
                else:
                    try: time_val = float(ts) * 10000
                    except: time_val = 0
                    
                if ch_num not in chapter_times:
                    chapter_times[ch_num] = {'min': time_val, 'title': node.data.get('chapter_title', '')}
                else:
                    chapter_times[ch_num]['min'] = min(chapter_times[ch_num]['min'], time_val)
                    
        for ch_num, ch_info in chapter_times.items():
            x_pos = self._interpolate_x(ch_info['min'], sorted_times, time_x_map)
            
            divider_pen = QPen(QColor("#4B5563"), 2, Qt.DashLine)
            line_item = self.scene.addLine(x_pos, 50, x_pos, self.next_y_offset + 50, divider_pen)
            line_item.setZValue(-20)
            
            label_text = f"第{ch_num}章"
            if ch_info['title']:
                label_text += f" {ch_info['title'][:10]}"
            label_item = self.scene.addText(label_text, QFont("Microsoft YaHei", 9, QFont.Bold))
            label_item.setDefaultTextColor(QColor("#374151"))
            label_item.setPos(x_pos + 5, 30)
            label_item.setZValue(5)
            
            self.chapter_dividers[ch_num] = {'line': line_item, 'label': label_item, 'x_pos': x_pos}

    # ==================== 生命周期与交互管理 ====================
    def load_timeline_data(self, characters_with_events: list):
        """全量加载人物和事件数据 [cite: 16]"""
        self.scene.clear()
        self.all_nodes.clear()
        self.character_lines.clear()
        self.character_name_items.clear()
        self.organization_boxes = {}

        org_groups = defaultdict(list)
        for ch in characters_with_events:
            org_id = ch.get('org_id', 0)
            org_groups[org_id].append(ch)

        self.next_y_offset = 100
        for org_id, org_chars in org_groups.items():
            org_color = org_chars[0].get('org_color') if org_chars[0].get('org_color') else None
            org_start_y = self.next_y_offset

            for ch in org_chars:
                ch_id = ch.get('id', len(self.character_lines) + 1)
                self._add_character_to_scene(ch_id, ch['name'], self.next_y_offset, ch.get('birth_time'), ch.get('death_time'), org_color)

                for ev in ch['events']:
                    ev = dict(ev)
                    ev['character_id'] = ch_id
                    ev['base_x'] = 0  # 坐标由 recalculate_layout 统一分配
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

        self.recalculate_layout()
        self.update_viewport_virtualization()

    def append_character_timeline(self, character_data):
        """追加单个角色轴线 [cite: 16]"""
        ch_id = character_data.get('id')
        if ch_id in self.character_lines:
            return False

        self._add_character_to_scene(ch_id, character_data.get('name', ''), self.next_y_offset, 
                                     character_data.get('birth_time'), character_data.get('death_time'), 
                                     character_data.get('org_color'))

        for ev in character_data.get('events', []):
            ev = dict(ev)
            ev['character_id'] = ch_id
            ev['base_x'] = 0 
            node = EventNodeItem(ev, self.next_y_offset)
            self.scene.addItem(node)
            self.all_nodes.append(node)

        self.next_y_offset += 160
        self.recalculate_layout()
        self.update_viewport_virtualization()
        return True

    def set_align_events(self, enabled: bool):
        """开关同一时间节点的竖向规避对齐 [cite: 16]"""
        self.align_events = enabled
        self.recalculate_layout()
        self.update_viewport_virtualization()

    def _add_character_to_scene(self, character_id, name, y_offset, birth_time=None, death_time=None, org_color=None):
        """绘制角色基础轴线与名称 [cite: 16]"""
        name_item = self.scene.addText(f"👤 {name}", QFont("Microsoft YaHei", 10, QFont.Bold))
        name_item.setDefaultTextColor(QColor("#1F2937"))
        name_item.setPos(10, y_offset - 32)
        name_item.setZValue(10)

        # 初始赋虚假长度，会在 recalculate_layout 修复
        line_item = self.scene.addLine(self.LINE_START_X, y_offset, self.LINE_START_X + 100, y_offset, QPen(QColor("#E5E7EB"), 2, Qt.SolidLine))
        line_item.setZValue(-10)

        char_info = {
            'line': line_item,
            'y_pos': y_offset,
            'name': name,
            'birth_time': birth_time,
            'death_time': death_time,
            'org_color': org_color
        }

        if birth_time is not None and death_time is not None:
            life_line = self.scene.addLine(
                self.LINE_START_X, y_offset, self.LINE_START_X + 100, y_offset,
                QPen(QColor("#10B981"), 3, Qt.SolidLine)
            )
            life_line.setZValue(-5)
            char_info['life_line'] = life_line

        self.character_lines[character_id] = char_info
        self.character_name_items[character_id] = name_item

    def add_event(self, character_id, event_data):
        if character_id not in self.character_lines:
            return

        y_offset = self.character_lines[character_id]['y_pos']
        event_data = dict(event_data)
        event_data['character_id'] = character_id
        event_data['base_x'] = 0
        
        node = EventNodeItem(event_data, y_offset)
        self.scene.addItem(node)
        self.all_nodes.append(node)

        self.recalculate_layout()
        self.update_viewport_virtualization()

    def get_character_y_offset(self, character_id):
        if character_id in self.character_lines:
            return self.character_lines[character_id]['y_pos']
        return None

    def select_event(self, event_id):
        for node in self.all_nodes:
            if node.data.get('id') == event_id:
                for n in self.all_nodes:
                    n.setSelected(False)
                node.setSelected(True)
                self.centerOn(node.x_pos, node.y_pos)
                return True
        return False

    def remove_event(self, event_id):
        for node in self.all_nodes:
            if node.data.get('id') == event_id:
                self.scene.removeItem(node)
                self.all_nodes.remove(node)
                self.recalculate_layout()
                self.update_viewport_virtualization()
                return True
        return False

    def remove_character(self, character_id):
        if character_id not in self.character_lines:
            return False

        char_info = self.character_lines[character_id]

        nodes_to_remove = [node for node in self.all_nodes if node.data.get('character_id') == character_id]
        for node in nodes_to_remove:
            self.scene.removeItem(node)
            if node in self.all_nodes:
                self.all_nodes.remove(node)

        self.scene.removeItem(char_info['line'])

        if 'life_line' in char_info:
            self.scene.removeItem(char_info['life_line'])

        self.scene.removeItem(self.character_name_items[character_id])

        del self.character_lines[character_id]
        del self.character_name_items[character_id]

        if self.character_lines:
            max_y = max(info['y_pos'] for info in self.character_lines.values())
            self.next_y_offset = max_y + 160
        else:
            self.next_y_offset = 80

        self.recalculate_layout()
        self.update_viewport_virtualization()
        return True

    def clear_all_characters(self):
        for char_id in list(self.character_lines.keys()):
            self.remove_character(char_id)
        self.next_y_offset = 80

    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        items = self.scene.items(pos)

        for item in items:
            if isinstance(item, EventNodeItem):
                for node in self.all_nodes:
                    node.setSelected(False)
                item.setSelected(True)
                self.node_selected.emit(item.data)
                super().mousePressEvent(event)
                return

        for char_id, char_info in self.character_lines.items():
            y_pos = char_info['y_pos']
            if abs(pos.y() - y_pos) < 20:
                self.character_selected.emit(char_id, char_info['name'])
                super().mousePressEvent(event)
                return

        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        pos_scene = self.mapToScene(pos)
        items = self.scene.items(pos_scene)

        menu = QMenu()

        for item in items:
            if isinstance(item, EventNodeItem):
                self.context_menu_node = item.data
                edit_action = menu.addAction("编辑此事件")
                edit_action.triggered.connect(lambda: self.node_edit_requested.emit(self.context_menu_node))
                delete_action = menu.addAction("删除此事件")
                delete_action.triggered.connect(lambda: self._delete_event_node(self.context_menu_node))
                menu.exec_(self.mapToGlobal(pos))
                return

        for char_id, char_info in self.character_lines.items():
            y_pos = char_info['y_pos']
            if abs(pos_scene.y() - y_pos) < 20:
                self.context_menu_char_id = char_id
                edit_action = menu.addAction(f"编辑人物「{char_info['name']}」")
                edit_action.triggered.connect(lambda: self.character_edit_requested.emit(char_id, char_info['name']))
                remove_action = menu.addAction(f"移除人物「{char_info['name']}」时间轴")
                remove_action.triggered.connect(lambda: self.remove_character(char_id))
                menu.exec_(self.mapToGlobal(pos))
                return

        add_event_action = menu.addAction("添加事件...")
        add_event_action.triggered.connect(self._add_event_at_position)
        
        if self.character_lines:
            clear_action = menu.addAction("清空所有时间轴")
            clear_action.triggered.connect(self.clear_all_characters)
        
        menu.exec_(self.mapToGlobal(pos))

    def _delete_event_node(self, event_data):
        event_id = event_data.get('id')
        if event_id:
            node_to_rm = [n for n in self.all_nodes if n.data.get('id') == event_id][0]
            self.scene.removeItem(node_to_rm)
            self.all_nodes.remove(node_to_rm)
            self.recalculate_layout()
            self.update_viewport_virtualization()

    def _add_event_at_position(self):
        pass  

    def wheelEvent(self, event: QWheelEvent):
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
            delta = event.angleDelta().x() if event.angleDelta().x() != 0 else event.angleDelta().y()
            scroll_amount = -delta * 3
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() + scroll_amount
            )
            event.accept()

    def set_scale(self, target_scale: float):
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