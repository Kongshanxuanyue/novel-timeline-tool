"""导出功能模块"""

import re
import json
import csv
import time
from PySide6.QtWidgets import QFileDialog

from constants import EVENT_TYPE_ICONS, EVENT_TYPE_NAMES


def parse_time_value(time_str):
    """将时间字符串转换为数值用于比较"""
    match = re.match(r'第?(\d+)年(\d+)月(\d+)日', str(time_str))
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return year * 10000 + month * 100 + day
    return 0


def collect_filtered_data(db, options):
    """根据筛选条件收集数据"""
    org_ids = options.get('org_ids', [])
    char_ids = options.get('char_ids', [])
    event_ids = options.get('event_ids', [])
    event_types = options.get('event_types', [])
    start_time = options.get('start_time', '')
    end_time = options.get('end_time', '')

    start_val = parse_time_value(start_time) if start_time else 0
    end_val = parse_time_value(end_time) if end_time else 999999999

    data = {
        'organizations': [],
        'characters': [],
        'events': []
    }

    all_orgs = db.get_all_organizations()
    all_chars = db.get_all_characters()

    # 如果选择了具体事件，优先处理
    if event_ids:
        selected_event_ids = set(event_ids)
        orgs = []
        chars = []
        char_events_map = {}
        
        for ch in all_chars:
            events = db.get_events_by_character(ch['id'])
            filtered_events = []
            for ev in events:
                if ev['id'] in selected_event_ids:
                    filtered_events.append(ev)
                    if ch['id'] not in char_events_map:
                        char_events_map[ch['id']] = []
                    char_events_map[ch['id']].append(ev)
            
            if filtered_events:
                chars.append(ch)
                org_id = ch.get('organization_id')
                if org_id:
                    org = db.get_organization(org_id)
                    if org and org not in orgs:
                        orgs.append(org)
        
        for org in orgs:
            data['organizations'].append({
                'id': org['id'],
                'name': org['name'],
                'description': org.get('description'),
                'color': org.get('color')
            })
        
        for ch in chars:
            char_data = {
                'id': ch['id'],
                'name': ch['name'],
                'alias': ch.get('alias'),
                'description': ch.get('description'),
                'organization_id': ch.get('organization_id'),
                'color': ch.get('color'),
                'birth_time': ch.get('birth_time'),
                'death_time': ch.get('death_time'),
                'events': char_events_map.get(ch['id'], [])
            }
            for ev in char_data['events']:
                data['events'].append({
                    'character_id': ch['id'],
                    'character_name': ch['name'],
                    'timestamp': ev['timestamp'],
                    'title': ev['title'],
                    'type': ev.get('type', 0),
                    'color': ev.get('color', '#10B981'),
                    'content': ev.get('content')
                })
            data['characters'].append(char_data)
        
        return data

    # 根据组织或人物筛选
    if org_ids:
        selected_org_ids = set(org_ids)
        orgs = []
        chars = []
        for org in all_orgs:
            if org['id'] in selected_org_ids:
                orgs.append(org)
        for ch in all_chars:
            org_id = ch.get('organization_id')
            if org_id in selected_org_ids or (org_id is None and 0 in selected_org_ids):
                chars.append(ch)
    elif char_ids:
        orgs = []
        chars = []
        selected_char_ids = set(char_ids)
        for ch in all_chars:
            if ch['id'] in selected_char_ids:
                chars.append(ch)
                org_id = ch.get('organization_id')
                if org_id:
                    org = db.get_organization(org_id)
                    if org and org not in orgs:
                        orgs.append(org)
    else:
        orgs = all_orgs
        chars = all_chars

    for org in orgs:
        data['organizations'].append({
            'id': org['id'],
            'name': org['name'],
            'description': org.get('description'),
            'color': org.get('color')
        })

    for ch in chars:
        char_data = {
            'id': ch['id'],
            'name': ch['name'],
            'alias': ch.get('alias'),
            'description': ch.get('description'),
            'organization_id': ch.get('organization_id'),
            'color': ch.get('color'),
            'birth_time': ch.get('birth_time'),
            'death_time': ch.get('death_time'),
            'events': []
        }
        events = db.get_events_by_character(ch['id'])
        for ev in events:
            ev_type = ev.get('type', 0)
            if event_types and ev_type not in event_types:
                continue

            ev_time_val = parse_time_value(ev['timestamp'])
            if ev_time_val < start_val or ev_time_val > end_val:
                continue

            event_data = {
                'id': ev['id'],
                'timestamp': ev['timestamp'],
                'title': ev['title'],
                'type': ev_type,
                'color': ev.get('color', '#10B981'),
                'content': ev.get('content')
            }
            char_data['events'].append(event_data)
            data['events'].append({
                'character_id': ch['id'],
                'character_name': ch['name'],
                'timestamp': ev['timestamp'],
                'title': ev['title'],
                'type': ev_type,
                'color': ev.get('color', '#10B981'),
                'content': ev.get('content')
            })
        data['characters'].append(char_data)

    return data


