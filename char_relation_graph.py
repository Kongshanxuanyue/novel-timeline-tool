"""角色关系图视图组件"""

import math
import random
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsTextItem, QGraphicsItem, QMenu, QMessageBox, QComboBox,
    QGraphicsLineItem, QGraphicsPolygonItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QFont,
    QRadialGradient, QPolygonF
)

from database import DatabaseManager


class CharNodeItem(QGraphicsEllipseItem):
    """角色节点图形项"""
    
    def __init__(self, char_data, event_count, x=0, y=0):
        # 节点大小根据事件数量计算
        size = 36 + min(event_count * 4, 44)
        super().__init__(-size/2, -size/2, size, size)
        
        self.char_data = char_data
        self.event_count = event_count
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        
        # 设置颜色
        color = QColor(char_data.get('color', '#8B5CF6'))
        
        # 发光效果
        gradient = QRadialGradient(0, 0, size/2)
        gradient.setColorAt(0, color.lighter(130))
        gradient.setColorAt(0.6, color)
        gradient.setColorAt(1, color.darker(120))
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(color.darker(150), 2))
        
        # 首字母标签（作为头像占位符）
        name = char_data.get('name', '?')
        initial = name[0] if name else '?'
        self.avatar_label = QGraphicsTextItem(initial, self)
        font = QFont("Microsoft YaHei", max(10, int(size/3.5)), QFont.Bold)
        self.avatar_label.setFont(font)
        self.avatar_label.setDefaultTextColor(QColor("#FFFFFF"))
        label_rect = self.avatar_label.boundingRect()
        self.avatar_label.setPos(-label_rect.width()/2, -label_rect.height()/2)
        
        # 角色名称标签（在节点下方）
        self.name_label = QGraphicsTextItem(name, self)
        self.name_label.setFont(QFont("Microsoft YaHei", 9))
        self.name_label.setDefaultTextColor(QColor("#E5E7EB"))
        name_rect = self.name_label.boundingRect()
        self.name_label.setPos(-name_rect.width()/2, size/2 + 4)
        
        self.relationships = []
        self._highlighted = False
        self._dimmed = False
    
    def set_highlighted(self, highlighted):
        """设置高亮状态"""
        self._highlighted = highlighted
        if highlighted:
            self.setPen(QPen(QColor("#FBBF24"), 4))
        else:
            color = QColor(self.char_data.get('color', '#8B5CF6'))
            self.setPen(QPen(color.darker(150), 2))
    
    def set_dimmed(self, dimmed):
        """设置暗淡状态（用于筛选）"""
        self._dimmed = dimmed
        if dimmed:
            self.setOpacity(0.25)
        else:
            self.setOpacity(1.0)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.relationships:
                edge.update_position()
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event):
        if not self._dimmed:
            self.setScale(1.15)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.setScale(1.0)
        super().hoverLeaveEvent(event)


