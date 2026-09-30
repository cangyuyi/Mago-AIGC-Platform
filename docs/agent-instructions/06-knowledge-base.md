# 指令 06：知识与资产底座（Knowledge Base & Asset Management）

## 角色设定

你是一名**RAG系统工程师+知识工程师+数据架构师**，擅长构建企业级知识库、向量检索系统、数据资产管理平台。你理解Embedding模型选择、向量索引优化、混合检索（关键词+向量+知识图谱）、以及知识的持续更新和质量保障机制。

## 前置依赖

必须先完成 `01-project-bootstrap.md`（PostgreSQL/Python环境/Milvus/MinIO）。其他板块会依赖本板块提供知识检索能力，可以并行开发。

## 任务目标

构建Mago Agent平台的**知识中枢**：
1. 向量检索基础设施（Embedding模型+Milvus集合+混合检索）
2. 爆款视频知识库（由板块02持续写入）
3. 创意理论知识库（由板块03初始化）
4. 提示词知识库（由板块05初始化）
5. 镜头语言/摄影/电影知识库
6. 用户项目资产库（角色/风格/场景/道具/模板复用）
7. 知识库管理后台（知识录入/审核/版本/质量评分）
8. 统一检索API（供所有Agent调用）

## 执行步骤

### Step 1：调研GitHub开源方案（必须）

记录到 `docs/research/06-knowledge-base.md`：

1. **RAG框架**：
   - 搜索关键词：`RAG framework production github`, `llama-index vs langchain rag`, `haystack RAG`, `RAGFlow`, `QAnything`
   - 参考：`infiniflow/ragflow`(⭐国产深搜RAG), `netease-youdao/QAnything`(网易有道), `langchain-ai/langchain`(LangChain RAG), `run-llama/llama_index`, `deepset-ai/haystack`, `microsoft/graphrag`(知识图谱增强RAG)
   - 决策：本项目不需要重型RAG框架（数据都是结构化/半结构化而非复杂文档），自己实现轻量的Embedding+Milvus+混合检索即可，但必须学习上述框架的chunking/reranking策略

2. **Embedding模型选型**：
   - 搜索关键词：`best text embedding model multilingual 2024`, `M3E bge embedding chinese`, `text-embedding-3-large open source alternative`
   - 候选：`BAAI/bge-m3`(多语言长文本，开源SOTA), `BAAI/bge-large-zh-v1.5`(中文最优), `openai/text-embedding-3-large`(效果好但调用费), `nvidia/NV-Embed-v2`
   - 视觉Embedding：`openai/clip-vit-large-patch14`(图文对齐), `google/siglip-base-patch16-256`
   - 决策：
     - 文本Embedding主力：`bge-m3`（本地部署，多语言，支持1024token，开源免费，避免OpenAI API费用）
     - 视觉Embedding：`clip-vit-large-patch14`（本地部署）
     - 可选增强：对英文检索可用OpenAI text-embedding-3-large作为备选
   - 部署方式：用 `text-embeddings-inference`(HF开源推理服务，Tea加速)或 `Infinity` 本地部署Embedding模型，提供HTTP API给各服务调用

3. **Milvus最佳实践**：
   - 参考Milvus官方文档schema设计/index配置
   - 索引类型：IVF_FLAT/HNSW/DiskANN，按数据规模选择（HNSW平衡性能/召回率）
   - 距离度量：COSINE或IP（归一化向量后等价）
   - 必须配置：分片数、副本数、动态字段

4. **中文分词/全文检索**：
   - PostgreSQL `pg_trgm` + `zhparser`/`jieba` 中文分词
   - Elasticsearch（可选，如果数据量超过PG全文检索能力，初期不需要）

5. **Rerank模型**：
   - 搜索关键词：`reranker model chinese`, `bge-reranker`
   - 参考：`BAAI/bge-reranker-v2-m3`(多语言reranker)
   - 决策：接入bge-reranker作为检索后精排步骤，显著提升命中率

6. **知识版本管理**：
   - 搜索：`knowledge graph versioning`, `semantic versioning knowledge base`
   - 参考：Datasaur/Label Studio等数据标注工具的版本管理思路

### Step 2：向量数据库Schema设计与初始化

在Milvus中创建以下Collection（启动时通过Python脚本自动创建）：

#### 2.1 Collections设计

