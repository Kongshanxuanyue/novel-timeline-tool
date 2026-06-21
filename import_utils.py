"""导入功能模块"""

import json
import re
from PySide6.QtWidgets import QFileDialog, QMessageBox
from database import parse_time_to_value


def import_from_json(parent, db):
    """从JSON文件导入数据"""
    file_path, _ = QFileDialog.getOpenFileName(
        parent, "导入数据", "", "JSON Files (*.json)"
    )
    if not file_path:
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        QMessageBox.warning(parent, "错误", f"无法读取文件: {str(e)}")
        return None
    
    # ID映射表：旧ID -> 新ID
    id_maps = {
        'organizations': {},  # 旧org_id -> 新org_id
        'characters': {},    # 旧char_id -> 新char_id
        'events': {},        # 旧event_id -> 新event_id
        'chapters': {},      # 旧chapter_id -> 新chapter_id
        'plot_threads': {},  # 旧thread_id -> 新thread_id
        'event_groups': {},  # 旧group_id -> 新group_id
    }
    
    import_stats = {
        'organizations': 0,
        'characters': 0,
        'events': 0,
        'chapters': 0,
        'plot_threads': 0,
        'event_groups': 0,
    }
    
    # 1. 导入组织
    if 'organizations' in data:
        for org_data in data['organizations']:
            try:
                org_id = db.create_organization(
                    name=org_data.get('name', ''),
                    description=org_data.get('description'),
                    color=org_data.get('color')
                )
                id_maps['organizations'][org_data['id']] = org_id
                import_stats['organizations'] += 1
            except Exception as e:
                print(f"导入组织失败: {e}")
    
    # 2. 导入章节（先于人物，因为人物可能关联章节）
    if 'chapters' in data:
        for chapter_data in data['chapters']:
            try:
                chapter_id = db.create_chapter(
                    number=chapter_data.get('number', 1),
                    title=chapter_data.get('title', ''),
                    summary=chapter_data.get('summary'),
                    status=chapter_data.get('status', 0),
                    word_count=chapter_data.get('word_count', 0)
                )
                id_maps['chapters'][chapter_data['id']] = chapter_id
                import_stats['chapters'] += 1
            except Exception as e:
                print(f"导入章节失败: {e}")
    
    # 3. 导入人物
    if 'characters' in data:
        for char_data in data['characters']:
            try:
                # 映射组织ID
                old_org_id = char_data.get('organization_id')
                new_org_id = id_maps['organizations'].get(old_org_id) if old_org_id else None
                
                char_id = db.create_character(
                    name=char_data.get('name', ''),
                    alias=char_data.get('alias'),
                    description=char_data.get('description'),
                    organization_id=new_org_id,
                    color=char_data.get('color'),
                    birth_time=char_data.get('birth_time'),
                    death_time=char_data.get('death_time'),
                    biography=char_data.get('biography', '')
                )
                id_maps['characters'][char_data['id']] = char_id
                import_stats['characters'] += 1
            except Exception as e:
                print(f"导入人物失败: {e}")
    
    # 4. 导入事件
    if 'events' in data:
        for event_data in data['events']:
            try:
                # 映射人物ID
                old_char_id = event_data.get('character_id')
                new_char_id = id_maps['characters'].get(old_char_id)
                if not new_char_id:
                    continue
                
                # 映射章节ID
                old_chapter_id = event_data.get('chapter_id')
                new_chapter_id = id_maps['chapters'].get(old_chapter_id) if old_chapter_id else None
                
                event_id = db.create_event(
                    character_id=new_char_id,
                    timestamp=event_data.get('timestamp', ''),
                    title=event_data.get('title', ''),
                    content=event_data.get('content'),
                    event_type=event_data.get('type', 0),
                    color=event_data.get('color', '#10B981'),
                    tags=event_data.get('tags'),
                    chapter_number=event_data.get('chapter_number'),
                    chapter_title=event_data.get('chapter_title'),
                    writing_status=event_data.get('writing_status', 0)
                )
                id_maps['events'][event_data['id']] = event_id
                import_stats['events'] += 1
            except Exception as e:
                print(f"导入事件失败: {e}")
    
    # 5. 导入线索
    if 'plot_threads' in data:
        for thread_data in data['plot_threads']:
            try:
                thread_id = db.create_plot_thread(
                    name=thread_data.get('name', ''),
                    description=thread_data.get('description'),
                    category=thread_data.get('category', 0),
                    status=thread_data.get('status', 0),
                    importance=thread_data.get('importance', 3)
                )
                id_maps['plot_threads'][thread_data['id']] = thread_id
                import_stats['plot_threads'] += 1
                
                # 导入线索-事件关联
                if 'events' in thread_data:
                    for thread_event in thread_data['events']:
                        old_event_id = thread_event.get('event_id')
                        new_event_id = id_maps['events'].get(old_event_id)
                        if new_event_id:
                            try:
                                db.link_event_to_thread(
                                    thread_id=thread_id,
                                    event_id=new_event_id,
                                    relation_type=thread_event.get('relation_type', 0),
                                    notes=thread_event.get('notes')
                                )
                            except Exception as e:
                                print(f"导入线索事件关联失败: {e}")
            except Exception as e:
                print(f"导入线索失败: {e}")
    
    # 6. 导入事件组
    if 'event_groups' in data:
        for group_data in data['event_groups']:
            try:
                group_id = db.create_event_group(
                    name=group_data.get('name', ''),
                    description=group_data.get('description'),
                    color=group_data.get('color', '#8B5CF6'),
                    status=group_data.get('status', 0)
                )
                id_maps['event_groups'][group_data['id']] = group_id
                import_stats['event_groups'] += 1
                
                # 导入事件组-事件关联
                if 'events' in group_data:
                    for idx, group_event in enumerate(group_data['events']):
                        old_event_id = group_event.get('event_id')
                        new_event_id = id_maps['events'].get(old_event_id)
                        if new_event_id:
                            try:
                                db.add_event_to_group(
                                    group_id=group_id,
                                    event_id=new_event_id,
                                    order_index=idx,
                                    relation_type=group_event.get('relation_type', 0)
                                )
                            except Exception as e:
                                print(f"导入事件组事件关联失败: {e}")
            except Exception as e:
                print(f"导入事件组失败: {e}")
    
    # 7. 导入组织关系
    if 'organization_relationships' in data:
        for rel_data in data['organization_relationships']:
            try:
                old_org1_id = rel_data.get('org1_id')
                old_org2_id = rel_data.get('org2_id')
                new_org1_id = id_maps['organizations'].get(old_org1_id)
                new_org2_id = id_maps['organizations'].get(old_org2_id)
                
                if new_org1_id and new_org2_id:
                    db.create_organization_relationship(
                        org1_id=new_org1_id,
                        org2_id=new_org2_id,
                        relationship_type_id=rel_data.get('relationship_type_id', 1),
                        strength=rel_data.get('strength', 5),
                        start_time=rel_data.get('start_time'),
                        end_time=rel_data.get('end_time'),
                        description=rel_data.get('description')
                    )
            except Exception as e:
                print(f"导入组织关系失败: {e}")
    
    # 8. 导入角色关系
    if 'character_relationships' in data:
        for rel_data in data['character_relationships']:
            try:
                old_char1_id = rel_data.get('char1_id')
                old_char2_id = rel_data.get('char2_id')
                new_char1_id = id_maps['characters'].get(old_char1_id)
                new_char2_id = id_maps['characters'].get(old_char2_id)
                
                if new_char1_id and new_char2_id:
                    db.create_character_relationship(
                        char1_id=new_char1_id,
                        char2_id=new_char2_id,
                        relationship_type_id=rel_data.get('relationship_type_id', 1),
                        strength=rel_data.get('strength', 5),
                        description=rel_data.get('description'),
                        start_event_id=None  # 事件ID映射较复杂，暂时不处理
                    )
            except Exception as e:
                print(f"导入角色关系失败: {e}")
    
    # 9. 导入灵感
    if 'inspirations' in data:
        for insp_data in data['inspirations']:
            try:
                old_event_id = insp_data.get('related_event_id')
                new_event_id = id_maps['events'].get(old_event_id) if old_event_id else None
                
                db.create_inspiration(
                    content=insp_data.get('content', ''),
                    category=insp_data.get('category', 0),
                    tags=insp_data.get('tags'),
                    source=insp_data.get('source'),
                    related_event_id=new_event_id,
                    is_used=insp_data.get('is_used', 0)
                )
            except Exception as e:
                print(f"导入灵感失败: {e}")
    
    # 显示导入统计
    stats_text = "\n".join([
        f"• {name}: {count} 条"
        for name, count in import_stats.items()
        if count > 0
    ])
    
    QMessageBox.information(
        parent, "导入完成",
        f"数据导入成功！\n\n{stats_text}"
    )
    
    return file_path