class CharRelationEdgeItem(QGraphicsPathItem):
    """角色关系连线图形项"""
    
    def __init__(self, rel_data, node1, node2):
        super().__init__()
        self.rel_data = rel_data
        self.node1 = node1
        self.node2 = node2
        
        self.setZValue(5)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        # 关系颜色
        color = QColor(rel_data.get('relationship_color', '#9CA3AF'))
        width = 1 + (rel_data.get('strength', 5) - 1) * 0.5
        
        pen = QPen(color, width)
        pen.setStyle(Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        
        # 是否双向
        self.bidirectional = rel_data.get('bidirectional', 1)
        
        # 箭头（非双向关系显示方向箭头）
        self.arrow_item = None
        if not self.bidirectional:
            self.arrow_item = QGraphicsPolygonItem(self)
            self.arrow_item.setBrush(QBrush(color))
            self.arrow_item.setPen(QPen(color, 1))
            self.arrow_item.setZValue(7)
        
        # 关系名称标签
        self.label = QGraphicsTextItem(rel_data.get('relationship_name', ''), self)
        self.label.setFont(QFont("Microsoft YaHei", 7))
        self.label.setDefaultTextColor(color)
        self.label.setZValue(6)
        
        self._dimmed = False
        self.update_position()
    
    def set_dimmed(self, dimmed):
        self._dimmed = dimmed
        if dimmed:
            self.setOpacity(0.15)
        else:
            self.setOpacity(1.0)
    
    def update_position(self):
        p1 = self.node1.pos()
        p2 = self.node2.pos()
        
        # 计算节点边缘点（而不是中心）
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1:
            dist = 1
        
        # 节点半径
        r1 = self.node1.rect().width() / 2
        r2 = self.node2.rect().width() / 2
        
        # 边缘点
        edge1 = QPointF(p1.x() + dx/dist * r1, p1.y() + dy/dist * r1)
        edge2 = QPointF(p2.x() - dx/dist * r2, p2.y() - dy/dist * r2)
        
        # 贝塞尔曲线
        path = QPainterPath()
        path.moveTo(edge1)
        
        mid_x = (edge1.x() + edge2.x()) / 2
        mid_y = (edge1.y() + edge2.y()) / 2
        offset = min(abs(dx), abs(dy)) * 0.15
        ctrl = QPointF(mid_x + offset, mid_y - offset)
        
        path.quadTo(ctrl, edge2)
        self.setPath(path)
        
        # 更新箭头位置
        if self.arrow_item and not self.bidirectional:
            arrow_size = 8
            # 在距离node2边缘 arrow_size+2 的位置
            t = 1.0 - (arrow_size + 2) / dist
            if t < 0:
                t = 0.5
            arrow_pos = path.pointAtPercent(t)
            angle = math.atan2(edge2.y() - ctrl.y(), edge2.x() - ctrl.x())
            
            pts = QPolygonF([
                QPointF(arrow_pos.x() + arrow_size * math.cos(angle),
                        arrow_pos.y() + arrow_size * math.sin(angle)),
                QPointF(arrow_pos.x() + arrow_size * 0.6 * math.cos(angle + 2.5),
                        arrow_pos.y() + arrow_size * 0.6 * math.sin(angle + 2.5)),
                QPointF(arrow_pos.x() + arrow_size * 0.6 * math.cos(angle - 2.5),
                        arrow_pos.y() + arrow_size * 0.6 * math.sin(angle - 2.5)),
            ])
            self.arrow_item.setPolygon(pts)
        
        # 更新标签位置
        label_pos = path.pointAtPercent(0.5)
        self.label.setPos(label_pos.x() - self.label.boundingRect().width()/2,
                         label_pos.y() - self.label.boundingRect().height()/2 - 8)
    
    def hoverEnterEvent(self, event):
        if not self._dimmed:
            tip = f"{self.rel_data.get('char1_name', '')} - {self.rel_data.get('char2_name', '')}\n"
            tip += f"关系: {self.rel_data.get('relationship_name', '')}\n"
            tip += f"强度: {self.rel_data.get('strength', 5)}"
            if self.rel_data.get('description'):
                tip += f"\n{self.rel_data['description']}"
            QMessageBox.information(None, "关系详情", tip)
        super().hoverEnterEvent(event)


class CharRelationGraphView(QGraphicsView):
    """角色关系图视图"""
    
    char_double_clicked = Signal(int)
    char_right_clicked = Signal(int, QPointF)
    relation_clicked = Signal(int)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        self.setBackgroundBrush(QBrush(QColor("#111827")))
        
        self.nodes = {}
        self.edges = []
        
        self.layout_timer = QTimer()
        self.layout_timer.timeout.connect(self.apply_force_layout_step)
        self.layout_iterations = 0
        self.max_layout_iterations = 100
        
        self.scale_factor = 1.0
    
    def load_graph_data(self, rel_type_filter=None, org_filter=None, search_term=None):
        """加载关系图数据"""
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        
        characters = self.db.get_all_characters()
        if not characters:
            return
        
        relationships = self.db.get_all_character_relationships()
        
        # 筛选关系
        if rel_type_filter:
            relationships = [r for r in relationships if r['relationship_type_id'] == rel_type_filter]
        
        # 构建需要显示的人物ID集合
        visible_char_ids = set()
        for rel in relationships:
            visible_char_ids.add(rel['char1_id'])
            visible_char_ids.add(rel['char2_id'])
        
        # 组织筛选：如果指定了组织，只显示该组织的人物
        if org_filter:
            org_chars = {c['id'] for c in self.db.get_characters_by_organization(org_filter)}
            visible_char_ids &= org_chars
            relationships = [r for r in relationships 
                           if r['char1_id'] in visible_char_ids and r['char2_id'] in visible_char_ids]
        
        # 如果没有关系但有搜索，显示所有人物
        if not relationships and search_term:
            visible_char_ids = {c['id'] for c in characters}
        elif not relationships and not search_term:
            # 没有任何关系时，显示所有人物
            visible_char_ids = {c['id'] for c in characters}
        
        # 搜索高亮
        search_match_ids = set()
        if search_term:
            term = search_term.lower()
            for ch in characters:
                if term in ch.get('name', '').lower() or term in ch.get('alias', '').lower():
                    search_match_ids.add(ch['id'])
        
        # 创建节点
        scene_w = max(self.width() - 80, 400)
        scene_h = max(self.height() - 80, 300)
        
        chars_to_show = [c for c in characters if c['id'] in visible_char_ids]
        for i, ch in enumerate(chars_to_show):
            event_count = self.db.get_character_event_count(ch['id'])
            
            angle = 2 * math.pi * i / max(len(chars_to_show), 1)
            radius = min(scene_w, scene_h) / 3
            x = scene_w / 2 + radius * math.cos(angle) * random.uniform(0.8, 1.2)
            y = scene_h / 2 + radius * math.sin(angle) * random.uniform(0.8, 1.2)
            
            node = CharNodeItem(ch, event_count, x, y)
            
            # 搜索高亮
            if search_term:
                if ch['id'] in search_match_ids:
                    node.set_highlighted(True)
                else:
                    node.set_dimmed(True)
            
            self.nodes[ch['id']] = node
            self.scene.addItem(node)
        
        # 创建连线
        for rel in relationships:
            c1_id = rel['char1_id']
            c2_id = rel['char2_id']
            
            if c1_id in self.nodes and c2_id in self.nodes:
                edge = CharRelationEdgeItem(rel, self.nodes[c1_id], self.nodes[c2_id])
                self.nodes[c1_id].relationships.append(edge)
                self.nodes[c2_id].relationships.append(edge)
                
                # 搜索时如果连线两端节点被dimmed，连线也dimmed
                if search_term and (c1_id not in search_match_ids and c2_id not in search_match_ids):
                    edge.set_dimmed(True)
                
                self.edges.append(edge)
                self.scene.addItem(edge)
        
        self.start_force_layout()
    
    def start_force_layout(self):
        self.layout_iterations = 0
        self.layout_timer.start(30)
    
    def apply_force_layout_step(self):
        if self.layout_iterations >= self.max_layout_iterations:
            self.layout_timer.stop()
            return
        
        self.layout_iterations += 1
        
        k = 0.01
        repulsion = 5000
        cooling = 1.0 - self.layout_iterations / self.max_layout_iterations
        
        forces = {cid: QPointF(0, 0) for cid in self.nodes}
        
        for id1, node1 in self.nodes.items():
            for id2, node2 in self.nodes.items():
                if id1 == id2:
                    continue
                dx = node1.pos().x() - node2.pos().x()
                dy = node1.pos().y() - node2.pos().y()
                dist = math.sqrt(dx*dx + dy*dy) + 1
                force = repulsion / (dist * dist)
                forces[id1] += QPointF(dx/dist * force, dy/dist * force)
        
        for edge in self.edges:
            node1 = edge.node1
            node2 = edge.node2
            dx = node2.pos().x() - node1.pos().x()
            dy = node2.pos().y() - node1.pos().y()
            dist = math.sqrt(dx*dx + dy*dy)
            
            ideal_dist = 140 + edge.rel_data.get('strength', 5) * 12
            force = k * (dist - ideal_dist)
            strength_factor = edge.rel_data.get('strength', 5) / 5
            force *= strength_factor
            
            id1 = node1.char_data['id']
            id2 = node2.char_data['id']
            
            forces[id1] += QPointF(dx/dist * force * cooling, dy/dist * force * cooling)
            forces[id2] -= QPointF(dx/dist * force * cooling, dy/dist * force * cooling)
        
        for cid, force in forces.items():
            node = self.nodes[cid]
            new_pos = node.pos() + force * cooling * 0.5
            margin = 60
            new_x = max(margin, min(self.width() - margin, new_pos.x()))
            new_y = max(margin, min(self.height() - margin, new_pos.y()))
            node.setPos(new_x, new_y)
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1/1.15
        new_scale = self.scale_factor * factor
        if 0.2 <= new_scale <= 3.0:
            self.scale_factor = new_scale
            self.scale(factor, factor)
    
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, CharNodeItem):
            self.char_double_clicked.emit(item.char_data['id'])
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, CharNodeItem):
            self.char_right_clicked.emit(item.char_data['id'], event.globalPos())
        elif isinstance(item, CharRelationEdgeItem):
            self.relation_clicked.emit(item.rel_data['id'])
        super().contextMenuEvent(event)
    
    def highlight_path(self, path_nodes):
        """高亮显示路径上的节点和连线"""
        # 先重置所有
        for node in self.nodes.values():
            node.setOpacity(0.2)
        for edge in self.edges:
            edge.setOpacity(0.1)
        
        # 高亮路径节点
        for cid in path_nodes:
            if cid in self.nodes:
                self.nodes[cid].setOpacity(1.0)
                self.nodes[cid].set_highlighted(True)
        
        # 高亮路径连线
        path_set = set(path_nodes)
        for edge in self.edges:
            c1 = edge.node1.char_data['id']
            c2 = edge.node2.char_data['id']
            if c1 in path_set and c2 in path_set:
                edge.setOpacity(1.0)
    
    def reset_highlight(self):
        """重置高亮"""
        for node in self.nodes.values():
            node.setOpacity(1.0)
            node.set_highlighted(False)
        for edge in self.edges:
            edge.setOpacity(1.0)
    
    def export_image(self, file_path):
        from PySide6.QtGui import QImage, QPainter
        rect = self.scene.sceneRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(QColor("#111827"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene.render(painter)
        painter.end()
        image.save(file_path)


class CharRelationGraphPanel(QWidget):
    """角色关系图面板"""
    
    char_selected = Signal(int)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 行1：搜索框
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("搜索角色:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入角色名或别名...")
        self.search_edit.setMinimumWidth(200)
        row1.addWidget(self.search_edit)
        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.setMinimumWidth(80)
        row1.addWidget(self.search_btn)
        self.clear_search_btn = QPushButton("✕ 清除")
        self.clear_search_btn.setMinimumWidth(80)
        row1.addWidget(self.clear_search_btn)
        row1.addStretch()
        layout.addLayout(row1)
        
        # 行2：关系类型筛选
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("关系类型:"))
        self.rel_type_combo = QComboBox()
        self.rel_type_combo.addItem("全部", None)
        self.rel_type_combo.setMinimumWidth(200)
        row2.addWidget(self.rel_type_combo)
        row2.addStretch()
        layout.addLayout(row2)
        
        # 行3：组织筛选
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("所属组织:"))
        self.org_combo = QComboBox()
        self.org_combo.addItem("全部", None)
        self.org_combo.setMinimumWidth(200)
        row3.addWidget(self.org_combo)
        self.filter_btn = QPushButton("应用筛选")
        self.filter_btn.setMinimumWidth(100)
        row3.addWidget(self.filter_btn)
        row3.addStretch()
        layout.addLayout(row3)
        
        # 行4：路径查找选择
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("关系路径:"))
        row4.addWidget(QLabel("从"))
        self.path_char1 = QComboBox()
        self.path_char1.setMinimumWidth(150)
        row4.addWidget(self.path_char1)
        row4.addWidget(QLabel("到"))
        self.path_char2 = QComboBox()
        self.path_char2.setMinimumWidth(150)
        row4.addWidget(self.path_char2)
        row4.addStretch()
        layout.addLayout(row4)
        
        # 行5：操作按钮
        row5 = QHBoxLayout()
        self.find_path_btn = QPushButton("🔗 查找最短路径")
        self.find_path_btn.setMinimumWidth(120)
        row5.addWidget(self.find_path_btn)
        
        self.reset_path_btn = QPushButton("↺ 重置高亮")
        self.reset_path_btn.setMinimumWidth(100)
        row5.addWidget(self.reset_path_btn)
        
        row5.addSpacing(12)
        
        refresh_btn = QPushButton("🔄 刷新图")
        refresh_btn.setMinimumWidth(80)
        row5.addWidget(refresh_btn)
        
        export_btn = QPushButton("📷 导出图片")
        export_btn.setMinimumWidth(100)
        row5.addWidget(export_btn)
        
        row5.addStretch()
        layout.addLayout(row5)
        
        # 连接信号
        self.search_btn.clicked.connect(self.apply_filters)
        self.clear_search_btn.clicked.connect(self.clear_search)
        self.filter_btn.clicked.connect(self.apply_filters)
        self.find_path_btn.clicked.connect(self.find_shortest_path)
        self.reset_path_btn.clicked.connect(self.reset_path_highlight)
        refresh_btn.clicked.connect(self.refresh_graph)
        export_btn.clicked.connect(self.export_image)
        
        # 关系图视图
        self.graph_view = CharRelationGraphView(self.db)
        self.graph_view.char_double_clicked.connect(self.on_char_double_clicked)
        self.graph_view.char_right_clicked.connect(self.on_char_right_clicked)
        self.graph_view.relation_clicked.connect(self.on_relation_clicked)
        layout.addWidget(self.graph_view)
        
        self._refresh_filter_options()
    
    def _refresh_filter_options(self):
        """刷新筛选选项"""
        # 关系类型
        current_rel = self.rel_type_combo.currentData()
        self.rel_type_combo.clear()
        self.rel_type_combo.addItem("全部", None)
        for rt in self.db.get_all_character_relationship_types():
            self.rel_type_combo.addItem(rt['name'], rt['id'])
        if current_rel:
            idx = self.rel_type_combo.findData(current_rel)
            if idx >= 0:
                self.rel_type_combo.setCurrentIndex(idx)
        
        # 组织
        current_org = self.org_combo.currentData()
        self.org_combo.clear()
        self.org_combo.addItem("全部", None)
        self.org_combo.addItem("无组织", 0)
        for org in self.db.get_all_organizations():
            self.org_combo.addItem(org['name'], org['id'])
        if current_org is not None:
            idx = self.org_combo.findData(current_org)
            if idx >= 0:
                self.org_combo.setCurrentIndex(idx)
        
        # 路径查找角色
        self.path_char1.clear()
        self.path_char2.clear()
        chars = self.db.get_all_characters()
        for ch in chars:
            self.path_char1.addItem(ch['name'], ch['id'])
            self.path_char2.addItem(ch['name'], ch['id'])
    
    def apply_filters(self):
        """应用筛选条件"""
        rel_type = self.rel_type_combo.currentData()
        org_id = self.org_combo.currentData()
        search = self.search_edit.text().strip() or None
        self.graph_view.load_graph_data(rel_type_filter=rel_type, org_filter=org_id, search_term=search)
    
    def clear_search(self):
        self.search_edit.clear()
        self.apply_filters()
    
    def refresh_graph(self):
        self._refresh_filter_options()
        self.apply_filters()
    
    def find_shortest_path(self):
        """查找两个角色之间的最短关系路径"""
        char1_id = self.path_char1.currentData()
        char2_id = self.path_char2.currentData()
        
        if char1_id == char2_id:
            QMessageBox.information(self, "提示", "请选择两个不同的角色")
            return
        
        # BFS查找最短路径
        path = self._bfs_shortest_path(char1_id, char2_id)
        if path:
            self.graph_view.highlight_path(path)
            path_names = []
            for cid in path:
                ch = self.db.get_character(cid)
                path_names.append(ch['name'] if ch else '?')
            self.status_label = QLabel(f"路径: {' → '.join(path_names)}")
        else:
            QMessageBox.information(self, "结果", "未找到关系路径")
    
    def _bfs_shortest_path(self, start_id, end_id):
        """BFS查找最短路径"""
        from collections import deque
        
        relationships = self.db.get_all_character_relationships()
        
        # 构建邻接表
        adj = {}
        for rel in relationships:
            c1, c2 = rel['char1_id'], rel['char2_id']
            adj.setdefault(c1, []).append(c2)
            adj.setdefault(c2, []).append(c1)
        
        if start_id not in adj:
            return None
        
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
        
        while queue:
            current, path = queue.popleft()
            if current == end_id:
                return path
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def reset_path_highlight(self):
        self.graph_view.reset_highlight()
    
    def on_char_double_clicked(self, char_id):
        self.char_selected.emit(char_id)
    
    def on_char_right_clicked(self, char_id, pos):
        menu = QMenu()
        view_detail = menu.addAction("查看详情")
        view_detail.triggered.connect(lambda: self.char_selected.emit(char_id))
        
        add_rel = menu.addAction("添加关系...")
        add_rel.triggered.connect(lambda: self.add_relation(char_id))
        
        menu.exec_(pos)
    
    def on_relation_clicked(self, rel_id):
        from dialogs import EditCharRelationDialog
        dialog = EditCharRelationDialog(self.db, rel_id, self)
        if dialog.exec() == EditCharRelationDialog.Accepted:
            self.refresh_graph()
    
    def add_relation(self, char_id=None):
        from dialogs import AddCharRelationDialog
        dialog = AddCharRelationDialog(self.db, char_id, self)
        if dialog.exec() == AddCharRelationDialog.Accepted:
            self.refresh_graph()
    
    def export_image(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "导出角色关系图", "", "PNG图片 (*.png)")
        if file_path:
            self.graph_view.export_image(file_path)
            QMessageBox.information(self, "导出成功", f"已保存到:\n{file_path}")
    
    def export_relations_markdown(self):
        """导出人物关系卡为Markdown"""
        relationships = self.db.get_all_character_relationships()
        if not relationships:
            QMessageBox.information(self, "提示", "暂无角色关系可导出")
            return
        
        md = "# 人物关系卡\n\n"
        for rel in relationships:
            md += f"## {rel['char1_name']} ↔ {rel['char2_name']}\n\n"
            md += f"- **关系类型**: {rel['relationship_name']}\n"
            md += f"- **关系强度**: {rel.get('strength', 5)}/10\n"
            if rel.get('description'):
                md += f"- **描述**: {rel['description']}\n"
            if rel.get('start_event_title'):
                md += f"- **起始事件**: {rel['start_event_title']}\n"
            md += "\n---\n\n"
        
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "导出人物关系卡", "", "Markdown (*.md)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md)
            QMessageBox.information(self, "导出成功", f"已保存到:\n{file_path}")