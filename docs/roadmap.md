# Course Agent 2.0 路线图

## 0. 目的

本文定义 Course Agent 的长期工程方向。

它是一份路线图，不是要求立刻实现所有能力的指令。

当前正在进行的工作由 `docs/current-sprint.md` 决定。

---

# 1. 当前基线

Course Agent 当前是一个可运行的全栈 Agent 原型。

现有能力包括：

### 应用

- Vue 前端；
- FastAPI 后端；
- PostgreSQL；
- Docker Compose；
- 用户注册和登录；
- Argon2 密码哈希；
- JWT 认证；
- 课程和任务 CRUD；
- 多用户数据隔离。

### Agent

- OpenAI Agents SDK；
- DeepSeek OpenAI-compatible 模型；
- function tool calling；
- 任务读/写 Tool；
- 课程资料搜索 Tool；
- SQLiteSession 对话历史。

### 文件/RAG 流程

- PDF / DOCX / TXT / Markdown 上传；
- 文件校验；
- 解析；
- 切块；
- PostgreSQL 文档存储；
- PostgreSQL 全文检索；
- embedding；
- pgvector；
- HNSW 向量索引；
- 语义检索；
- FTS 回退；
- 向前端返回来源元数据。

### 工程能力

- 后端单元测试；
- Docker Compose 部署；
- 基础限流；
- 所有权过滤；
- embedding 重试/回退。

---

# 2. 已知架构限制

当前系统还不是成熟的 Agent 工程系统。

重要的缺失或未完成能力包括：

- 确定性的 Agent Tool 风险策略；
- 通用的人在回路中审批；
- 持久化 Agent state/checkpoint/resume；
- 真正的混合检索；
- 重排序；
- 检索评估；
- Agent 评估；
- 追踪与可观测性；
- SSE / Agent 事件流；
- 请求取消；
- 数据库连接池；
- 版本化数据库迁移；
- 更强的集成/E2E 测试；
- 统一的重试、超时和资源预算。

当前“向量 → FTS”的行为是回退，不是混合检索。

---

# 3. 目标架构理念

长期要探索的核心问题是：

> Agent 应如何获取上下文、基于上下文进行推理，并安全地采取行动？

目标架构应逐步回答：

1. 信息应来自哪里？
2. 应采用哪种检索策略？
3. 现有证据是否足够？
4. Agent 是否应该再次检索？
5. Agent 应采取什么行动？
6. 自动执行是否安全？
7. 该行动是否需要人工审批？
8. 任务是否真的成功？
9. 如何衡量成功或失败？

---

# 阶段 0 — 基线与稳定化

## 目标

在引入重大 Agent 改动前，保留当前系统的可测量版本。

## 工作内容

记录并测量：

- 当前架构；
- Agent 请求流程；
- 检索流程；
- 现有测试；
- 当前向量检索行为；
- 当前 FTS 回退行为；
- 有代表性的延迟；
- 有代表性的 Agent/Tool 行为。

创建初始回归数据集。

## 退出标准

能够将未来实现与原始系统对比，而不是依靠主观印象。

---

# 阶段 1 — 安全可靠的 Agent 后端

## 目标

在提高 Agent 自主性前，解决重要工程风险。

## 工作内容

### Tool 风险策略

将 Tool 分类为：

- READ；
- WRITE；
- DESTRUCTIVE。

引入确定性的授权和策略校验。

不要只依赖 Agent prompt。

### 人工审批基础

破坏性操作不能仅因 LLM 发起请求就执行。

准备可在后续接入持久化工作流的审批模型。

### 异步/阻塞清理

识别异步 endpoint 内的阻塞操作。

将合适的同步工作转移到受控 worker thread，或重新设计执行边界。

不要在没有证据表明有收益时，把整个后端转为异步。

### PostgreSQL 连接管理

引入受控连接池。

### 文件解析安全

加入 PDF 资源限制，例如：

