"""势力关系图视图组件"""

import math
import random
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsTextItem, QGraphicsItemGroup, QMenu, QMessageBox, QToolTip,
    QGraphicsItem, QFileDialog, QComboBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QRectF, QPropertyAnimation
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QFont, QTransform,
    QLinearGradient, QRadialGradient
)

from database import DatabaseManager, parse_time_to_value, format_time_label


class OrgNodeItem(QGraphicsEllipseItem):
    """组织节点图形项"""
    
    def __init__(self, org_data, member_count, x=0, y=0):
        # 节点大小根据成员数量计算
        size = 40 + min(member_count * 5, 60)
        super().__init__(-size/2, -size/2, size, size)
        
        self.org_data = org_data
        self.member_count = member_count
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        
        # 设置颜色
        color = QColor(org_data.get('color', '#8B5CF6'))
        
        # 发光效果
        gradient = QRadialGradient(0, 0, size/2)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(0.7, color)
        gradient.setColorAt(1, color.darker(130))
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(color.darker(150), 2))
        
        # 组织名称标签
        self.label = QGraphicsTextItem(org_data['name'], self)
        font = QFont("Microsoft YaHei", 10, QFont.Bold)
        self.label.setFont(font)
        self.label.setDefaultTextColor(QColor("#FFFFFF"))
        label_rect = self.label.boundingRect()
        self.label.setPos(-label_rect.width()/2, -label_rect.height()/2 - 5)
        
        # 成员数量标签
        self.count_label = QGraphicsTextItem(f"({member_count})", self)
        self.count_label.setFont(QFont("Microsoft YaHei", 8))
        self.count_label.setDefaultTextColor(QColor("#FFFFFF"))
        count_rect = self.count_label.boundingRect()
        self.count_label.setPos(-count_rect.width()/2, label_rect.height()/2 - 5)
        
        self.relationships = []
        self._hover = False
    
    def itemChange(self, change, value):
        """位置变化时更新连线"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.relationships:
                edge.update_position()
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event):
        """鼠标悬停进入"""
        self._hover = True
        self.setScale(1.1)
        # 显示悬浮提示
        tip = f"{self.org_data['name']}\n成员数: {self.member_count}"
        QToolTip.showText(event.sceneBoundingRect().center().toPoint(), tip)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """鼠标悬停离开"""
        self._hover = False
        self.setScale(1.0)
        super().hoverLeaveEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件"""
        # 由父组件处理
        super().mouseDoubleClickEvent(event)


class RelationEdgeItem(QGraphicsPathItem):
    """关系连线图形项"""
    
    def __init__(self, rel_data, node1, node2):
        super().__init__()
        self.rel_data = rel_data
        self.node1 = node1
        self.node2 = node2
        
        self.setZValue(5)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        # 关系颜色和线型
        color = QColor(rel_data.get('relationship_color', '#9CA3AF'))
        line_style = rel_data.get('line_style', 'solid')
        
        # 线宽根据强度计算 (1-10 -> 1-6px)
        width = 1 + (rel_data.get('strength', 5) - 1) * 0.5
        
        pen = QPen(color, width)
        if line_style == 'dashed':
            pen.setStyle(Qt.DashLine)
        elif line_style == 'dotted':
            pen.setStyle(Qt.DotLine)
        else:
            pen.setStyle(Qt.SolidLine)
        self.setPen(pen)
        
        # 关系类型标签
        self.label = QGraphicsTextItem(rel_data.get('relationship_name', ''), self)
        self.label.setFont(QFont("Microsoft YaHei", 8))
        self.label.setDefaultTextColor(color)
        self.label.setZValue(6)
        
        self.update_position()
    
    def update_position(self):
        """更新连线位置"""
        p1 = self.node1.pos()
        p2 = self.node2.pos()
        
        # 贝塞尔曲线避免重叠
        path = QPainterPath()
        path.moveTo(p1)
        
        # 计算中间点
        mid_x = (p1.x() + p2.x()) / 2
        mid_y = (p1.y() + p2.y()) / 2
        
        # 添加弯曲
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        offset = min(abs(dx), abs(dy)) * 0.2
        
        # 根据位置决定弯曲方向
        ctrl1 = QPointF(mid_x + offset, mid_y - offset)
        ctrl2 = QPointF(mid_x - offset, mid_y + offset)
        
        path.quadTo(ctrl1, p2)
        self.setPath(path)
        
        # 更新标签位置
        label_pos = path.pointAtPercent(0.5)
        self.label.setPos(label_pos.x() - self.label.boundingRect().width()/2,
                         label_pos.y() - self.label.boundingRect().height()/2 - 10)
    
    def hoverEnterEvent(self, event):
        """鼠标悬停显示详情"""
        tip = f"{self.rel_data.get('org1_name', '')} - {self.rel_data.get('org2_name', '')}\n"
        tip += f"关系: {self.rel_data.get('relationship_name', '')}\n"
        tip += f"强度: {self.rel_data.get('strength', 5)}"
        if self.rel_data.get('description'):
            tip += f"\n{self.rel_data['description']}"
        QToolTip.showText(event.sceneBoundingRect().center().toPoint(), tip)
        super().hoverEnterEvent(event)
    
    def mousePressEvent(self, event):
        """点击选中"""
        self.setSelected(True)
        super().mousePressEvent(event)