def export_to_json(parent, db, options, title="导出 JSON"):
    """导出为 JSON 格式"""
    file_path, _ = QFileDialog.getSaveFileName(parent, title, "", "JSON Files (*.json)")
    if not file_path:
        return None
    
    data = collect_filtered_data(db, options)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return file_path


def export_to_markdown(parent, db, options):
    """导出为 Markdown 格式"""
    file_path, _ = QFileDialog.getSaveFileName(parent, "导出 Markdown", "", "Markdown Files (*.md)")
    if not file_path:
        return None
    
    filtered_data = collect_filtered_data(db, options)

    md_content = []
    md_content.append("# 故事时间线\n")
    md_content.append("> 导出时间：{}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    md_content.append("")

    for org in filtered_data['organizations']:
        org_chars = [ch for ch in filtered_data['characters'] if ch.get('organization_id') == org['id']]
        if not org_chars:
            continue

        md_content.append("## 🏛️ {}\n\n".format(org['name']))
        if org.get('description'):
            md_content.append("{}\n\n".format(org['description']))

        for ch in org_chars:
            md_content.append("### 👤 {}\n\n".format(ch['name']))
            if ch.get('alias'):
                md_content.append("**别名**: {}\n\n".format(ch['alias']))
            if ch.get('description'):
                md_content.append("{}\n\n".format(ch['description']))
            if ch.get('birth_time'):
                md_content.append("**出生**: {}\n\n".format(ch['birth_time']))
            if ch.get('death_time'):
                md_content.append("**死亡**: {}\n\n".format(ch['death_time']))
            md_content.append("**时间线:**\n\n")

            if ch.get('events'):
                for ev in ch['events']:
                    type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
                    md_content.append("- {} **{}** - {}\n".format(type_icon, ev['timestamp'], ev['title']))
                    if ev.get('content'):
                        md_content.append("  - {}\n".format(ev['content']))
            else:
                md_content.append("- 暂无事件\n")
            md_content.append("\n")

    no_org_chars = [ch for ch in filtered_data['characters'] if ch.get('organization_id') is None or ch.get('organization_id') == 0]
    if no_org_chars:
        md_content.append("## 🏛️ 无组织人物\n\n")
        for ch in no_org_chars:
            md_content.append("### 👤 {}\n\n".format(ch['name']))
            if ch.get('alias'):
                md_content.append("**别名**: {}\n\n".format(ch['alias']))
            if ch.get('description'):
                md_content.append("{}\n\n".format(ch['description']))
            if ch.get('birth_time'):
                md_content.append("**出生**: {}\n\n".format(ch['birth_time']))
            if ch.get('death_time'):
                md_content.append("**死亡**: {}\n\n".format(ch['death_time']))
            md_content.append("**时间线:**\n\n")

            if ch.get('events'):
                for ev in ch['events']:
                    type_icon = EVENT_TYPE_ICONS.get(ev.get('type', 0), "●")
                    md_content.append("- {} **{}** - {}\n".format(type_icon, ev['timestamp'], ev['title']))
                    if ev.get('content'):
                        md_content.append("  - {}\n".format(ev['content']))
            else:
                md_content.append("- 暂无事件\n")
            md_content.append("\n")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(md_content)
    
    return file_path


def export_to_csv(parent, db, options):
    """导出事件为 CSV 格式"""
    file_path, _ = QFileDialog.getSaveFileName(parent, "导出 CSV", "", "CSV Files (*.csv)")
    if not file_path:
        return None
    
    filtered_data = collect_filtered_data(db, options)

    with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['人物', '时间', '事件标题', '类型', '颜色', '内容'])

        for ch in filtered_data['characters']:
            if ch.get('events'):
                for ev in ch['events']:
                    writer.writerow([
                        ch['name'],
                        ev['timestamp'],
                        ev['title'],
                        EVENT_TYPE_NAMES.get(ev.get('type', 0), "普通"),
                        ev.get('color', '#10B981'),
                        ev.get('content', '')
                    ])
    
    return file_path