```python
# scripts/init_milvus.py 中定义schema

COLLECTIONS = {
    # 爆款视频文本embedding
    "viral_videos_text": {
        "fields": [
            {"name": "id", "dtype": "VARCHAR", "max_length": 36, "is_primary": True},
            {"name": "video_id", "dtype": "VARCHAR", "max_length": 36},
            {"name": "platform", "dtype": "VARCHAR", "max_length": 32},
            {"name": "category", "dtype": "VARCHAR", "max_length": 64},
            {"name": "title", "dtype": "VARCHAR", "max_length": 512},
            {"name": "text_content", "dtype": "VARCHAR", "max_length": 65535},  # 标题+描述+脚本+标签
            {"name": "viral_score", "dtype": "FLOAT"},
            {"name": "trend_score", "dtype": "FLOAT"},
            {"name": "created_at", "dtype": "INT64"},  # unix timestamp
            {"name": "embedding", "dtype": "FLOAT_VECTOR", "dim": 1024}       # bge-m3
        ],
        "index": {"field": "embedding", "index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}
    },
    # 爆款视频视觉embedding（关键帧CLIP）
    "viral_videos_visual": {
        "fields": [
            {"name": "id", "dtype": "VARCHAR", "max_length": 36, "is_primary": True},
            {"name": "video_id", "dtype": "VARCHAR", "max_length": 36},
            {"name": "shot_id", "dtype": "VARCHAR", "max_length": 36},
            {"name": "keyframe_url", "dtype": "VARCHAR", "max_length": 512},
            {"name": "shot_type", "dtype": "VARCHAR", "max_length": 32},
            {"name": "color_tone", "dtype": "VARCHAR", "max_length": 64},
            {"name": "style_tags", "dtype": "ARRAY", "element_type": "VARCHAR", "max_length": 64, "max_capacity": 20},
            {"name": "embedding", "dtype": "FLOAT_VECTOR", "dim": 768}       # CLIP
        ],
        "index": {"field": "embedding", "index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}
    },
    # 创意理论知识（钩子/结构/CTA等）
    "creative_knowledge": {
        "fields": [
            {"name": "id", "dtype": "VARCHAR", "max_length": 36, "is_primary": True},
            {"name": "knowledge_type", "dtype": "VARCHAR", "max_length": 32},  # hook/structure/cta/emotion/rhythm/genre
            {"name": "name", "dtype": "VARCHAR", "max_length": 256},
            {"name": "category", "dtype": "VARCHAR", "max_length": 64},
            {"name": "content", "dtype": "VARCHAR", "max_length": 65535},     # 知识点完整内容（模板/示例/描述）
            {"name": "tags", "dtype": "ARRAY", "element_type": "VARCHAR", "max_length": 64, "max_capacity": 30},
            {"name": "applicable_scenarios", "dtype": "ARRAY", "element_type": "VARCHAR", "max_length": 64, "max_capacity": 20},
            {"name": "success_rate", "dtype": "FLOAT"},
            {"name": "usage_count", "dtype": "INT64"},
            {"name": "embedding", "dtype": "FLOAT_VECTOR", "dim": 1024}
        ],
        "index": {"field": "embedding", "index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}
    },
    # 提示词知识（术语/技巧/Best Practice）
    "prompt_knowledge": {
        "fields": [
            {"name": "id", "dtype": "VARCHAR", "max_length": 36, "is_primary": True},
            {"name": "knowledge_type", "dtype": "VARCHAR", "max_length": 32},  # term/technique/model_tip/lora/best_practice/bad_case
            {"name": "model_id", "dtype": "VARCHAR", "max_length": 64},        # 适用模型（空=通用）
            {"name": "category", "dtype": "VARCHAR", "max_length": 64},
            {"name": "title", "dtype": "VARCHAR", "max_length": 256},
            {"name": "content", "dtype": "VARCHAR", "max_length": 65535},
            {"name": "examples", "dtype": "VARCHAR", "max_length": 65535},     # 示例JSON
            {"name": "tags", "dtype": "ARRAY", "element_type": "VARCHAR", "max_length": 64, "max_capacity": 30},
            {"name": "embedding", "dtype": "FLOAT_VECTOR", "dim": 1024}
        ],
        "index": {"field": "embedding", "index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}
    },
    # 镜头语言/摄影知识
    "cinematography_knowledge": {
        "fields": [
            {"name": "id", "dtype": "VARCHAR", "max_length": 36, "is_primary": True},
            {"name": "category", "dtype": "VARCHAR", "max_length": 32},        # shot_type/camera_movement/lighting/color/composition/lens/film_stock/format
            {"name": "term_cn", "dtype": "VARCHAR", "max_length": 128},
            {"name": "term_en", "dtype": "VARCHAR", "max_length": 128},
            {"name": "definition", "dtype": "VARCHAR", "max_length": 1024},
            {"name": "visual_effect", "dtype": "VARCHAR", "max_length": 1024},
            {"name": "usage_scenarios", "dtype": "VARCHAR", "max_length": 2048},
            {"name": "prompt_fragment_cn", "dtype": "VARCHAR", "max_length": 512},
            {"name": "prompt_fragment_en", "dtype": "VARCHAR", "max_length": 512},
            {"name": "famous_examples", "dtype": "VARCHAR", "max_length": 2048},  # 知名电影中的例子
            {"name": "tags", "dtype": "ARRAY", "element_type": "VARCHAR", "max_length": 64, "max_capacity": 20},
            {"name": "embedding", "dtype": "FLOAT_VECTOR", "dim": 1024}
        ],
        "index": {"field": "embedding", "index_type": "HNSW", "metric_type": "COSINE"}
    },
    # 用户角色/风格/场景资产（用于"我的资产"跨项目检索）
    "user_assets": {
        "fields": [
            {"name": "id", "dtype": "VARCHAR", "max_length": 36, "is_primary": True},
            {"name": "owner_id", "dtype": "VARCHAR", "max_length": 36},
            {"name": "org_id", "dtype": "VARCHAR", "max_length": 36},
            {"name": "asset_type", "dtype": "VARCHAR", "max_length": 32},    # character/style/scene/prop/script_template
            {"name": "name", "dtype": "VARCHAR", "max_length": 256},
            {"name": "description", "dtype": "VARCHAR", "max_length": 2048},
            {"name": "tags", "dtype": "ARRAY", "element_type": "VARCHAR", "max_length": 64, "max_capacity": 30},
            {"name": "embedding", "dtype": "FLOAT_VECTOR", "dim": 1024}
        ],
        "index": {"field": "embedding", "index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 12, "efConstruction": 150}},
        "partition_key": "owner_id"  # 按用户分区，保证数据隔离+检索效率
    }
}
```

