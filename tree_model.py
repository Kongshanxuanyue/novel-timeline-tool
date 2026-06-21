"""树模型模块"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QStandardItemModel, QStandardItem


class OrgTreeModel(QStandardItemModel):
    """组织树模型"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setHorizontalHeaderLabels(['组织与人物'])
        self.load_data()

    def load_data(self):
        self.clear()
        self.setHorizontalHeaderLabels(['组织与人物'])

        orgs = self.db.get_all_organizations()
        for org in orgs:
            org_item = QStandardItem(f"🏛️ {org['name']}")
            org_item.setForeground(QColor(org.get('color', '#8B5CF6')))
            org_item.setData({'type': 'org', 'id': org['id'], 'name': org['name']}, Qt.UserRole)
            org_item.setEditable(False)

            chars = self.db.get_characters_by_organization(org['id'])
            for ch in chars:
                char_item = QStandardItem(f"👤 {ch['name']}")
                char_item.setForeground(QColor(ch.get('color', '#10B981')))
                char_item.setData({'type': 'char', 'id': ch['id'], 'name': ch['name']}, Qt.UserRole)
                char_item.setEditable(False)
                
                # 添加该人物的事件作为子节点
                events = self.db.get_events_by_character(ch['id'])
                for ev in events:
                    event_item = QStandardItem(f"📍 {ev['title']}")
                    event_item.setForeground(QColor(ev.get('color', '#6B7280')))
                    event_item.setData({'type': 'event', 'id': ev['id'], 'name': ev['title'], 'char_id': ch['id']}, Qt.UserRole)
                    event_item.setEditable(False)
                    char_item.appendRow(event_item)
                
                org_item.appendRow(char_item)

            self.appendRow(org_item)

        no_org_chars = []
        all_chars = self.db.get_all_characters()
        for ch in all_chars:
            org_id = ch.get('organization_id')
            if org_id is None or org_id == 0:
                no_org_chars.append(ch)

        if no_org_chars:
            no_org_item = QStandardItem("🏛️ 无组织人物")
            no_org_item.setForeground(QColor('#6B7280'))
            no_org_item.setData({'type': 'org', 'id': 0, 'name': '无组织人物'}, Qt.UserRole)
            no_org_item.setEditable(False)

            for ch in no_org_chars:
                char_item = QStandardItem(f"👤 {ch['name']}")
                char_item.setForeground(QColor(ch.get('color', '#10B981')))
                char_item.setData({'type': 'char', 'id': ch['id'], 'name': ch['name']}, Qt.UserRole)
                char_item.setEditable(False)
                
                # 添加该人物的事件作为子节点
                events = self.db.get_events_by_character(ch['id'])
                for ev in events:
                    event_item = QStandardItem(f"📍 {ev['title']}")
                    event_item.setForeground(QColor(ev.get('color', '#6B7280')))
                    event_item.setData({'type': 'event', 'id': ev['id'], 'name': ev['title'], 'char_id': ch['id']}, Qt.UserRole)
                    event_item.setEditable(False)
                    char_item.appendRow(event_item)
                
                no_org_item.appendRow(char_item)

            self.appendRow(no_org_item)

    def refresh(self):
        self.load_data()