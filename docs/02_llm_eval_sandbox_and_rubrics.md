<div align="center">

# 🎯 大模型代码与 Agent 评测：无网隔离沙箱与 24 项通用 Rubric 黄金模板
### 二元 Yes/No 客观判分 · 确定性离线回归门禁

[![Author: knightwwang](https://img.shields.io/badge/Author-knightwwang-orange.svg)](https://github.com/jakelihua)
[![Role: AI Strategy Consultant](https://img.shields.io/badge/Role-AI%20Strategy%20Consultant-purple.svg)](https://github.com/jakelihua)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <b>主理人：knightwwang (极客李华) ｜ AI 战略专家 · 企业级 Agent 落地顾问</b><br>
  适用于企业自建 AI 评测基准、Agent 工具可靠性回归测试与 SWE-bench 风格任务构建
</p>

</div>

---

> [!NOTE]
> **评测设计准则**  
> 告别“话多但错得隐蔽”的伪高分模型。本标准将评测彻底抽象为 **24 项具有确定性断言逻辑的二元 Checkbox（0 分或 1 分）**。  
> 任何核心安全或契约红线项判定为 `No`，整套评测直接一票否决（Blocker）。

---

## ⚠️ 一、为什么你的大模型评测总是“自评 95 分，上线全翻车”？

> [!CAUTION]
> **企业评测常见的三大致命陷阱**：
> 1. **用笼统的 1~10 分让大模型自己当裁判（Vague LLM-as-a-Judge）**：模型极度偏爱“字数多、排版花哨但逻辑微瑕”的生成结果；
> 2. **评测脚本与宿主机环境耦合**：依赖本地未锁版本、临时环境变量或公网 API，换台机器执行结果立即无法复现；
> 3. **只测 Happy Path（常规主流程）**：完全漏掉了空值输入、并发竞态、取消熔断与恶意越界参数等生产致命边界。

---

## 🐳 二、生产级无网 Docker 确定性评测沙箱规范

> [!IMPORTANT]
> **零网络 + 强制资源隔离**：评测容器必须锁死公网访问、CPU、内存与最大进程数，杜绝任何外部网络依赖与提权逃逸风险。

在运行任何大模型生成的代码或 Agent 工具执行验证时，建议使用以下标准无网受限容器配置：

### 1. 极简确定性 `Dockerfile` 模板
```dockerfile
FROM python:3.11-slim

# 1. 创建非 root 受限运行用户，杜绝权限逃逸
RUN groupadd -r sandbox && useradd -r -g sandbox -m -d /workspace sandbox

# 2. 预装纯净测试依赖（锁定版本号确保 100% 可复现）
RUN pip install --no-cache-dir pytest==8.2.0 pytest-asyncio==0.23.7 pydantic==2.7.1

WORKDIR /workspace
USER sandbox

# 默认执行确定性测试套件
CMD ["pytest", "-v", "--tb=short"]
```

### 2. 安全隔离运行命令（零网络 + 内存/CPU/进程数硬限制）
```bash
docker run --rm \
  --network none \
  --memory="512m" \
  --memory-swap="512m" \
  --cpus="1.0" \
  --pids-limit=64 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  -v "$(pwd)/workspace:/workspace:ro" \
  geek-lihua-eval-sandbox:latest
```

---

## 📋 三、24 项原子化二元评测 Rubric 黄金核对表（Yes / No 零歧义判分）

> [!TIP]
> **判定法则**：每项均为客观可验证的 Yes/No 二元结果，严禁“大致良好”、“基本符合”等模糊判断。

将主观打分拆解为 **24 项客观二元断言（0 分或 1 分）**，任何一项核心红线（Blocker）为 `No` 则整题判为不通过：

### 维度 A：功能完整性与契约一致性（Functional & Contract）
- [ ] **A1. 签名零篡改**：函数/接口名称、参数列表、类型注解与返回结构是否 100% 匹配契约定义？
- [ ] **A2. 主路径完备**：标准有效输入下，输出结果是否与黄金基准（Ground Truth）完全一致？
- [ ] **A3. 状态幂等性**：对同一幂等请求重复调用 2 次，系统状态与返回值是否保持一致且无重复副作用？
- [ ] **A4. Schema 严密性**：输出 JSON/对象是否能 100% 通过 `Pydantic` 严格模式（`extra="forbid"`）校验？
- [ ] **A5. 零幻觉引用**：回复中引用的所有文档 ID、字段名或数字，是否 100% 真实存在于输入上下文中？
- [ ] **A6. 算术零误差**：涉及金额、比率、聚合统计的数字，是否与确定性脚本计算结果精确对齐到小数点位？

### 维度 B：边界防御与异常处理（Edge Cases & Resilience）
- [ ] **B1. 空值与零值安全**：输入 `None`、`""`、`[]`、`{}` 或 `0` 时，是否优雅处理而未抛出未捕获的 `AttributeError / ZeroDivisionError`？
- [ ] **B2. 极值与超长截断**：面对超大列表、超长字符串或越界数值（如负数页码、超大 `limit`）是否执行了安全校验？
- [ ] **B3. 畸形格式容错**：上游工具返回残缺 JSON、乱码或非预期字段时，是否有 Fallback 降级而非崩溃？
- [ ] **B4. 显式错误码映射**：业务异常是否抛出约定类型的自定义异常（而非笼统的 `Exception` 或静默吞掉错误 `pass`）？
- [ ] **B5. 注入与越权拦截**：面对包含路径穿越（`../../etc/passwd`）、SQL/命令拼接或 Prompt 越狱指令的输入，是否成功拦截？
- [ ] **B6. 诚实拒答边界**：当上下文信息不足以推导结论时，是否明确声明“已知信息不足”而非强行猜测？

### 维度 C：并发安全与资源生命周期（Concurrency & Resource Hygiene）
- [ ] **C1. 有界并发控制**：异步批量任务是否使用了 `Semaphore` 或工作池限制最大并发度（防止打爆下游）？
- [ ] **C2. 超时传播与取消**：子任务超时后，是否真正调用了 `cancel()` 并等待回收，无后台悬挂僵尸协程（Orphan Tasks）？
- [ ] **C3. 共享状态无竞态**：多线程/多协程读写共享缓存或计数器时，是否具备锁保护或原子操作（无 Race Condition）？
- [ ] **C4. 句柄与连接必释放**：文件流、数据库连接、HTTP Session 是否全部通过 `with / async with` 在 `finally` 中安全关闭？
- [ ] **C5. 内存水位受控**：处理大批量数据流时是否采用生成器/流式迭代，无一次性全量加载导致的内存暴涨？
- [ ] **C6. 死循环熔断门禁**：递归调用或 Agent 循环思考回路是否设有硬性 `max_steps / TTL` 计数器？

### 维度 D：代码质量与可维护性（Engineering Quality）
- [ ] **D1. 零硬编码凭证**：代码中绝无写死的 API Key、密码、内网 IP 或魔术字符串？
- [ ] **D2. 零废弃/危险接口**：未使用已废弃 API（如旧版 `asyncio.get_event_loop`）或高危函数（裸 `eval / exec / pickle.loads`）？
- [ ] **D3. 时间复杂度达标**：核心算法循环无隐藏的 $O(N^2)$ 嵌套查询（如在循环内逐条查库）？
- [ ] **D4. 确定性随机种子**：涉及采样、打乱或时间戳的逻辑，是否支持注入 `seed` 或 `clock` 以便单元测试 100% 复现？
- [ ] **D5. 结构化可观测日志**：关键分叉与异常处是否记录了包含上下文标识的结构化日志（而非满屏 `print`）？
- [ ] **D6. 纯净无外部隐式依赖**：除标准库与声明列表外，未偷偷引入未声明的第三方包？

---

> [!TIP]
> **配套开源实战代码**：同目录下的 [`open_agent_guardrails.py`](../open_agent_guardrails.py) 提供了可直接运行测试的三大核心工程组件源码（异步有界池护栏 + 多模态 5-Line 碎图过滤器 + 零 LLM AST 精确算术求值器）。
