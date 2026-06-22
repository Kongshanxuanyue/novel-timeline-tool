import sqlite3
import os
import json
import time
import re

from PySide6.QtGui import QColor


def parse_time_to_value(time_str):
    """将年月日格式字符串转换为数值用于时间轴排序"""
    if not time_str:
        return 0
    # 如果是数值类型，直接返回
    if isinstance(time_str, (int, float)):
        return int(time_str * 10000) if time_str < 10000 else int(time_str)
    # 匹配格式: 第N年M月D日 或 N年M月D日
    match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(time_str))
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return year * 10000 + month * 100 + day
    return 0


def format_time_label(time_str):
    """格式化时间标签显示"""
    if not time_str:
        return ""
    # 匹配格式: 第N年M月D日 或 N年M月D日
    match = re.match(r'第?(\d+)年(\d+)月(\d+)日', time_str)
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3)
        return f"第{year}年{month}月{day}日"
    return time_str


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # 使用本地项目目录存储数据库
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(script_dir, "timeline.db")
        else:
            self.db_path = db_path

        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")  # 启用外键约束
        conn.row_factory = sqlite3.Row            # 返回字典字典型数据
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1.1 组织表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES organizations(id) ON DELETE SET NULL
            )''')

            # 1.2 人物表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                alias TEXT,
                description TEXT,
                organization_id INTEGER,
                color TEXT,
                birth_time TEXT,
                death_time TEXT,
                biography TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
            )''')

            # 迁移旧表：添加 birth_time 和 death_time 字段
            try:
                cursor.execute("ALTER TABLE characters ADD COLUMN birth_time TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE characters ADD COLUMN death_time TEXT;")
            except sqlite3.OperationalError:
                pass

            # 1.3 人物内核表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_cores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                core_name TEXT NOT NULL,
                core_value TEXT,
                start_time REAL NOT NULL,
                end_time REAL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )''')

            # 1.4 事件表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                type INTEGER DEFAULT 0,
                color TEXT DEFAULT '#10B981',
                tags TEXT,
                core_changes TEXT,
                is_public INTEGER DEFAULT 1,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )''')

            # 迁移旧表：添加 color 字段
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN color TEXT DEFAULT '#10B981';")
            except sqlite3.OperationalError:
                pass

            # 迁移旧表：添加章节相关字段
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN chapter_number INTEGER;")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN chapter_title TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN writing_status INTEGER DEFAULT 0;")
            except sqlite3.OperationalError:
                pass

            # 1.5 章节表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER UNIQUE NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                word_count INTEGER DEFAULT 0,
                status INTEGER DEFAULT 0,
                start_event_id INTEGER,
                end_event_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (start_event_id) REFERENCES events(id) ON DELETE SET NULL,
                FOREIGN KEY (end_event_id) REFERENCES events(id) ON DELETE SET NULL
            )''')

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_number ON chapters(number);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_chapter ON events(chapter_number);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(writing_status);")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_character ON events(character_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_org ON characters(organization_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cores_character ON character_cores(character_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cores_time ON character_cores(start_time, end_time);")

            # 1.6 关系类型表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationship_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                line_style TEXT NOT NULL DEFAULT 'solid'
            )''')
            
            # 1.7 组织关系表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS organization_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org1_id INTEGER NOT NULL,
                org2_id INTEGER NOT NULL,
                relationship_type_id INTEGER NOT NULL,
                strength INTEGER DEFAULT 5,
                start_time TEXT,
                end_time TEXT,
                description TEXT,
                FOREIGN KEY (org1_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (org2_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (relationship_type_id) REFERENCES relationship_types(id) ON DELETE CASCADE
            )''')
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_org_rel_org1 ON organization_relationships(org1_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_org_rel_org2 ON organization_relationships(org2_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_org_rel_type ON organization_relationships(relationship_type_id);")
            
            # 插入默认关系类型
            default_types = [
                ("同盟", "#10B981", "solid"),
                ("敌对", "#EF4444", "solid"),
                ("附属", "#3B82F6", "dashed"),
                ("中立", "#9CA3AF", "dotted"),
                ("联姻", "#F59E0B", "solid"),
            ]
            cursor.execute("SELECT COUNT(*) FROM relationship_types")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO relationship_types (name, color, line_style) VALUES (?, ?, ?)",
                    default_types
                )
            
            # 1.8 角色关系类型表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_relationship_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                bidirectional INTEGER DEFAULT 0
            )''')
            
            # 1.9 角色关系表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char1_id INTEGER NOT NULL,
                char2_id INTEGER NOT NULL,
                relationship_type_id INTEGER NOT NULL,
                strength INTEGER DEFAULT 5,
                description TEXT,
                start_event_id INTEGER,
                FOREIGN KEY (char1_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (char2_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (relationship_type_id) REFERENCES character_relationship_types(id) ON DELETE CASCADE
            )''')
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_char_rel_char1 ON character_relationships(char1_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_char_rel_char2 ON character_relationships(char2_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_char_rel_type ON character_relationships(relationship_type_id);")
            
            # 插入默认角色关系类型
            default_char_types = [
                ("师徒", "#8B5CF6", 1),
                ("恋人", "#EF4444", 1),
                ("仇敌", "#DC2626", 1),
                ("亲属", "#F59E0B", 1),
                ("盟友", "#10B981", 1),
                ("上下级", "#3B82F6", 0),
            ]
            cursor.execute("SELECT COUNT(*) FROM character_relationship_types")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO character_relationship_types (name, color, bidirectional) VALUES (?, ?, ?)",
                    default_char_types
                )
            
            # 1.10 情节线索表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category INTEGER DEFAULT 0,
                status INTEGER DEFAULT 0,
                importance INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )''')
            
            # 1.11 线索-事件关联表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_thread_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                relation_type INTEGER DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (thread_id) REFERENCES plot_threads(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )''')
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plot_thread_status ON plot_threads(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plot_thread_category ON plot_threads(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plot_thread_events_thread ON plot_thread_events(thread_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plot_thread_events_event ON plot_thread_events(event_id);")
            
            # 1.12 灵感表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS inspirations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category INTEGER DEFAULT 0,
                tags TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_used INTEGER DEFAULT 0,
                related_event_id INTEGER,
                embedding BLOB,
                FOREIGN KEY (related_event_id) REFERENCES events(id) ON DELETE SET NULL
            )''')
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspiration_category ON inspirations(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspiration_is_used ON inspirations(is_used);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspiration_event ON inspirations(related_event_id);")
            
            # 1.13 事件组表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#8B5CF6',
                status INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # 1.14 事件组-事件关联表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_group_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                order_index INTEGER DEFAULT 0,
                relation_type INTEGER DEFAULT 0,
                FOREIGN KEY (group_id) REFERENCES event_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )''')
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_groups_status ON event_groups(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_group_events_group ON event_group_events(group_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_group_events_event ON event_group_events(event_id);")
            
            # FTS5 全文检索虚表（若 SQLite 支持）
            try:
                cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(title, content);")
            except sqlite3.OperationalError:
                pass # 兼容部分未编译 FTS5 的精简版环境
            
            # 2.4 自动化机制：通过触发器或应用层控制。
            # 这里创建 SQLite 触发器：当事件新增时，自动在对应人物的小传追加记录
            cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS trig_append_biography_on_event_insert
            AFTER INSERT ON events
            BEGIN
                UPDATE characters 
                SET biography = biography || printf('\n【时间: %f】%s：%s', NEW.timestamp, NEW.title, COALESCE(NEW.content, ''))
                WHERE id = NEW.character_id;
            END;
            ''')
            
            conn.commit()

    # --- 高效分页查询逻辑 ---
    def get_character_events_page(self, character_id, page=1, per_page=200):
        """分页获取单人物事件，防内存撑爆"""
        offset = (page - 1) * per_page
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events 
                WHERE character_id = ? 
                ORDER BY timestamp ASC 
                LIMIT ? OFFSET ?
            ''', (character_id, per_page, offset))
            return [dict(row) for row in cursor.fetchall()]

    def create_character(self, name, alias=None, description=None, organization_id=None, color=None, birth_time=None, death_time=None):
        """创建新人物"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO characters (name, alias, description, organization_id, color, birth_time, death_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, alias, description, organization_id, color, birth_time, death_time))
            conn.commit()
            return cursor.lastrowid

    def update_character_times(self, character_id, birth_time=None, death_time=None):
        """更新人物的出生/死亡时间"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE characters SET birth_time = ?, death_time = ? WHERE id = ?
            ''', (birth_time, death_time, character_id))
            conn.commit()
            return cursor.rowcount

    def create_event(self, character_id, timestamp, title, content=None, type=0, color=None, tags=None, core_changes=None, is_public=1):
        """创建时间事件节点"""
        core_changes_json = json.dumps(core_changes) if core_changes else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (character_id, timestamp, title, content, type, color, tags, core_changes, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (character_id, timestamp, title, content, type, color, tags, core_changes_json, is_public))
            conn.commit()
            return cursor.lastrowid

    def get_all_characters(self):
        """获取所有人物列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, alias, color, description, organization_id, birth_time, death_time FROM characters ORDER BY created_at ASC')
            return [dict(row) for row in cursor.fetchall()]

    def get_character(self, character_id):
        """获取单个人物信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
            ch = cursor.fetchone()
            return dict(ch) if ch else None

    def get_character_by_name(self, name):
        """根据名称获取人物信息"""
        if not name:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM characters WHERE name = ? LIMIT 1', (name,))
            ch = cursor.fetchone()
            return dict(ch) if ch else None

    def get_character_with_events(self, character_id):
        """获取人物及其所有事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
            ch = cursor.fetchone()
            if not ch:
                return None
            ch_dict = dict(ch)
            
            cursor.execute('SELECT * FROM events WHERE character_id = ? ORDER BY timestamp ASC', (character_id,))
            ch_dict['events'] = [dict(row) for row in cursor.fetchall()]
            return ch_dict

    def delete_character(self, character_id):
        """删除人物及其关联的所有事件（外键级联删除）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM characters WHERE id = ?', (character_id,))
            conn.commit()
            return cursor.rowcount

    def delete_event(self, event_id):
        """删除单个事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
            conn.commit()
            return cursor.rowcount

    def update_event(self, event_id, title=None, timestamp=None, content=None, type=None, color=None, tags=None, core_changes=None, is_public=None):
        """更新事件"""
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if timestamp is not None:
            updates.append("timestamp = ?")
            params.append(timestamp)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if type is not None:
            updates.append("type = ?")
            params.append(type)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)
        if core_changes is not None:
            updates.append("core_changes = ?")
            params.append(core_changes)
        if is_public is not None:
            updates.append("is_public = ?")
            params.append(is_public)

        if not updates:
            return 0

        params.append(event_id)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return cursor.rowcount

    def update_character(self, character_id, name=None, alias=None, description=None, organization_id=None, color=None, birth_time=None, death_time=None):
        """更新人物"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if alias is not None:
            updates.append("alias = ?")
            params.append(alias)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if organization_id is not None:
            updates.append("organization_id = ?")
            params.append(organization_id)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if birth_time is not None:
            updates.append("birth_time = ?")
            params.append(birth_time)
        if death_time is not None:
            updates.append("death_time = ?")
            params.append(death_time)

        if not updates:
            return 0

        params.append(character_id)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE characters SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return cursor.rowcount

    def get_events_by_character(self, character_id):
        """获取某人物的所有事件（用于删除选择）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, timestamp, title, type FROM events WHERE character_id = ? ORDER BY timestamp ASC',
                (character_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_event_by_title_and_character(self, title, character_id, timestamp=None):
        """根据标题和人物ID查找事件，可选匹配时间戳"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if timestamp:
                cursor.execute(
                    'SELECT * FROM events WHERE title = ? AND character_id = ? AND timestamp = ? LIMIT 1',
                    (title, character_id, timestamp)
                )
            else:
                cursor.execute(
                    'SELECT * FROM events WHERE title = ? AND character_id = ? LIMIT 1',
                    (title, character_id)
                )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_events(self):
        """获取所有事件（包含人物名称和组织ID）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.id, e.timestamp, e.title, e.character_id,
                       c.name as character_name, c.organization_id
                FROM events e
                LEFT JOIN characters c ON e.character_id = c.id
                ORDER BY e.timestamp ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def get_event(self, event_id):
        """获取单个事件（包含人物名称和组织ID）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.*, c.name as character_name, c.organization_id
                FROM events e
                LEFT JOIN characters c ON e.character_id = c.id
                WHERE e.id = ?
            ''', (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== 组织管理 ====================
    def create_organization(self, name, description=None, color=None, parent_id=None):
        """创建组织"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO organizations (name, description, color, parent_id)
                VALUES (?, ?, ?, ?)
            ''', (name, description, color, parent_id))
            conn.commit()
            return cursor.lastrowid

    def get_all_organizations(self):
        """获取所有组织列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, description, color, parent_id FROM organizations ORDER BY name ASC')
            return [dict(row) for row in cursor.fetchall()]

    def get_organization(self, org_id):
        """获取单个组织"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM organizations WHERE id = ?', (org_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_organization_by_name(self, name):
        """根据名称获取组织"""
        if not name:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM organizations WHERE name = ? LIMIT 1', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_organization(self, org_id, name=None, description=None, color=None, parent_id=None):
        """更新组织信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            if parent_id is not None:
                updates.append("parent_id = ?")
                params.append(parent_id)
            if updates:
                params.append(org_id)
                cursor.execute(f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
            return cursor.rowcount

    def delete_organization(self, org_id):
        """删除组织（关联人物的组织字段置空）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
            conn.commit()
            return cursor.rowcount

    def get_characters_by_organization(self, org_id):
        """获取指定组织的所有人物"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, name, alias, color FROM characters WHERE organization_id = ? ORDER BY created_at ASC',
                (org_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_character_color_from_organization(self, character_id, index_in_org=0):
        """根据人物在组织中的索引，计算颜色（从深到浅渐变）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT organization_id FROM characters WHERE id = ?', (character_id,))
            row = cursor.fetchone()
            if not row or not row['organization_id']:
                return None

            org_id = row['organization_id']
            cursor.execute('SELECT color FROM organizations WHERE id = ?', (org_id,))
            org_row = cursor.fetchone()
            if not org_row or not org_row['color']:
                return None

            org_color = QColor(org_row['color'])
            # 计算浅色变体
            from PySide6.QtGui import QColor
            h, s, l, a = org_color.hslHsl()
            # 逐渐增加亮度，减少饱和度
            lightness = min(95, 50 + index_in_org * 10)
            saturation = max(20, 70 - index_in_org * 10)
            lighter_color = QColor.fromHsl(h, saturation, lightness, a)
            return lighter_color.name()

    # ==================== 章节管理 ====================
    def create_chapter(self, number, title, summary=None, word_count=0, status=0, start_event_id=None, end_event_id=None):
        """创建章节"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chapters (number, title, summary, word_count, status, start_event_id, end_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (number, title, summary, word_count, status, start_event_id, end_event_id))
            conn.commit()
            return cursor.lastrowid

    def get_all_chapters(self):
        """获取所有章节列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chapters ORDER BY number ASC')
            return [dict(row) for row in cursor.fetchall()]

    def get_chapter(self, chapter_id):
        """获取单个章节"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chapters WHERE id = ?', (chapter_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_chapter_by_number(self, number):
        """根据章节号获取章节"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chapters WHERE number = ?', (number,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_chapter(self, chapter_id, number=None, title=None, summary=None, word_count=None, status=None, start_event_id=None, end_event_id=None):
        """更新章节"""
        updates = []
        params = []
        if number is not None:
            updates.append("number = ?")
            params.append(number)
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        if word_count is not None:
            updates.append("word_count = ?")
            params.append(word_count)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if start_event_id is not None:
            updates.append("start_event_id = ?")
            params.append(start_event_id)
        if end_event_id is not None:
            updates.append("end_event_id = ?")
            params.append(end_event_id)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(chapter_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE chapters SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0

    def delete_chapter(self, chapter_id):
        """删除章节"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 先解除该章节下所有事件的绑定
            chapter = self.get_chapter(chapter_id)
            if chapter:
                cursor.execute('UPDATE events SET chapter_number = NULL, chapter_title = NULL WHERE chapter_number = ?', (chapter['number'],))
            cursor.execute('DELETE FROM chapters WHERE id = ?', (chapter_id,))
            conn.commit()
            return cursor.rowcount

    def get_events_by_chapter(self, chapter_number):
        """获取指定章节的所有事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.*, c.name as character_name 
                FROM events e 
                LEFT JOIN characters c ON e.character_id = c.id 
                WHERE e.chapter_number = ? 
                ORDER BY e.timestamp ASC
            ''', (chapter_number,))
            return [dict(row) for row in cursor.fetchall()]

    def bind_event_to_chapter(self, event_id, chapter_number, chapter_title=None):
        """将事件绑定到章节"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if chapter_title is None:
                chapter = self.get_chapter_by_number(chapter_number)
                chapter_title = chapter['title'] if chapter else None
            cursor.execute('''
                UPDATE events SET chapter_number = ?, chapter_title = ? WHERE id = ?
            ''', (chapter_number, chapter_title, event_id))
            conn.commit()
            return cursor.rowcount

    def unbind_event_from_chapter(self, event_id):
        """解除事件与章节的绑定"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE events SET chapter_number = NULL, chapter_title = NULL WHERE id = ?', (event_id,))
            conn.commit()
            return cursor.rowcount

    def update_event_writing_status(self, event_id, status):
        """更新事件的写作状态"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE events SET writing_status = ? WHERE id = ?', (status, event_id))
            conn.commit()
            return cursor.rowcount

    def get_next_chapter_number(self):
        """获取下一个章节编号"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(number) FROM chapters')
            row = cursor.fetchone()
            return (row[0] or 0) + 1

    def get_chapter_time_range(self, chapter_number):
        """获取章节覆盖的时间范围"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MIN(timestamp) as start_time, MAX(timestamp) as end_time 
                FROM events WHERE chapter_number = ?
            ''', (chapter_number,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== 关系类型管理 ====================
    def get_all_relationship_types(self):
        """获取所有关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM relationship_types ORDER BY id ASC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_relationship_type(self, type_id):
        """获取单个关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM relationship_types WHERE id = ?', (type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_relationship_type(self, name, color, line_style='solid'):
        """创建关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO relationship_types (name, color, line_style)
                VALUES (?, ?, ?)
            ''', (name, color, line_style))
            conn.commit()
            return cursor.lastrowid
    
    def update_relationship_type(self, type_id, name=None, color=None, line_style=None):
        """更新关系类型"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if line_style is not None:
            updates.append("line_style = ?")
            params.append(line_style)
        
        if updates:
            params.append(type_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE relationship_types SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_relationship_type(self, type_id):
        """删除关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM relationship_types WHERE id = ?', (type_id,))
            conn.commit()
            return cursor.rowcount
    
    # ==================== 组织关系管理 ====================
    def create_org_relationship(self, org1_id, org2_id, relationship_type_id, strength=5, start_time=None, end_time=None, description=None):
        """创建组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO organization_relationships (org1_id, org2_id, relationship_type_id, strength, start_time, end_time, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (org1_id, org2_id, relationship_type_id, strength, start_time, end_time, description))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_org_relationships(self):
        """获取所有组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, 
                       o1.name as org1_name, o1.color as org1_color,
                       o2.name as org2_name, o2.color as org2_color,
                       rt.name as relationship_name, rt.color as relationship_color, rt.line_style
                FROM organization_relationships r
                LEFT JOIN organizations o1 ON r.org1_id = o1.id
                LEFT JOIN organizations o2 ON r.org2_id = o2.id
                LEFT JOIN relationship_types rt ON r.relationship_type_id = rt.id
                ORDER BY r.id ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_org_relationships_by_org(self, org_id):
        """获取指定组织的所有关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, 
                       o1.name as org1_name, o1.color as org1_color,
                       o2.name as org2_name, o2.color as org2_color,
                       rt.name as relationship_name, rt.color as relationship_color, rt.line_style
                FROM organization_relationships r
                LEFT JOIN organizations o1 ON r.org1_id = o1.id
                LEFT JOIN organizations o2 ON r.org2_id = o2.id
                LEFT JOIN relationship_types rt ON r.relationship_type_id = rt.id
                WHERE r.org1_id = ? OR r.org2_id = ?
                ORDER BY r.id ASC
            ''', (org_id, org_id))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_org_relationship(self, rel_id):
        """获取单个组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, 
                       o1.name as org1_name, o1.color as org1_color,
                       o2.name as org2_name, o2.color as org2_color,
                       rt.name as relationship_name, rt.color as relationship_color, rt.line_style
                FROM organization_relationships r
                LEFT JOIN organizations o1 ON r.org1_id = o1.id
                LEFT JOIN organizations o2 ON r.org2_id = o2.id
                LEFT JOIN relationship_types rt ON r.relationship_type_id = rt.id
                WHERE r.id = ?
            ''', (rel_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_org_relationship(self, rel_id, org1_id=None, org2_id=None, relationship_type_id=None, strength=None, start_time=None, end_time=None, description=None):
        """更新组织关系"""
        updates = []
        params = []
        if org1_id is not None:
            updates.append("org1_id = ?")
            params.append(org1_id)
        if org2_id is not None:
            updates.append("org2_id = ?")
            params.append(org2_id)
        if relationship_type_id is not None:
            updates.append("relationship_type_id = ?")
            params.append(relationship_type_id)
        if strength is not None:
            updates.append("strength = ?")
            params.append(strength)
        if start_time is not None:
            updates.append("start_time = ?")
            params.append(start_time)
        if end_time is not None:
            updates.append("end_time = ?")
            params.append(end_time)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if updates:
            params.append(rel_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE organization_relationships SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_org_relationship(self, rel_id):
        """删除组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM organization_relationships WHERE id = ?', (rel_id,))
            conn.commit()
    
    def create_organization_relationship(self, org1_id, org2_id, relationship_type_id, strength=5, start_time=None, end_time=None, description=None):
        """创建组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO organization_relationships (org1_id, org2_id, relationship_type_id, strength, start_time, end_time, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (org1_id, org2_id, relationship_type_id, strength, start_time, end_time, description))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_organization_relationships(self):
        """获取所有组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*
                FROM organization_relationships r
                ORDER BY r.id ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_org_relationships_at_time(self, time_value):
        """获取指定时间点有效的组织关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*,
                       o1.name as org1_name, o1.color as org1_color,
                       o2.name as org2_name, o2.color as org2_color,
                       rt.name as relationship_name, rt.color as relationship_color, rt.line_style
                FROM organization_relationships r
                LEFT JOIN organizations o1 ON r.org1_id = o1.id
                LEFT JOIN organizations o2 ON r.org2_id = o2.id
                LEFT JOIN relationship_types rt ON r.relationship_type_id = rt.id
                ORDER BY r.id ASC
            ''')
            all_rels = [dict(row) for row in cursor.fetchall()]
            # Python端时间过滤
            result = []
            for rel in all_rels:
                start = parse_time_to_value(rel.get('start_time'))
                end = parse_time_to_value(rel.get('end_time'))
                if (start == 0 or start <= time_value) and (end == 0 or end >= time_value):
                    result.append(rel)
            return result
    
    def get_org_member_count(self, org_id):
        """获取组织成员数量"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM characters WHERE organization_id = ?', (org_id,))
            return cursor.fetchone()[0]
    
    def get_org_key_characters(self, org_id, limit=5):
        """获取组织关键人物（按事件数量排序）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.id, c.name, c.color, COUNT(e.id) as event_count
                FROM characters c
                LEFT JOIN events e ON c.id = e.character_id
                WHERE c.organization_id = ?
                GROUP BY c.id
                ORDER BY event_count DESC
                LIMIT ?
            ''', (org_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_org_relationship_summary(self, org_id):
        """获取组织关系摘要"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT rt.name, COUNT(*) as count
                FROM organization_relationships r
                LEFT JOIN relationship_types rt ON r.relationship_type_id = rt.id
                WHERE r.org1_id = ? OR r.org2_id = ?
                GROUP BY rt.id
            ''', (org_id, org_id))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 角色关系管理 ====================
    def get_all_character_relationship_types(self):
        """获取所有角色关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM character_relationship_types ORDER BY id ASC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_character_relationship_type(self, type_id):
        """获取单个角色关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM character_relationship_types WHERE id = ?', (type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_character_relationship_type(self, name, color, bidirectional=0):
        """创建角色关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO character_relationship_types (name, color, bidirectional)
                VALUES (?, ?, ?)
            ''', (name, color, bidirectional))
            conn.commit()
            return cursor.lastrowid
    
    def update_character_relationship_type(self, type_id, name=None, color=None, bidirectional=None):
        """更新角色关系类型"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if bidirectional is not None:
            updates.append("bidirectional = ?")
            params.append(bidirectional)
        
        if updates:
            params.append(type_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE character_relationship_types SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_character_relationship_type(self, type_id):
        """删除角色关系类型"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM character_relationship_types WHERE id = ?', (type_id,))
            conn.commit()
            return cursor.rowcount
    
    def create_character_relationship(self, char1_id, char2_id, relationship_type_id, strength=5, description=None, start_event_id=None):
        """创建角色关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO character_relationships (char1_id, char2_id, relationship_type_id, strength, description, start_event_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (char1_id, char2_id, relationship_type_id, strength, description, start_event_id))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_character_relationships(self):
        """获取所有角色关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*,
                       c1.name as char1_name, c1.color as char1_color, c1.organization_id as char1_org_id,
                       c2.name as char2_name, c2.color as char2_color, c2.organization_id as char2_org_id,
                       rt.name as relationship_name, rt.color as relationship_color, rt.bidirectional,
                       e.title as start_event_title
                FROM character_relationships r
                LEFT JOIN characters c1 ON r.char1_id = c1.id
                LEFT JOIN characters c2 ON r.char2_id = c2.id
                LEFT JOIN character_relationship_types rt ON r.relationship_type_id = rt.id
                LEFT JOIN events e ON r.start_event_id = e.id
                ORDER BY r.id ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_character_relationships_by_character(self, char_id):
        """获取指定角色的所有关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*,
                       c1.name as char1_name, c1.color as char1_color,
                       c2.name as char2_name, c2.color as char2_color,
                       rt.name as relationship_name, rt.color as relationship_color, rt.bidirectional,
                       e.title as start_event_title
                FROM character_relationships r
                LEFT JOIN characters c1 ON r.char1_id = c1.id
                LEFT JOIN characters c2 ON r.char2_id = c2.id
                LEFT JOIN character_relationship_types rt ON r.relationship_type_id = rt.id
                LEFT JOIN events e ON r.start_event_id = e.id
                WHERE r.char1_id = ? OR r.char2_id = ?
                ORDER BY r.id ASC
            ''', (char_id, char_id))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_character_relationship(self, rel_id):
        """获取单个角色关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*,
                       c1.name as char1_name, c1.color as char1_color,
                       c2.name as char2_name, c2.color as char2_color,
                       rt.name as relationship_name, rt.color as relationship_color, rt.bidirectional,
                       e.title as start_event_title
                FROM character_relationships r
                LEFT JOIN characters c1 ON r.char1_id = c1.id
                LEFT JOIN characters c2 ON r.char2_id = c2.id
                LEFT JOIN character_relationship_types rt ON r.relationship_type_id = rt.id
                LEFT JOIN events e ON r.start_event_id = e.id
                WHERE r.id = ?
            ''', (rel_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_character_relationship(self, rel_id, char1_id=None, char2_id=None, relationship_type_id=None,
                                       strength=None, description=None, start_event_id=None):
        """更新角色关系"""
        updates = []
        params = []
        if char1_id is not None:
            updates.append("char1_id = ?")
            params.append(char1_id)
        if char2_id is not None:
            updates.append("char2_id = ?")
            params.append(char2_id)
        if relationship_type_id is not None:
            updates.append("relationship_type_id = ?")
            params.append(relationship_type_id)
        if strength is not None:
            updates.append("strength = ?")
            params.append(strength)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if start_event_id is not None:
            updates.append("start_event_id = ?")
            params.append(start_event_id)
        
        if updates:
            params.append(rel_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE character_relationships SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_character_relationship(self, rel_id):
        """删除角色关系"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM character_relationships WHERE id = ?', (rel_id,))
            conn.commit()
            return cursor.rowcount
    
    def get_character_event_count(self, char_id):
        """获取角色事件数量"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM events WHERE character_id = ?', (char_id,))
            return cursor.fetchone()[0]
    
    def check_relationship_conflict(self, char1_id, char2_id, relationship_type_id=None):
        """检查两个角色之间是否存在关系冲突（多种关系类型）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if relationship_type_id:
                cursor.execute('''
                    SELECT COUNT(*) FROM character_relationships
                    WHERE ((char1_id = ? AND char2_id = ?) OR (char1_id = ? AND char2_id = ?))
                    AND relationship_type_id != ?
                ''', (char1_id, char2_id, char2_id, char1_id, relationship_type_id))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM character_relationships
                    WHERE ((char1_id = ? AND char2_id = ?) OR (char1_id = ? AND char2_id = ?))
                ''', (char1_id, char2_id, char2_id, char1_id))
            return cursor.fetchone()[0]
    
    # ==================== 情节线索管理 ====================
    def create_plot_thread(self, name, description=None, category=0, status=0, importance=3):
        """创建情节线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO plot_threads (name, description, category, status, importance)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, category, status, importance))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_plot_threads(self):
        """获取所有情节线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM plot_threads ORDER BY importance DESC, created_at ASC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_plot_threads_by_status(self, status):
        """获取指定状态的线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM plot_threads WHERE status = ? ORDER BY importance DESC', (status,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_plot_thread(self, thread_id):
        """获取单个线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM plot_threads WHERE id = ?', (thread_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_plot_thread(self, thread_id, name=None, description=None, category=None, 
                           status=None, importance=None, resolved_at=None):
        """更新线索"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if resolved_at is not None:
            updates.append("resolved_at = ?")
            params.append(resolved_at)
        
        if updates:
            params.append(thread_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE plot_threads SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_plot_thread(self, thread_id):
        """删除线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM plot_threads WHERE id = ?', (thread_id,))
            conn.commit()
            return cursor.rowcount
    
    def link_event_to_thread(self, thread_id, event_id, relation_type=0, notes=None):
        """关联事件到线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO plot_thread_events (thread_id, event_id, relation_type, notes)
                VALUES (?, ?, ?, ?)
            ''', (thread_id, event_id, relation_type, notes))
            conn.commit()
            return cursor.lastrowid
    
    def unlink_event_from_thread(self, thread_id, event_id):
        """解除事件与线索的关联"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM plot_thread_events WHERE thread_id = ? AND event_id = ?', 
                          (thread_id, event_id))
            conn.commit()
            return cursor.rowcount
    
    def clear_thread_events(self, thread_id):
        """清除线索的所有事件关联"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM plot_thread_events WHERE thread_id = ?', (thread_id,))
            conn.commit()
            return cursor.rowcount
    
    def get_thread_events(self, thread_id):
        """获取线索关联的所有事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT te.*, e.timestamp, e.title, e.content, e.character_id, c.name as character_name
                FROM plot_thread_events te
                LEFT JOIN events e ON te.event_id = e.id
                LEFT JOIN characters c ON e.character_id = c.id
                WHERE te.thread_id = ?
                ORDER BY e.timestamp ASC
            ''', (thread_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_event_threads(self, event_id):
        """获取事件关联的所有线索"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pt.*, te.relation_type, te.notes
                FROM plot_thread_events te
                LEFT JOIN plot_threads pt ON te.thread_id = pt.id
                WHERE te.event_id = ?
            ''', (event_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_thread_event_count(self, thread_id):
        """获取线索关联事件数量"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM plot_thread_events WHERE thread_id = ?', (thread_id,))
            return cursor.fetchone()[0]
    
    def get_unresolved_threads_stats(self):
        """获取未回收线索统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 按重要性分组统计未回收线索
            cursor.execute('''
                SELECT importance, COUNT(*) as count
                FROM plot_threads
                WHERE status IN (0, 1, 2)
                GROUP BY importance
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_overdue_threads(self, threshold_events=10):
        """获取超期未回收的线索（埋设后超过threshold_events个事件仍未回收）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 获取已埋设但未回收的线索
            cursor.execute('''
                SELECT pt.*, 
                       (SELECT COUNT(*) FROM events e 
                        WHERE e.id NOT IN (SELECT event_id FROM plot_thread_events WHERE thread_id = pt.id AND relation_type = 2)
                        AND e.timestamp > (SELECT MIN(e2.timestamp) FROM plot_thread_events te2 
                                           JOIN events e2 ON te2.event_id = e2.id 
                                           WHERE te2.thread_id = pt.id AND te2.relation_type = 0)
                       ) as events_since_plant
                FROM plot_threads pt
                WHERE pt.status = 1
            ''')
            threads = [dict(row) for row in cursor.fetchall()]
            # 过滤超过阈值的
            return [t for t in threads if t.get('events_since_plant', 0) >= threshold_events]
    
    # ==================== 灵感管理 ====================
    def create_inspiration(self, content, category=0, tags=None, source=None, embedding=None):
        """创建灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO inspirations (content, category, tags, source, embedding)
                VALUES (?, ?, ?, ?, ?)
            ''', (content, category, tags, source, embedding))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_inspirations(self):
        """获取所有灵感（按时间倒序）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, e.title as event_title, e.timestamp as event_timestamp
                FROM inspirations i
                LEFT JOIN events e ON i.related_event_id = e.id
                ORDER BY i.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_inspirations_by_category(self, category):
        """获取指定类别的灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, e.title as event_title, e.timestamp as event_timestamp
                FROM inspirations i
                LEFT JOIN events e ON i.related_event_id = e.id
                WHERE i.category = ?
                ORDER BY i.created_at DESC
            ''', (category,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_inspirations_by_tag(self, tag):
        """获取包含指定标签的灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, e.title as event_title, e.timestamp as event_timestamp
                FROM inspirations i
                LEFT JOIN events e ON i.related_event_id = e.id
                WHERE i.tags LIKE ?
                ORDER BY i.created_at DESC
            ''', (f'%{tag}%',))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_inspiration(self, insp_id):
        """获取单个灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, e.title as event_title, e.timestamp as event_timestamp
                FROM inspirations i
                LEFT JOIN events e ON i.related_event_id = e.id
                WHERE i.id = ?
            ''', (insp_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_inspiration(self, insp_id, content=None, category=None, tags=None, 
                           source=None, is_used=None, related_event_id=None, embedding=None):
        """更新灵感"""
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)
        if source is not None:
            updates.append("source = ?")
            params.append(source)
        if is_used is not None:
            updates.append("is_used = ?")
            params.append(is_used)
        if related_event_id is not None:
            updates.append("related_event_id = ?")
            params.append(related_event_id)
        if embedding is not None:
            updates.append("embedding = ?")
            params.append(embedding)
        
        if updates:
            params.append(insp_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE inspirations SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_inspiration(self, insp_id):
        """删除灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM inspirations WHERE id = ?', (insp_id,))
            conn.commit()
            return cursor.rowcount
    
    def search_inspirations_keyword(self, keyword):
        """关键词搜索灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, e.title as event_title, e.timestamp as event_timestamp
                FROM inspirations i
                LEFT JOIN events e ON i.related_event_id = e.id
                WHERE i.content LIKE ? OR i.tags LIKE ? OR i.source LIKE ?
                ORDER BY i.created_at DESC
            ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_inspirations_with_embeddings(self):
        """获取所有有向量嵌入的灵感"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, e.title as event_title, e.timestamp as event_timestamp
                FROM inspirations i
                LEFT JOIN events e ON i.related_event_id = e.id
                WHERE i.embedding IS NOT NULL
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 事件组管理 ====================
    def create_event_group(self, name, description=None, color=None, status=0, progress=0):
        """创建事件组"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO event_groups (name, description, color, status, progress)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, color, status, progress))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_event_groups(self):
        """获取所有事件组"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM event_groups ORDER BY created_at ASC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_event_group(self, group_id):
        """获取单个事件组"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM event_groups WHERE id = ?', (group_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_event_group_with_events(self, group_id):
        """获取事件组及其关联的所有事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM event_groups WHERE id = ?', (group_id,))
            group = cursor.fetchone()
            if not group:
                return None
            group_dict = dict(group)
            
            cursor.execute('''
                SELECT e.*, eg.order_index, eg.relation_type, c.name as character_name
                FROM event_group_events eg
                LEFT JOIN events e ON eg.event_id = e.id
                LEFT JOIN characters c ON e.character_id = c.id
                WHERE eg.group_id = ?
                ORDER BY eg.order_index ASC, e.timestamp ASC
            ''', (group_id,))
            group_dict['events'] = [dict(row) for row in cursor.fetchall()]
            return group_dict
    
    def update_event_group(self, group_id, name=None, description=None, color=None, 
                          status=None, progress=None):
        """更新事件组"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(group_id)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE event_groups SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return cursor.rowcount
        return 0
    
    def delete_event_group(self, group_id):
        """删除事件组"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM event_groups WHERE id = ?', (group_id,))
            conn.commit()
            return cursor.rowcount
    
    def add_event_to_group(self, group_id, event_id, order_index=0, relation_type=0):
        """将事件添加到事件组"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO event_group_events (group_id, event_id, order_index, relation_type)
                VALUES (?, ?, ?, ?)
            ''', (group_id, event_id, order_index, relation_type))
            conn.commit()
            return cursor.lastrowid
    
    def remove_event_from_group(self, group_id, event_id):
        """从事件组中移除事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM event_group_events WHERE group_id = ? AND event_id = ?',
                          (group_id, event_id))
            conn.commit()
            return cursor.rowcount
    
    def get_event_groups_by_event(self, event_id):
        """获取事件所属的事件组"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT eg.*, ege.order_index, ege.relation_type
                FROM event_groups eg
                LEFT JOIN event_group_events ege ON eg.id = ege.group_id
                WHERE ege.event_id = ?
                ORDER BY eg.created_at ASC
            ''', (event_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_event_order_in_group(self, group_id, event_id, order_index):
        """更新事件在事件组中的排序"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE event_group_events SET order_index = ? 
                WHERE group_id = ? AND event_id = ?
            ''', (order_index, group_id, event_id))
            conn.commit()
            return cursor.rowcount
    
    def recalculate_group_progress(self, group_id):
        """重新计算事件组进度（基于已完成事件比例）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN e.writing_status = 2 OR e.writing_status = 3 THEN 1 ELSE 0 END) as completed
                FROM event_group_events ege
                LEFT JOIN events e ON ege.event_id = e.id
                WHERE ege.group_id = ?
            ''', (group_id,))
            row = cursor.fetchone()
            if row and row['total'] > 0:
                progress = int((row['completed'] or 0) / row['total'] * 100)
                cursor.execute('UPDATE event_groups SET progress = ? WHERE id = ?', (progress, group_id))
                conn.commit()
                return progress
        return 0