# 网文写作时间轴管理工具

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一个功能强大的网文写作时间轴管理工具，帮助作者系统性地管理小说中的人物、组织、事件、章节、线索和灵感。

## 📖 功能特点

### 核心功能

- **时间轴管理**
  - 可视化展示故事时间线
  - 支持虚拟时间轴（如"第1年1月1日"）
  - 事件对齐和缩放功能
  - 事件分类（普通事件、特殊事件、出生、死亡）

- **人物管理**
  - 人物信息管理（名称、别名、描述、传记）
  - 人物关系管理（师徒、恋人、仇敌、亲属等）
  - 人物内核系统（记录人物核心变化）

- **组织管理**
  - 组织架构管理
  - 组织关系可视化
  - 层级树形结构展示

- **事件管理**
  - 事件关联人物和时间
  - 事件类型标记
  - 事件内容详细描述
  - 标签系统

- **章节管理**
  - 章节看板视图
  - 章节与事件绑定
  - 写作进度追踪
  - 字数统计

- **线索管理**
  - 情节线索追踪
  - 事件关联
  - 伏笔标记
  - 线索状态管理（规划中、进行中、已完成）

- **事件组**
  - 将关联事件组合管理
  - 事件关系展示（起因、发展、高潮、结局、分支）
  - 进度自动计算
  - 状态管理

- **灵感管理**
  - 快速记录灵感
  - 分类管理（人物、情节、对话、设定等）
  - 全局搜索
  - 语义搜索功能

### 数据管理

- **导入导出**
  - 支持JSON格式完整数据备份
  - 数据迁移
  - 导出为Markdown、CSV格式

- **数据安全**
  - 本地SQLite数据库存储
  - 用户数据与代码分离

## 🛠️ 技术栈

- **语言**: Python 3.8+
- **GUI框架**: PySide6
- **数据库**: SQLite
- **依赖管理**: pip

## 📦 安装

### 1. 克隆项目

```bash
git clone https://github.com/Kongshanxuanyue/novel-timeline-tool.git
cd novel-timeline-tool
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install PySide6
```

### 4. 运行程序

```bash
python main.py
```

## 🚀 使用指南

### 基本操作

1. **添加人物**
   - 菜单：编辑 → 添加人物 或 `Ctrl+1`
   - 填写人物名称、别名、所属组织等信息

2. **添加事件**
   - 菜单：编辑 → 添加事件 或 `Ctrl+2`
   - 选择关联人物、填写时间、事件标题和内容

3. **组织管理**
   - 菜单：编辑 → 添加组织 或 `Ctrl+3`
   - 管理组织 → `Ctrl+4`

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+1` | 添加人物 |
| `Ctrl+2` | 添加事件 |
| `Ctrl+3` | 添加组织 |
| `Ctrl+4` | 管理组织 |
| `Ctrl+5` | 添加章节 |
| `Ctrl+6` | 新建线索 |
| `Ctrl+7` | 新建事件组 |
| `Ctrl+I` | 导入数据 |
| `Ctrl+F` | 全局搜索 |
| `Ctrl+Shift+N` | 快速记录灵感 |
| `Ctrl++` | 放大时间轴 |
| `Ctrl+-` | 缩小时间轴 |
| `Ctrl+0` | 重置缩放 |

### 数据导入导出

1. **导出完整备份**
   - 菜单：文件 → 导出完整备份
   - 保存为JSON格式

2. **导入数据**
   - 菜单：文件 → 导入数据
   - 选择之前导出的JSON文件

3. **导出为Markdown**
   - 菜单：导出 → 导出为 Markdown
   - 按组织-人物-事件结构导出

## 📁 项目结构

```
novel-timeline-tool/
├── main.py                 # 主程序入口
├── database.py             # 数据库管理
├── constants.py            # 常量定义
├── dialogs.py              # 对话框组件
├── timeline_canvas.py      # 时间轴画布
├── tree_model.py           # 树形数据模型
├── chapter_board.py        # 章节看板
├── plot_thread_panel.py    # 线索面板
├── event_group_panel.py    # 事件组面板
├── inspiration_panel.py    # 灵感面板
├── org_relation_graph.py   # 组织关系图
├── char_relation_graph.py  # 人物关系图
├── semantic_search.py      # 语义搜索
├── export_utils.py         # 导出功能
├── import_utils.py         # 导入功能
└── .gitignore              # Git忽略配置
```

## 🎯 数据导入说明

程序支持导入以下格式的数据：

- **组织** (organizations)
- **人物** (characters)
- **事件** (events)
- **章节** (chapters)
- **事件组** (event_groups)
- **情节线索** (plot_threads)
- **组织关系** (organization_relationships)
- **角色关系** (character_relationships)
- **灵感** (inspirations)

导入时会自动处理ID映射，确保引用关系正确。

## 🔧 开发说明

### 数据库结构

程序使用SQLite数据库存储数据，主要表包括：

- `organizations` - 组织表
- `characters` - 人物表
- `events` - 事件表
- `chapters` - 章节表
- `plot_threads` - 情节线索表
- `event_groups` - 事件组表
- `inspirations` - 灵感表
- 以及多个关联表

### 添加新功能

1. 在 `database.py` 中添加数据表和CRUD方法
2. 在 `dialogs.py` 中添加相应的对话框
3. 在 `main.py` 中集成菜单和逻辑

## 📝 更新日志

### v1.0 (2024-06)
- 初始版本发布
- 支持人物、事件、组织、章节管理
- 支持时间轴可视化
- 支持线索和灵感管理
- 支持数据导入导出
- 支持事件组功能

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

本项目采用 MIT 许可证。

## 📧 联系

- GitHub: https://github.com/Kongshanxuanyue/novel-timeline-tool

---

如果这个工具对你有帮助，请给个Star ⭐️