- 页数预算；
- 提取文本预算；
- 解析超时/失败状态。

### 任务删除重设计

移除“删除一个任务就自动创建全数据库 JSON 备份”的设计。

若需要回滚/审计，优先采用明确的审计或软删除策略。

## 退出标准

Agent 写操作具有确定性边界，主要阻塞问题和后端可靠性问题已受控。

---

# 阶段 2 — 后端可靠性

## 目标

把后端从功能原型变为可预测的服务。

## 工作内容

考虑：

- 版本化 schema 迁移；
- 统一错误模型；
- PostgreSQL 集成测试；
- 请求/消息限制；
- session 生命周期限制；
- Provider 超时；
- 重试边界；
- 健康/readiness 检查；
- 结构化日志。

## 退出标准

重要应用行为可以在不同环境中复现和测试。

---

# 阶段 3 — 检索评估

## 目标

在增加更多检索复杂度前，创建可测量的信息检索系统。

## 数据集

构建覆盖以下类别的代表性查询：

- 精确术语；
- 标识符；
- 普通语义问题；
- 跨 chunk 问题；
- 有歧义的问题；
- 无答案问题。

每个案例在可行时应包含 ground truth。

## 基线

分别评估：

- PostgreSQL FTS；
- 当前向量检索。

## 指标

至少考虑：

- Recall@K；
- MRR；
- NDCG；
- 延迟。

保存实验结果。

## 退出标准

能够解释词法检索在哪些场景成功、稠密检索在哪些场景成功，以及两者在哪些场景失败。

---

# 阶段 4 — 混合检索与重排序

## 目标

依据阶段 3 的证据改进检索。

目标流程：

```text
Query
→ lexical retrieval
→ dense retrieval
→ candidate fusion
→ reranking
→ context construction
```

候选融合方式可考虑：

- Reciprocal Rank Fusion（RRF）。

只有在候选检索存在可测量基线后，才应加入重排序。

比较：

1. 仅 FTS；
2. 仅向量；
3. 混合检索；
4. 混合检索 + Reranker。

测量质量、延迟和成本。

## 退出标准

选择的检索栈有项目专属的评估结果支撑。

---

# 阶段 5 — 上下文路由

## 目标

不再把每一个知识问题都路由到同一种检索机制。

候选信息源：

### 结构化 SQL

示例：

- 任务截止日期；
- 优先级；
- 课程/任务状态。

### 词法检索

示例：

- 精确术语；
- 函数名；
- 标识符；
- 术语出现位置。

### 语义 / 混合检索

示例：

- 概念解释；
- 改写后的问题；
- 知识类问题。

### 长上下文

当源材料足够小且有边界、而检索帮助不大时，可考虑使用。

## 评估

创建路由案例并测量路由准确率。

## 退出标准

系统能说明为什么一个查询应走 SQL、词法搜索、语义检索或其他上下文策略。

---

# 阶段 6 — Agentic Retrieval

## 目标

让检索成为可迭代的 Agent 行动，而不是一次固定的预处理步骤。

目标行为：

```text
Question
→ initial retrieval
→ evidence assessment
→ answer if sufficient
OR
→ query rewrite/decomposition
→ additional retrieval
→ evidence assessment
→ answer
```

## 必要控制

Agent 自主性必须有边界。

例如：

- 最大检索轮数；
- 最大检索文档数；
- 最大 Tool 调用次数；
- token/成本预算；
- 无新证据时停止。

## 评估

测量：

- 任务成功；
- 检索轮数；
- 证据覆盖度；
- 延迟；
- 成本；
- 相对单轮检索的改进。

## 退出标准

迭代检索能在单轮检索不足的问题上展现可测量价值。

---

# 阶段 7 — 有状态工作流与人在回路中

## 目标

实现一个真正需要持久状态的工作流。

推荐工作流：

> 根据任务、截止日期和可用时间生成并执行学习计划。