### Step 3：Embedding服务部署

- 在docker-compose.yml中新增 `text-embeddings-inference` 服务（或Infinity），加载 `bge-m3` 模型
- 另起一个 `clip-embedding` 服务（可用 `clip-as-service` 或自建FastAPI包装CLIP），加载 `clip-vit-large-patch14`
- 编写 `services/agent/src/common/embeddings.py` 封装统一Embedding接口：
  ```python
  async def embed_text(texts: list[str]) -> list[list[float]]: ...
  async def embed_images(image_urls: list[str]) -> list[list[float]]: ...
  ```
- 支持批处理（提高吞吐）、自动重试、降级策略（本地Embedding失败时降级到OpenAI API）
- 所有Embedding结果做归一化（COSINE等价于IP）

### Step 4：知识入库Pipeline

实现 `services/agent/src/knowledge/ingestion/` 模块：

```
knowledge/
├── __init__.py
├── ingestion/
│   ├── base.py             # 知识入库基类
│   ├── creative_kb.py      # 创意理论知识入库
│   ├── prompt_kb.py        # 提示词知识入库
│   ├── cinematography_kb.py # 镜头知识入库
│   ├── viral_video_kb.py   # 爆款数据入库（由板块02调用）
│   └── user_asset_kb.py    # 用户资产入库（创建角色/风格时自动入库）
├── retrieval/
│   ├── hybrid_search.py    # 混合检索
│   ├── reranker.py         # Rerank精排
│   ├── query_rewriter.py   # 查询改写（Agent调用前先扩展query）
│   └── filters.py          # 过滤条件构造
└── management/
    ├── version.py          # 版本管理
    ├── quality.py          # 质量检测
    └── admin_api.py        # 管理后台API
```

**入库流程**：
1. 结构化知识（预置JSON）：启动时或手动触发加载脚本，读取JSON → 清洗 → embedding → 批量写入Milvus
2. 爆款视频：分析完成后异步写入viral_videos_text和viral_videos_visual集合
3. 用户资产：创建/更新角色/风格/场景时同步更新user_assets集合
4. Prompt迭代经验：优化Agent每次成功优化后，将"问题→解决方案"写入prompt_knowledge（bad_case类型）

**入库前处理**：
- 文本清洗：去HTML、多余空白、特殊字符
- Chunking（针对长内容如爆款脚本文本）：按语义段落切分，每块512-1024token，保留overlap
- 元数据附加上下文信息（类型、分类、时间、热度分）
- Embedding批量计算（支持GPU加速）

### Step 5：混合检索引擎（核心）

实现 `retrieval/hybrid_search.py`，融合三种检索信号：