def export_all_to_json(parent, db):
    """导出所有数据为JSON格式（用于备份/迁移）"""
    file_path, _ = QFileDialog.getSaveFileName(
        parent, "导出完整数据", "", "JSON Files (*.json)"
    )
    if not file_path:
        return None
    
    data = {
        'version': '1.0',
        'export_time': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
        'organizations': [],
        'characters': [],
        'events': [],
        'chapters': [],
        'plot_threads': [],
        'event_groups': [],
        'organization_relationships': [],
        'character_relationships': [],
        'inspirations': [],
        'relationship_types': [],
        'character_relationship_types': [],
    }
    
    # 导出组织
    for org in db.get_all_organizations():
        data['organizations'].append({
            'id': org['id'],
            'name': org['name'],
            'description': org.get('description'),
            'color': org.get('color'),
            'parent_id': org.get('parent_id')
        })
    
    # 导出人物
    for char in db.get_all_characters():
        data['characters'].append({
            'id': char['id'],
            'name': char['name'],
            'alias': char.get('alias'),
            'description': char.get('description'),
            'organization_id': char.get('organization_id'),
            'color': char.get('color'),
            'birth_time': char.get('birth_time'),
            'death_time': char.get('death_time'),
            'biography': char.get('biography', '')
        })
    
    # 导出事件
    all_chars = db.get_all_characters()
    for char in all_chars:
        events = db.get_events_by_character(char['id'])
        for ev in events:
            data['events'].append({
                'id': ev['id'],
                'character_id': ev['character_id'],
                'timestamp': ev['timestamp'],
                'title': ev['title'],
                'content': ev.get('content'),
                'type': ev.get('type', 0),
                'color': ev.get('color', '#10B981'),
                'tags': ev.get('tags'),
                'chapter_number': ev.get('chapter_number'),
                'chapter_title': ev.get('chapter_title'),
                'writing_status': ev.get('writing_status', 0)
            })
    
    # 导出章节
    for chapter in db.get_all_chapters():
        data['chapters'].append({
            'id': chapter['id'],
            'number': chapter['number'],
            'title': chapter['title'],
            'summary': chapter.get('summary'),
            'word_count': chapter.get('word_count', 0),
            'status': chapter.get('status', 0),
            'start_event_id': chapter.get('start_event_id'),
            'end_event_id': chapter.get('end_event_id')
        })
    
    # 导出线索
    for thread in db.get_all_plot_threads():
        thread_data = {
            'id': thread['id'],
            'name': thread['name'],
            'description': thread.get('description'),
            'category': thread.get('category', 0),
            'status': thread.get('status', 0),
            'importance': thread.get('importance', 3),
            'events': []
        }
        
        # 导出线索事件关联
        thread_events = db.get_thread_events(thread['id'])
        for te in thread_events:
            thread_data['events'].append({
                'event_id': te['event_id'],
                'relation_type': te.get('relation_type', 0),
                'notes': te.get('notes')
            })
        
        data['plot_threads'].append(thread_data)
    
    # 导出事件组
    for group in db.get_all_event_groups():
        group_data = {
            'id': group['id'],
            'name': group['name'],
            'description': group.get('description'),
            'color': group.get('color', '#8B5CF6'),
            'status': group.get('status', 0),
            'events': []
        }
        
        # 导出事件组事件关联
        group_data_full = db.get_event_group_with_events(group['id'])
        if group_data_full and 'events' in group_data_full:
            for idx, ev in enumerate(group_data_full['events']):
                group_data['events'].append({
                    'event_id': ev['id'],
                    'order_index': idx,
                    'relation_type': ev.get('relation_type', 0)
                })
        
        data['event_groups'].append(group_data)
    
    # 导出组织关系
    for rel in db.get_all_organization_relationships():
        data['organization_relationships'].append({
            'id': rel['id'],
            'org1_id': rel['org1_id'],
            'org2_id': rel['org2_id'],
            'relationship_type_id': rel['relationship_type_id'],
            'strength': rel.get('strength', 5),
            'start_time': rel.get('start_time'),
            'end_time': rel.get('end_time'),
            'description': rel.get('description')
        })
    
    # 导出角色关系
    for rel in db.get_all_character_relationships():
        data['character_relationships'].append({
            'id': rel['id'],
            'char1_id': rel['char1_id'],
            'char2_id': rel['char2_id'],
            'relationship_type_id': rel['relationship_type_id'],
            'strength': rel.get('strength', 5),
            'description': rel.get('description'),
            'start_event_id': rel.get('start_event_id')
        })
    
    # 导出灵感
    for insp in db.get_all_inspirations():
        data['inspirations'].append({
            'id': insp['id'],
            'content': insp['content'],
            'category': insp.get('category', 0),
            'tags': insp.get('tags'),
            'source': insp.get('source'),
            'is_used': insp.get('is_used', 0),
            'related_event_id': insp.get('related_event_id')
        })
    
    # 导出关系类型
    for rt in db.get_all_relationship_types():
        data['relationship_types'].append({
            'id': rt['id'],
            'name': rt['name'],
            'color': rt['color'],
            'line_style': rt.get('line_style', 'solid')
        })
    
    # 导出角色关系类型
    for rt in db.get_all_character_relationship_types():
        data['character_relationship_types'].append({
            'id': rt['id'],
            'name': rt['name'],
            'color': rt['color'],
            'bidirectional': rt.get('bidirectional', 0)
        })
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        QMessageBox.information(parent, "导出成功", f"数据已导出到:\n{file_path}")
        return file_path
    except Exception as e:
        QMessageBox.warning(parent, "错误", f"导出失败: {str(e)}")
        return None
