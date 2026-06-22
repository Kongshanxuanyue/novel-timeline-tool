"""操作日志系统 - 支持撤销/重做"""

from collections import deque
from PySide6.QtCore import QObject, Signal


class ActionRecord:
    """单条操作记录"""
    def __init__(self, action_type, entity_type, entity_id, old_data=None, new_data=None, extra=None):
        """
        action_type: 'add', 'delete', 'update'
        entity_type: 'character', 'event', 'organization', 'chapter', 'plot_thread', 'event_group', 'inspiration'
        entity_id: 实体ID
        old_data: 操作前的完整数据（用于撤销update/delete）
        new_data: 操作后的数据（用于撤销add时知道创建了哪些关联）
        extra: 额外信息（如事件关联的人物ID等）
        """
        self.action_type = action_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.old_data = old_data
        self.new_data = new_data
        self.extra = extra


class ActionLogManager(QObject):
    """操作日志管理器 - 最多存储10条操作"""
    action_recorded = Signal()
    action_undone = Signal(str)  # entity_type

    def __init__(self, max_size=10):
        super().__init__()
        self._log = deque(maxlen=max_size)
        self._db = None

    def set_db(self, db):
        self._db = db

    def record(self, action_type, entity_type, entity_id, old_data=None, new_data=None, extra=None):
        """记录一条操作"""
        record = ActionRecord(action_type, entity_type, entity_id, old_data, new_data, extra)
        self._log.append(record)
        self.action_recorded.emit()

    def can_undo(self):
        return len(self._log) > 0

    def undo(self):
        """撤销最近一条操作，返回操作类型和实体类型"""
        if not self._log:
            return None

        record = self._log.pop()
        if not self._db:
            return None

        try:
            if record.action_type == 'add':
                self._undo_add(record)
            elif record.action_type == 'delete':
                self._undo_delete(record)
            elif record.action_type == 'update':
                self._undo_update(record)

            self.action_undone.emit(record.entity_type)
            return record.entity_type
        except Exception as e:
            print(f"撤销操作失败: {e}")
            return None

    def _undo_add(self, record):
        """撤销添加 = 删除"""
        if record.entity_type == 'character':
            self._db.delete_character(record.entity_id)
        elif record.entity_type == 'event':
            self._db.delete_event(record.entity_id)
        elif record.entity_type == 'organization':
            self._db.delete_organization(record.entity_id)
        elif record.entity_type == 'chapter':
            self._db.delete_chapter(record.entity_id)
        elif record.entity_type == 'plot_thread':
            self._db.delete_plot_thread(record.entity_id)
        elif record.entity_type == 'event_group':
            self._db.delete_event_group(record.entity_id)
        elif record.entity_type == 'inspiration':
            self._db.delete_inspiration(record.entity_id)

    def _undo_delete(self, record):
        """撤销删除 = 重新创建"""
        old = record.old_data
        if not old:
            return

        if record.entity_type == 'character':
            # 重新创建人物，并恢复原始ID
            new_id = self._db.create_character(
                name=old.get('name', ''),
                alias=old.get('alias'),
                description=old.get('description'),
                organization_id=old.get('organization_id'),
                color=old.get('color'),
                birth_time=old.get('birth_time'),
                death_time=old.get('death_time')
            )
            # 更新ID映射
            record.new_id = new_id

        elif record.entity_type == 'event':
            new_id = self._db.create_event(
                character_id=old.get('character_id'),
                timestamp=old.get('timestamp', ''),
                title=old.get('title', ''),
                content=old.get('content'),
                type=old.get('type', 0),
                color=old.get('color', '#10B981'),
                tags=old.get('tags')
            )
            # 恢复写作状态
            ws = old.get('writing_status', 0)
            if ws and ws != 0:
                try:
                    self._db.update_event_writing_status(new_id, ws)
                except Exception:
                    pass
            # 恢复章节关联
            if old.get('chapter_id'):
                try:
                    self._db.update_event_chapter(new_id, old['chapter_id'])
                except Exception:
                    pass
            record.new_id = new_id

        elif record.entity_type == 'organization':
            new_id = self._db.create_organization(
                name=old.get('name', ''),
                description=old.get('description'),
                color=old.get('color')
            )
            record.new_id = new_id

        elif record.entity_type == 'chapter':
            new_id = self._db.create_chapter(
                number=old.get('number', 1),
                title=old.get('title', ''),
                summary=old.get('summary'),
                status=old.get('status', 0),
                word_count=old.get('word_count', 0)
            )
            record.new_id = new_id

        elif record.entity_type == 'plot_thread':
            new_id = self._db.create_plot_thread(
                title=old.get('title', ''),
                description=old.get('description'),
                category=old.get('category', 0),
                color=old.get('color', '#8B5CF6')
            )
            # 恢复关联事件
            if record.extra and 'event_ids' in record.extra:
                for ev_id in record.extra['event_ids']:
                    try:
                        self._db.add_event_to_thread(new_id, ev_id)
                    except Exception:
                        pass
            record.new_id = new_id

        elif record.entity_type == 'event_group':
            new_id = self._db.create_event_group(
                name=old.get('name', ''),
                description=old.get('description'),
                color=old.get('color', '#8B5CF6')
            )
            # 恢复关联事件
            if record.extra and 'events' in record.extra:
                for ev in record.extra['events']:
                    try:
                        self._db.add_event_to_group(new_id, ev['event_id'], ev.get('order_index', 0), ev.get('relation_type', 0))
                    except Exception:
                        pass
            record.new_id = new_id

        elif record.entity_type == 'inspiration':
            new_id = self._db.create_inspiration(
                content=old.get('content', ''),
                tags=old.get('tags')
            )
            record.new_id = new_id

    def _undo_update(self, record):
        """撤销更新 = 恢复旧数据"""
        old = record.old_data
        if not old:
            return

        entity_id = record.entity_id

        if record.entity_type == 'character':
            self._db.update_character(
                entity_id,
                name=old.get('name'),
                alias=old.get('alias'),
                description=old.get('description'),
                organization_id=old.get('organization_id'),
                color=old.get('color'),
                birth_time=old.get('birth_time'),
                death_time=old.get('death_time')
            )

        elif record.entity_type == 'event':
            self._db.update_event(
                entity_id,
                character_id=old.get('character_id'),
                timestamp=old.get('timestamp'),
                title=old.get('title'),
                content=old.get('content'),
                type=old.get('type'),
                color=old.get('color'),
                tags=old.get('tags')
            )
            # 恢复写作状态
            ws = old.get('writing_status', 0)
            if ws is not None:
                try:
                    self._db.update_event_writing_status(entity_id, ws)
                except Exception:
                    pass
            # 恢复章节关联
            if 'chapter_id' in old:
                try:
                    self._db.update_event_chapter(entity_id, old['chapter_id'])
                except Exception:
                    pass

        elif record.entity_type == 'organization':
            self._db.update_organization(
                entity_id,
                name=old.get('name'),
                description=old.get('description'),
                color=old.get('color'),
                parent_id=old.get('parent_id')
            )

        elif record.entity_type == 'chapter':
            self._db.update_chapter(
                entity_id,
                number=old.get('number'),
                title=old.get('title'),
                summary=old.get('summary'),
                status=old.get('status'),
                word_count=old.get('word_count')
            )

        elif record.entity_type == 'plot_thread':
            self._db.update_plot_thread(
                entity_id,
                title=old.get('title'),
                description=old.get('description'),
                category=old.get('category'),
                color=old.get('color')
            )

        elif record.entity_type == 'event_group':
            self._db.update_event_group(
                entity_id,
                name=old.get('name'),
                description=old.get('description'),
                color=old.get('color'),
                status=old.get('status')
            )

        elif record.entity_type == 'inspiration':
            self._db.update_inspiration(
                entity_id,
                content=old.get('content'),
                tags=old.get('tags')
            )

    def get_undo_description(self):
        """获取下一条可撤销操作的描述"""
        if not self._log:
            return None
        record = self._log[-1]
        action_names = {'add': '添加', 'delete': '删除', 'update': '编辑'}
        entity_names = {
            'character': '人物', 'event': '事件', 'organization': '组织',
            'chapter': '章节', 'plot_thread': '线索', 'event_group': '事件组',
            'inspiration': '灵感'
        }
        return f"撤销{action_names.get(record.action_type, '操作')}{entity_names.get(record.entity_type, '对象')}"
