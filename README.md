# 🛡️ Enterprise Agent Guardrails (`enterprise-agent-guardrails`)
### 企业级大模型 Agent、多模态 RAG 与确定性评测沙箱开源实战套件

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Author: Shunchi Wang](https://img.shields.io/badge/Author-Shunchi_Wang_(Jake_Lihua)-orange.svg)](https://github.com/jakelihua)
[![WeChat: 极客李华](https://img.shields.io/badge/WeChat-极客李华-07C160.svg)](https://mp.weixin.qq.com)

> **开源声明**：本工程套件由资深 AI 架构师**王顺驰（极客李华）**主理维护，**100% 基于公开顶会学术论文（Stanford / Anthropic / Princeton / NeurIPS / ICLR）与 Python 3.11+ 标准生态从零实现**。采用 MIT 开源协议，不包含任何特定商业机密与专有业务数据，可供广大开发者、架构师复用于生产环境自检。

---

## 📦 核心开源套件清单

| 模块 / 组件 | 路径 / 源码 | 核心解决痛点 |
| :--- | :--- | :--- |
| **01 生产防崩盘清单** | [`docs/01_production_rag_agent_checklist.md`](./docs/01_production_rag_agent_checklist.md) | 涵盖 KV Cache 保护、多模态 5-Line 碎图过滤、跨页表格表头注入、高并发防死循环等 20 道上线生死线。 |
| **02 客观评测沙箱模板** | [`docs/02_llm_eval_sandbox_and_rubrics.md`](./docs/02_llm_eval_sandbox_and_rubrics.md) | 告别“自评 95 分、上线全翻车”！提供无网受限 Docker 评测沙箱与 24 项二元 Yes/No 客观判分核对表。 |
| **03 生产级 Python 护栏** | [`open_agent_guardrails.py`](./open_agent_guardrails.py) | **零第三方依赖、开箱即跑的三大生产级护栏**：<br/>① `MultimodalImageFilter`（多模态 5-Line 碎图清洗，省 75% 算力）<br/>② `BoundedAsyncExecutor`（异步有界并发池与级联超时取消）<br/>③ `SafeDecimalASTEvaluator`（基于 Decimal 的 AST 精确算术沙箱，彻底免疫注入与浮点误差） |
| **04 架构师顶会精读地图** | [`docs/03_2026_agent_rag_papers_roadmap.md`](./docs/03_2026_agent_rag_papers_roadmap.md) | 提炼 20 篇改变工业界走向的顶会论文（Lost in the Middle / DSPy / SWE-bench / ColPali / HippoRAG / vLLM 等），每篇给出**一句工程人话 + 生产落地动作**。 |

---

## ⚡ 30 秒快速运行与自检验证

本项目零外部依赖，直接基于 Python 3.11+ 标准库运行：

```bash
git clone https://github.com/jakelihua/enterprise-agent-guardrails.git
cd enterprise-agent-guardrails
python3 open_agent_guardrails.py
```

自检输出：
```text
=== [极客李华开源套件] 开始运行生产护栏自检 ===
[PASS] 组件 1 (多模态碎图清洗): 输入 4 张图，精准拦截 3 张装饰碎图，省下 75% VLM 算力。
[PASS] 组件 2 (异步有界并发池): 10 个并发请求平稳完成，峰值并发严格锁死在 3，零协程泄漏。
[PASS] 组件 3 (零 LLM AST 算术沙箱): 表达式精确求值 = 284.45，彻底免疫浮点数误差与代码注入。
=== 全部 3 大开源生产级组件自检 100% 通过！ ===
```

---

## 🤝 关于作者与技术支持

- **作者**：王顺驰（Shunchi Wang / Jake Lihua），资深 AI 架构师 ｜ 前鹅厂研发 ｜ 大模型后训练金牌考官
- **微信公众号**：**【极客李华】**（专注企业级大模型与生产 Agent 深度排雷、架构实操复盘）
- **CSDN 博客**：10.6 万+ 粉丝博客专家，220 万+ 开发者阅读
- **开源协议**：MIT License —— 欢迎 Star、Fork 并用于企业生产环境！