1. **向量语义检索**：query embedding → Milvus ANN搜索 → Top-K候选
2. **关键词检索**：对title/tags/category等短文本字段用PostgreSQL全文检索（zhparser中文分词）
3. **元数据过滤**：按category/tags/platform/model_id/asset_type等过滤
4. **Rerank精排**：用bge-reranker对向量召回的Top-N做精排 → 最终Top-K

检索接口设计（供所有Agent调用）：
```python
class KnowledgeRetriever:
    async def search_creative(
        self,
        query: str,                          # 自然语言查询
        knowledge_types: list[str] | None,   # ["hook", "structure"] 或 None=全部
        categories: list[str] | None,
        top_k: int = 5,
        min_score: float = 0.5
    ) -> list[KnowledgeItem]: ...

    async def search_viral_videos(
        self,
        query: str,
        platform: str | None = None,
        category: str | None = None,
        viral_score_min: float | None = None,
        time_range_days: int | None = None,
        top_k: int = 10,
        search_modality: str = "text"  # text/visual/image
    ) -> list[ViralVideoResult]: ...

    async def search_prompt_knowledge(
        self,
        query: str,
        model_id: str | None = None,
        category: str | None = None,
        top_k: int = 5
    ) -> list[PromptKnowledgeItem]: ...

    async def search_cinematography(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 5
    ) -> list[CinematographyItem]: ...

    async def search_user_assets(
        self,
        query: str,
        owner_id: str,
        asset_type: str | None = None,
        top_k: int = 5
    ) -> list[UserAssetItem]: ...
```

**检索增强策略（实现至少3种）**：
1. **Query Rewriting**：用户原始query太简短时（如"钩子"），用LLM扩展为"短视频钩子类型 前3秒抓注意力 抖音爆款hook formula"
2. **Multi-Query检索**：用LLM生成3个不同角度的query分别检索，结果合并去重
3. **HyDE（Hypothetical Document Embeddings）**：对于创意类检索，先用LLM生成一个"理想答案"，用理想答案的embedding检索，提升召回率

### Step 6：知识库初始化（必须亲手构建）

在知识库系统搭建完成后，**必须**把板块03和板块05中设计的预置知识灌入知识库（通过ingestion pipeline）：

1. **创意理论**：100+钩子、30+叙事结构、20+CTA、15+情绪曲线、20+垂类规范、10+节奏模式
2. **提示词知识**：300+专业术语、每个模型的Best Practice和Known Limitations、50+LoRA推荐、100+常见Bad Case修复方案
3. **镜头语言**：额外补充500+条电影摄影专业术语（景别/运镜/光影/色调/构图/镜头/胶片/格式），从专业摄影书籍/IMDb技术资料整理
4. **预置资产**：50+角色、100+风格、100+场景、80+道具（asset_type=preset，owner_id=system）

你必须确保这些知识不是空壳，每条都有实质内容（描述+示例+适用场景+prompt片段）。

### Step 7：知识持续更新机制

1. **爆款拆解自动入库**：板块02每完成一条爆款视频分析，自动提取创意公式、钩子模式、结构特征，去重后入库creative_knowledge
2. **Prompt优化经验入库**：每次用户反馈+成功优化形成一个bad_case→solution条目，自动存入prompt_knowledge
3. **使用频次统计**：每条知识记录被引用次数，高频知识优先展示
4. **质量评分**：知识条目有success_rate字段，实际使用效果数据回流（如使用某钩子的视频完播率高），更新评分
5. **过期淘汰**：超过180天未被引用且评分低的知识标记为deprecated
6. **人工审核**：新自动入库知识默认unverified状态，管理员审核后变为verified才参与推荐

### Step 8：检索API暴露

在Go/Python服务层暴露RESTful API（供前端和其他服务调用）：

| 方法 | 路径 | 功能 |
|:---|:---|:---|
| GET | `/api/v1/knowledge/search` | 通用知识检索（参数：query/type/category/model/top_k） |
| GET | `/api/v1/knowledge/creative` | 创意知识检索 |
| GET | `/api/v1/knowledge/prompts` | 提示词知识检索 |
| GET | `/api/v1/knowledge/cinematography` | 镜头语言知识检索 |
| GET | `/api/v1/knowledge/viral-videos` | 爆款视频语义检索 |
| GET | `/api/v1/knowledge/my-assets` | 我的资产检索 |
| POST | `/api/v1/admin/knowledge/reindex` | 重建索引（管理员） |
| POST | `/api/v1/admin/knowledge/ingest` | 手动触发批量导入 |
| GET | `/api/v1/admin/knowledge/stats` | 知识库统计（各Collection文档数/平均质量分） |

### Step 9：前端知识库浏览页面

