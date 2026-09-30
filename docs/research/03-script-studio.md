# 03 脚本创作中心 — GitHub调研与技术选型报告

> 调研日期：2026-09-08
> 板块：Script Studio — 创意输出核心

---

## 1. 多Agent协作框架

### 1.1 评估

| 框架 | 特点 | 适用场景 | 结论 |
|------|------|---------|------|
| **LangGraph** | 原生支持状态机/条件边/中断/HITL/流式输出 | 我们已有依赖，最匹配 | **核心编排框架** |
| CrewAI | Role-based agent teams, sequential/hierarchical | 灵感来自其role定义方式 | 借鉴Agent角色设计模式，不直接引入 |
| AutoGen | Microsoft多Agent对话/辩论 | GroupChat辩论模式 | 借鉴DebateJudge设计思路 |

### 1.2 决策
- 使用LangGraph编排，参考CrewAI的角色定义模式
- 实现DebateJudge节点（参考AutoGen GroupChatManager的投票/裁决机制）
- 关键设计：每个Agent输出结构化Pydantic模型，而非自由文本，确保下游可消费

---

## 2. 剧本/分镜数据结构

### 2.1 评估

| 方案 | 特点 | 复杂度 | 决策 |
|------|------|--------|------|
| OpenTimelineIO | 皮克斯开源，专业影视行业标准 | 重(C++依赖) | 借鉴其Timeline/Track/Clip层级，不引入 |
| Fountain格式 | 纯文本剧本标记语言 | 中 | 适合长电影，不适合短视频15-60s |
| **自研轻量Schema** | Pydantic模型, 面向短视频优化 | 低 | **采用**: Shot/Script/Beat/EmotionPoint |

### 2.2 核心数据结构
- **Script**: title, hook, beats[], cta, emotion_curve[], duration, structure_type
- **StoryboardShot**: index, duration, shot_type, camera, scene, subject, dialogue, lighting, emotion, transition
- **CreativeDirection**: angle, hook_type, emotion_tone, target_audience, unique_value

---

## 3. 影视编剧理论（知识库构建依据）

### 3.1 提炼的理论体系

**钩子套路（100+种，分10大类）：**
1. 提问类: 反问/追问/灵魂拷问/二选一/数字提问
2. 震惊类: 反常识/数据冲击/身份反差/结果剧透/极端对比
3. 好奇类: 悬念/秘密/猜不到/反转预告/信息差
4. 数字类: N个技巧/百分比/时间/价格/排名
5. 痛点类: 扎心/共鸣/困境/错误纠正/避坑
6. 故事类: 个人经历/转折/奇遇/教训/真情流露
7. 演示类: 挑战/过程展示/速成/变身/对比实验
8. 共鸣类: 群体认同/情感共鸣/金句/价值观
9. 热梗类: 热点嫁接/BGM卡点/挑战话题/平台热点
10. 权威类: 数据支撑/专家引用/内幕消息/独家

**叙事结构（30+种）：**
- 经典结构: 钩子-正文-CTA / 问题-方案-证明 / 起承转合
- 短视频特化: 快切蒙太奇 / 口播直给 / 反转剧 / POV代入 / 倒计时 / 沉浸式
- 情绪结构: 情绪V曲线 / 持续高潮 / 反转惊喜 / 治愈渐进
- 互动结构: 投票/留悬念/系列连载

**CTA策略（20+种）：**
- 关注类: "关注我下期讲"/"点收藏防走失"
- 互动类: "评论区告诉我"/"你们觉得呢"/"双击屏幕"
- 行动类: "赶紧试试"/"收藏起来"/"转发给朋友"
- 情绪类: "看到最后有惊喜"/"忍住别哭"
- 系列类: "下期更精彩"/"续集更新中"

**情绪曲线模板（15种）：**
- V型(痛苦→治愈) / 倒V(平静→高潮→回落) / 阶梯上升 / 过山车(多次反转)
- 持续高能 / 先压后扬 / 暖心渐进 / 紧张→释放 / 好奇→满足

**节奏模式（10+种）：**
- 快切节奏(<1.5s/镜) / 中速叙事(2-3s/镜) / 慢镜头+快切混合
- 3秒钩子强节奏 / 呼吸式节奏(快慢交替) / BGM驱动型 / 静默冲击

---

## 4. 前端富文本/编辑器组件

### 4.1 评估

| 组件 | 用途 | 决策 |
|------|------|------|
| **dnd-kit** | 拖拽排序（分镜行拖拽） | 采用，现代轻量 |
| TanStack Table | 分镜表格 | 采用，功能强大 |
| Tiptap | 富文本脚本编辑 | 采用，扩展性好 |
| Lucide React | 图标 | 已有 |
| Recharts | 情绪曲线可视化 | 已有 |

### 4.2 决策
- 分镜表: 原生table + dnd-kit拖拽（不引入TanStack Table的复杂度，短视频分镜场景够用）
- 脚本编辑: contentEditable + Markdown-like block（MVP阶段不用tiptap，减少依赖）
- 情绪曲线: Recharts LineChart（已有recharts）

---

## 技术栈总结

| 模块 | 选型 |
|------|------|
| Agent编排 | LangGraph (已有) |
| 多Agent模式 | 参考CrewAI role + AutoGen debate |
| 数据结构 | Pydantic自研Schema（借鉴OTIO概念） |
| 创意知识库 | JSON文件 + PG持久化（6个核心文件） |
| 拖拽排序 | @dnd-kit/core + @dnd-kit/sortable |
| 富文本 | 原生contentEditable（MVP） |
| 情绪可视化 | Recharts（已有） |
| 测试框架 | pytest + pytest-asyncio（已有） |