class OrgRelationGraphView(QGraphicsView):
    """势力关系图视图"""
    
    org_double_clicked = Signal(int)  # 组织ID
    org_right_clicked = Signal(int, QPointF)  # 组织ID, 位置
    relation_clicked = Signal(int)  # 关系ID
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 视图设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # 背景
        self.setBackgroundBrush(QBrush(QColor("#1E293B")))
        
        # 数据
        self.nodes = {}  # org_id -> OrgNodeItem
        self.edges = []  # RelationEdgeItem列表
        
        # 力导向布局参数
        self.layout_timer = QTimer()
        self.layout_timer.timeout.connect(self.apply_force_layout_step)
        self.layout_iterations = 0
        self.max_layout_iterations = 100
        
        # 时间切片
        self.current_time_value = 0
        
        # 缩放
        self.scale_factor = 1.0
        
        self.load_graph_data()
    
    def load_graph_data(self, time_value=None):
        """加载关系图数据"""
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        
        if time_value is not None:
            self.current_time_value = time_value
        
        # 获取所有组织
        orgs = self.db.get_all_organizations()
        if not orgs:
            return
        
        # 获取关系数据
        if time_value:
            relationships = self.db.get_org_relationships_at_time(time_value)
        else:
            relationships = self.db.get_all_org_relationships()
        
        # 创建节点
        scene_width = self.width() - 100
        scene_height = self.height() - 100
        
        for i, org in enumerate(orgs):
            member_count = self.db.get_org_member_count(org['id'])
            
            # 随机初始位置（圆形分布）
            angle = 2 * math.pi * i / len(orgs)
            radius = min(scene_width, scene_height) / 3
            x = scene_width / 2 + radius * math.cos(angle) * random.uniform(0.8, 1.2)
            y = scene_height / 2 + radius * math.sin(angle) * random.uniform(0.8, 1.2)
            
            node = OrgNodeItem(org, member_count, x, y)
            self.nodes[org['id']] = node
            self.scene.addItem(node)
        
        # 创建连线
        for rel in relationships:
            org1_id = rel['org1_id']
            org2_id = rel['org2_id']
            
            if org1_id in self.nodes and org2_id in self.nodes:
                node1 = self.nodes[org1_id]
                node2 = self.nodes[org2_id]
                
                edge = RelationEdgeItem(rel, node1, node2)
                node1.relationships.append(edge)
                node2.relationships.append(edge)
                self.edges.append(edge)
                self.scene.addItem(edge)
        
        # 启动力导向布局
        self.start_force_layout()
    
    def start_force_layout(self):
        """启动力导向布局动画"""
        self.layout_iterations = 0
        self.layout_timer.start(30)
    
    def apply_force_layout_step(self):
        """力导向布局单步"""
        if self.layout_iterations >= self.max_layout_iterations:
            self.layout_timer.stop()
            return
        
        self.layout_iterations += 1
        
        # 力参数
        k = 0.01  # 弹簧常数
        repulsion = 5000  # 排斥力
        cooling = 1.0 - self.layout_iterations / self.max_layout_iterations
        
        # 计算排斥力
        forces = {org_id: QPointF(0, 0) for org_id in self.nodes}
        
        for id1, node1 in self.nodes.items():
            for id2, node2 in self.nodes.items():
                if id1 == id2:
                    continue
                
                dx = node1.pos().x() - node2.pos().x()
                dy = node1.pos().y() - node2.pos().y()
                dist = math.sqrt(dx*dx + dy*dy) + 1
                
                # 排斥力
                force = repulsion / (dist * dist)
                forces[id1] += QPointF(dx/dist * force, dy/dist * force)
        
        # 计算弹簧力（连线）
        for edge in self.edges:
            node1 = edge.node1
            node2 = edge.node2
            
            dx = node2.pos().x() - node1.pos().x()
            dy = node2.pos().y() - node1.pos().y()
            dist = math.sqrt(dx*dx + dy*dy)
            
            # 弹簧力（理想距离）
            ideal_dist = 150 + edge.rel_data.get('strength', 5) * 10
            force = k * (dist - ideal_dist)
            
            # 根据关系强度调整
            strength_factor = edge.rel_data.get('strength', 5) / 5
            force *= strength_factor
            
            id1 = node1.org_data['id']
            id2 = node2.org_data['id']
            
            forces[id1] += QPointF(dx/dist * force * cooling, dy/dist * force * cooling)
            forces[id2] -= QPointF(dx/dist * force * cooling, dy/dist * force * cooling)
        
        # 应用力
        for org_id, force in forces.items():
            node = self.nodes[org_id]
            new_pos = node.pos() + force * cooling * 0.5
            
            # 边界限制
            margin = 50
            new_x = max(margin, min(self.width() - margin, new_pos.x()))
            new_y = max(margin, min(self.height() - margin, new_pos.y()))
            
            node.setPos(new_x, new_y)
    
    def wheelEvent(self, event):
        """滚轮缩放"""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1/1.15
        
        new_scale = self.scale_factor * factor
        if 0.2 <= new_scale <= 3.0:
            self.scale_factor = new_scale
            self.scale(factor, factor)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件"""
        item = self.itemAt(event.pos())
        if isinstance(item, OrgNodeItem):
            self.org_double_clicked.emit(item.org_data['id'])
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        """右键菜单"""
        item = self.itemAt(event.pos())
        if isinstance(item, OrgNodeItem):
            self.org_right_clicked.emit(item.org_data['id'], event.globalPos())
        elif isinstance(item, RelationEdgeItem):
            self.relation_clicked.emit(item.rel_data['id'])
        super().contextMenuEvent(event)
    
    def export_image(self, file_path):
        """导出为图片"""
        from PySide6.QtGui import QImage, QPainter
        
        rect = self.scene.sceneRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(QColor("#1E293B"))
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene.render(painter)
        painter.end()
        
        image.save(file_path)


class OrgRelationGraphPanel(QWidget):
    """势力关系图面板"""
    
    org_selected = Signal(int)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        
        self.init_ui()
        self.load_time_range()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 顶部控制栏
        control_bar = QHBoxLayout()
        
        # 时间切片标签
        time_label = QLabel("时间切片:")
        time_label.setStyleSheet("color: #E5E7EB; font-weight: bold;")
        control_bar.addWidget(time_label)
        
        # 时间滑动条
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.setValue(100)
        self.time_slider.setTickPosition(QSlider.TicksBelow)
        self.time_slider.setTickInterval(10)
        self.time_slider.valueChanged.connect(self.on_time_slider_changed)
        control_bar.addWidget(self.time_slider)
        
        # 当前时间显示
        self.time_display = QLabel("全部时间")
        self.time_display.setStyleSheet("color: #E5E7EB; min-width: 120px;")
        control_bar.addWidget(self.time_display)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_graph)
        control_bar.addWidget(refresh_btn)
        
        # 导出按钮
        export_btn = QPushButton("📷 导出图片")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: white;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #7C3AED;
            }
        """)
        export_btn.clicked.connect(self.export_image)
        control_bar.addWidget(export_btn)
        
        layout.addLayout(control_bar)
        
        # 关系图视图
        self.graph_view = OrgRelationGraphView(self.db)
        self.graph_view.org_double_clicked.connect(self.on_org_double_clicked)
        self.graph_view.org_right_clicked.connect(self.on_org_right_clicked)
        self.graph_view.relation_clicked.connect(self.on_relation_clicked)
        layout.addWidget(self.graph_view)
        
        # 时间范围
        self.min_time = 0
        self.max_time = 1000000
    
    def load_time_range(self):
        """加载时间范围"""
        # 从事件表获取时间范围
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM events')
            row = cursor.fetchone()
            if row and row[0] and row[1]:
                self.min_time = parse_time_to_value(row[0])
                self.max_time = parse_time_to_value(row[1])
                
                # 更新滑动条范围
                if self.max_time > self.min_time:
                    self.time_slider.setMinimum(0)
                    self.time_slider.setMaximum(100)
    
    def on_time_slider_changed(self, value):
        """时间滑动条变化"""
        if value == 100:
            self.time_display.setText("全部时间")
            self.graph_view.load_graph_data(None)
        else:
            # 计算实际时间值
            time_value = self.min_time + (self.max_time - self.min_time) * value / 100
            
            # 格式化显示
            year = time_value // 10000
            month = (time_value % 10000) // 100
            day = time_value % 100
            self.time_display.setText(f"第{year}年{month}月{day}日")
            
            self.graph_view.load_graph_data(time_value)
    
    def set_time_from_timestamp(self, timestamp_str):
        """根据时间字符串设置当前时间并刷新关系图"""
        time_value = parse_time_to_value(timestamp_str)
        if time_value == 0:
            return
        
        # 确保时间范围已加载
        if self.max_time <= self.min_time:
            self.load_time_range()
        
        if self.max_time > self.min_time:
            # 计算滑动条位置
            slider_value = int((time_value - self.min_time) / (self.max_time - self.min_time) * 100)
            slider_value = max(0, min(100, slider_value))
            self.time_slider.setValue(slider_value)
            # on_time_slider_changed 会自动触发刷新
        else:
            # 时间范围无效，直接显示该时间
            year = time_value // 10000
            month = (time_value % 10000) // 100
            day = time_value % 100
            self.time_display.setText(f"第{year}年{month}月{day}日")
            self.graph_view.load_graph_data(time_value)
    
    def refresh_graph(self):
        """刷新关系图"""
        self.load_time_range()
        self.graph_view.load_graph_data()
    
    def on_org_double_clicked(self, org_id):
        """双击组织"""
        self.org_selected.emit(org_id)
    
    def on_org_right_clicked(self, org_id, pos):
        """右键组织"""
        menu = QMenu()
        
        view_chars_action = menu.addAction("查看该组织所有人物")
        view_chars_action.triggered.connect(lambda: self.view_org_characters(org_id))
        
        add_relation_action = menu.addAction("添加关系...")
        add_relation_action.triggered.connect(lambda: self.add_relation(org_id))
        
        menu.exec_(pos)
    
    def on_relation_clicked(self, rel_id):
        """点击关系线"""
        from dialogs import EditRelationDialog
        dialog = EditRelationDialog(self.db, rel_id, self)
        if dialog.exec() == EditRelationDialog.Accepted:
            self.refresh_graph()
    
    def view_org_characters(self, org_id):
        """查看组织人物"""
        chars = self.db.get_characters_by_organization(org_id)
        org = self.db.get_organization(org_id)
        
        if chars:
            msg = f"【{org['name']}】成员列表:\n\n"
            for ch in chars:
                msg += f"• {ch['name']}\n"
            QMessageBox.information(self, "组织成员", msg)
        else:
            QMessageBox.information(self, "组织成员", f"【{org['name']}】暂无成员")
    
    def add_relation(self, org_id):
        """添加关系"""
        from dialogs import AddRelationDialog
        dialog = AddRelationDialog(self.db, org_id, self)
        if dialog.exec() == AddRelationDialog.Accepted:
            self.refresh_graph()
    
    def export_image(self):
        """导出图片"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出关系图", "", "PNG图片 (*.png);;SVG图片 (*.svg)"
        )
        if file_path:
            self.graph_view.export_image(file_path)
            QMessageBox.information(self, "导出成功", f"关系图已保存到:\n{file_path}")