在 `apps/web/src/app/knowledge/` 下实现知识库浏览界面（主要供高级用户和管理员使用，普通用户不直接接触）：

```
app/knowledge/
├── page.tsx                    # 知识库首页（统计数据+分类入口）
├── creative/                   # 创意理论浏览
│   └── page.tsx
│       └── components/
│           ├── hook-library.tsx            # 钩子大全浏览/搜索
│           ├── structure-library.tsx       # 叙事结构库
│           ├── knowledge-card.tsx          # 知识卡片（含示例、适用场景）
│           └── apply-to-project-btn.tsx    # 一键应用到当前项目
├── cinematography/             # 镜头语言词典
│   └── page.tsx
│       └── components/
│           ├── term-card.tsx               # 术语卡片（中英文+定义+视觉示例图+prompt片段）
│           ├── term-category-tree.tsx      # 分类树导航
│           └── visual-glossary.tsx         # 视觉化术语表（图+文）
└── admin/                      # 管理后台
    └── page.tsx
        └── components/
            ├── knowledge-stats.tsx         # 统计看板
            ├── pending-review-list.tsx     # 待审核知识
            ├── knowledge-editor.tsx        # 知识条目编辑
            └── reindex-btn.tsx             # 重建索引按钮
```

### Step 10：Agent调用知识的机制

在所有Agent的基类中注入 `KnowledgeRetriever` 实例，Agent在思考前必须先检索相关知识：

- Ideation Agent → 检索"当前热点相关爆款"+"跨领域创意公式"+"钩子类型"
- Storyteller Agent → 检索"叙事结构模板"+"同垂类爆款"
- Hook Specialist → 检索"钩子类型库"+"钩子成功案例"
- Storyboard Agent → 检索"镜头语言术语"+"场景描述最佳实践"
- Prompt Engineer → 检索"模型特定提示词技巧"+"术语翻译"+"LoRA推荐"+"Bad Case修复方案"

在Agent的System Prompt中明确："在做出创意决策前，先用search_creative/search_prompt_knowledge工具检索知识库，引用检索到的模板和案例，不要全凭记忆发挥"。

这是保证输出稳定高质量的关键——Agent**必须**基于知识库事实，而非LLM的"自由发挥"。

### Step 11：数据初始化脚本

编写 `scripts/init_knowledge.py`：
- 检查Milvus连接
- 创建所有Collections（若不存在）
- 读取 `services/agent/src/knowledge/presets/*.json` 预置数据
- 调用embedding服务计算向量
- 批量写入Milvus
- 输出统计信息（各Collection写入条数）
- 幂等：可重复执行，不重复插入（按主键去重）

### Step 12：与数据库的双写一致性

- 关系型数据（角色/风格/爆款视频等）主存PostgreSQL
- Milvus中只存embedding和检索必要的metadata（id+类型+标签+少量文本字段）
- 详细信息通过Milvus返回的video_id/character_id反查PostgreSQL
- 入库时保证双写：先写PG成功再写Milvus，失败重试+死信队列
- 删除/更新时同步删除/更新Milvus对应记录

## 验收标准

- [ ] Docker-compose启动后Milvus+Embedding服务+CLIP服务正常启动
- [ ] 所有Milvus Collections创建成功，索引配置合理
- [ ] Embedding服务可正常处理文本和图片，返回归一化向量
- [ ] 混合检索（向量+关键词+过滤+Rerank）可用，延迟<200ms（Top-10）
- [ ] 所有预置知识（创意100+/术语300+/镜头500+/角色50+/风格100+/场景100+/道具80+）成功入库，可检索到
- [ ] 爆款视频在拆解完成后自动入库，可通过语义搜索找到（如"快节奏美妆种草"能搜到对应视频）
- [ ] 用户角色/风格创建后可通过语义搜索找到（如"温柔职场"能搜到创建的对应角色）
- [ ] Query Rewriting/Multi-Query/HyDE至少3种检索增强策略实现
- [ ] 知识库管理后台可用（查看统计/审核/编辑/重建索引）
- [ ] 前端知识库浏览页面可用，创意知识和镜头语言词典可浏览/搜索/一键应用到项目
- [ ] Agent基类集成KnowledgeRetriever，Agent执行时实际调用知识库（可通过日志验证）
- [ ] 知识持续更新机制正常（爆款拆解后知识增长、Prompt优化后Bad Case入库）
- [ ] 双写一致性保证（PG和Milvus数据一致）
- [ ] 初始化脚本幂等可重复执行
- [ ] `docs/research/06-knowledge-base.md` 调研记录完整（Embedding模型/Rerank/RAG框架选型理由）
- [ ] `make lint && make test` 通过
