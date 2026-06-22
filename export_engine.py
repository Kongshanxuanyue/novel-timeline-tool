import json

class AIExportEngine:
    def __init__(self, db_manager):
        self.db = db_manager

    def generate_llm_context(self, filter_options: dict) -> str:
        """
        根据前端勾选的筛选范围，导出标准 AI API 数据
        filter_options 包含: character_ids (list), include_biography (bool), template_type (str)
        """
        character_ids = filter_options.get('character_ids', [])
        include_biography = filter_options.get('include_biography', True)
        template_type = filter_options.get('template_type', 'OpenAI')

        export_data = {
            "system_prompt": "你是一位拥有神级大纲逻辑的网文写作助手，请严格遵循以下提供的小说设定、时间轴演进以及人物内核快照进行续写或情节推演，不得前后矛盾。",
            "characters": [],
            "user_prompt": "请根据以上提供的人物内核和时间线发展，帮我构思接下来的关键转折冲突情节。"
        }

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for ch_id in character_ids:
                # 获取人物基础数据
                cursor.execute("SELECT * FROM characters WHERE id = ?", (ch_id,))
                ch_row = cursor.fetchone()
                if not ch_row: continue
                ch_dict = dict(ch_row)

                ch_payload = {
                    "role": "character",
                    "name": ch_dict["name"],
                    "alias": ch_dict["alias"],
                }

                if include_biography:
                    ch_payload["biography"] = ch_dict["biography"]

                # 提取该人物的时间轴事件
                cursor.execute("SELECT timestamp, title, content, core_changes FROM events WHERE character_id = ? AND is_public = 1 ORDER BY timestamp ASC", (ch_id,))
                events = cursor.fetchall()
                
                ch_payload["timeline"] = []
                for ev in events:
                    ch_payload["timeline"].append({
                        "time_node": ev["timestamp"],
                        "event": ev["title"],
                        "details": ev["content"],
                        "core_changes": json.loads(ev["core_changes"]) if ev["core_changes"] else {}
                    })

                # 获取当前最新内核维度
                cursor.execute("SELECT core_name, core_value FROM character_cores WHERE character_id = ? AND end_time IS NULL", (ch_id,))
                cores = cursor.fetchall()
                ch_payload["current_core"] = {row["core_name"]: row["core_value"] for row in cores}

                export_data["characters"].append(ch_payload)

        # 针对不同大模型的包装机制
        if template_type == "Claude_System_Prompt":
            # Claude 喜欢 XML 标签包裹的上下文，可以针对性转换
            return self._to_xml_format(export_data)
        
        # 默认返回 OpenAI / 标准 JSON 格式
        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def _to_xml_format(self, data: dict) -> str:
        """辅助方法：将结构化数据转为 Claude 最爱的 XML 风格标签提示词"""
        xml = f"<system_instruction>\n{data['system_prompt']}\n"
        for ch in data['characters']:
            xml += f"  <character name='{ch['name']}'>\n"
            xml += f"    <biography>{ch.get('biography','')}</biography>\n"
            xml += f"    <current_core>{json.dumps(ch['current_core'], ensure_ascii=False)}</current_core>\n"
            xml += "  </character>\n"
        xml += f"</system_instruction>\n\nUser: {data['user_prompt']}"
        return xml