目标流程：

```text
load tasks
→ obtain required user constraints
→ generate plan
→ deterministic constraint validation
→ limited replanning when invalid
→ human approval/edit/reject
→ idempotent database write
```

## 技术

如果 LangGraph 能解决以下问题，可在此阶段引入：

- 状态；
- 条件分支；
- 有界循环；
- checkpoint；
- interrupt；
- resume；
- 人在回路中。

不要仅为框架一致性把普通 Agent Chat 迁移到 LangGraph。

## 确定性约束

应由代码而不是 LLM 校验：

- 截止日期边界；
- 时间冲突；
- 负时长；
- 重复排期；
- 所有权；
- 审批状态。

## 退出标准

工作流能够在中断后恢复，并且未经适当审批不能执行受保护的修改操作。

---

# 阶段 8 — Agent 事件流

## 目标

将 Agent 执行公开为可观测事件流，而不只是返回最终 JSON。

潜在事件类型：

- `agent_start`；
- `retrieval_start`；
- `retrieval_result`；
- `tool_call`；
- `tool_result`；
- `approval_required`；
- `token_delta`；
- `final_answer`；
- `error`。

SSE 是候选传输方式。

要求包括：

- 断开连接处理；
- 取消；
- 错误语义；
- 前端消费。

## 退出标准

前端能展示有意义的 Agent 进度，并安全处理取消和失败。

---

# 阶段 9 — 追踪与 Agent 评估

## 目标

从“Agent 看起来能用”转向可测量的 Agent 工程。

## 追踪

在适当场景记录：

- 模型调用；
- 检索；
- 重排序；
- Tool 调用；
- 参数；
- 审批事件；
- 延迟；
- token 使用量；
- 成本；
- 重试；
- 回退；
- 错误。

## Agent 评估

构建覆盖以下方面的案例：

- 正确 Tool 选择；
- 参数正确性；
- 授权；
- 审批行为；
- 最终任务成功；
- prompt injection 抵抗能力；
- 检索正确性；
- 引用正确性；
- 延迟和成本回归。

候选指标：

- Tool Selection Accuracy；
- Tool Argument Accuracy；
- Task Success Rate；
- Unauthorized Action Rate；
- Retrieval Recall@K；
- Citation Correctness；
- Mean/P95 latency；
- token 使用量；
- 成本。

## 退出标准

模型、prompt、检索或 Agent 改动可在被接受前对照回归数据集测试。

---

# 阶段 10 — 项目完成

当系统具备以下能力后，应停止大规模功能开发：

- 可靠的 Docker 启动；
- 稳定的认证和 CRUD；
- 安全的 Agent Tool；
- 经过测试的检索流程；
- 有评估支持的混合检索；
- 有充分理由的 Context Router；
- 有边界的 Agentic Retrieval；
- 一个持久化 HITL 工作流；
- 事件流；
- 追踪；
- Agent/RAG 评估；
- 有意义的自动化测试；
- 架构文档；
- 已记录的已知限制。

此时，重点应从增加功能转向：

- 面试准备；
- 演示；
- 基准测试；
- 文档；
- bug 修复；
- 开源贡献；
- 提炼可复用的 Agent 评估基础设施。

---

# 未来可选工作

以下内容明确不是完成 Course Agent 的必需项：

- Redis；
- MCP；
- 多 Agent 架构；
- GraphRAG；
- OCR；
- 消息队列；
- 微服务。

只有真实项目需求证明其合理性时，才应引入。

---

# 可能的第二个项目

当评估基础设施在 Course Agent 内部证明有用后，可考虑将其提炼为：

**AgentEval Studio**

可能负责：

- 评估数据集；
- Agent 运行编排；
- trace 对比；
- 指标计算；
- 回归测试；
- 实验对比。

它应从 Course Agent 的真实需求中自然演化，而不是作为一个无关的 demo 单独创建。
