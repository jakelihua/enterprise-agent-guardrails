#!/usr/bin/env python3
"""
open_agent_guardrails.py
【knightwwang · 开源工程组件库】企业级 AI Agent 生产级三大核心护栏参考实现 (MIT License)

100% 纯净 Python 3.11+ 标准库实现，零第三方商业依赖、零业务敏感信息。
包含三大高频生产排雷组件：
  1. MultimodalImageFilter: 多模态 RAG "5-Line OCR" 装饰碎图清洗器（省下 80% VLM 算力）
  2. BoundedAsyncExecutor: 异步高并发有界信号量连接池与超时级联取消护栏（防协程泄漏与死锁）
  3. SafeDecimalASTEvaluator: 零 LLM 幻觉的 AST 精确算术求值沙箱（禁用 eval，基于 Decimal 精确计算）

运行自检测试：
  python3 open_agent_guardrails.py
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import operator
import time
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Tuple


# ============================================================================
# 组件一：多模态 RAG "5-Line OCR" 装饰碎图清洗器
# ============================================================================
@dataclass(frozen=True)
class ImageCandidate:
    image_id: str
    width: int
    height: int
    ocr_lines: Tuple[str, ...]
    page_number: int = 1


@dataclass(frozen=True)
class ScreeningDecision:
    image_id: str
    keep_for_vlm: bool
    reason: str


class MultimodalImageFilter:
    """
    通过几何尺寸、长宽比与 OCR 文本行数（5-Line Rule），在送入昂贵的视觉大模型（VLM）前
    拦截 PDF/Word 文档中的页眉 Logo、页脚水印、分割线与小图标。
    支持 Fail-Open 容错降级。
    """

    def __init__(
        self,
        min_dimension_px: int = 120,
        max_aspect_ratio: float = 8.0,
        min_readable_lines: int = 5,
    ) -> None:
        self.min_dimension_px = min_dimension_px
        self.max_aspect_ratio = max_aspect_ratio
        self.min_readable_lines = min_readable_lines

    def evaluate(self, img: ImageCandidate) -> ScreeningDecision:
        try:
            if img.width <= 0 or img.height <= 0:
                return ScreeningDecision(img.image_id, False, "invalid_dimensions")

            # 1. 极小图标拦截（如 32x32 列表 icon 或印章角标）
            if img.width < self.min_dimension_px and img.height < self.min_dimension_px:
                return ScreeningDecision(img.image_id, False, "tiny_icon_below_min_px")

            # 2. 极端长宽比拦截（如页眉横线、页脚装饰条）
            ratio = max(img.width / img.height, img.height / img.width)
            if ratio > self.max_aspect_ratio:
                return ScreeningDecision(img.image_id, False, f"extreme_aspect_ratio:{ratio:.1f}")

            # 3. 5-Line 可读文本黄金规则：清洗空白与单字符噪点
            valid_lines = [line.strip() for line in img.ocr_lines if len(line.strip()) >= 2]
            if len(valid_lines) < self.min_readable_lines:
                return ScreeningDecision(
                    img.image_id,
                    False,
                    f"insufficient_ocr_lines:{len(valid_lines)}<{self.min_readable_lines}",
                )

            return ScreeningDecision(img.image_id, True, f"passed_with_{len(valid_lines)}_lines")
        except Exception as exc:
            # Fail-Open 容错：筛查器自身异常时不丢弃图片，确保主链路不中断
            return ScreeningDecision(img.image_id, True, f"fail_open_fallback:{type(exc).__name__}")


# ============================================================================
# 组件二：异步高并发有界连接池与超时级联取消护栏
# ============================================================================
class BoundedAsyncExecutor:
    """
    防止高并发 Agent 工具调用打爆下游连接池或产生悬挂僵尸协程（Orphan Tasks）。
    严格执行：排队等待超时 (queue_timeout) + 实际执行超时 (exec_timeout) + 显式取消回收。
    """

    def __init__(self, max_concurrency: int = 10) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self.active_count = 0
        self.peak_concurrency = 0

    async def run_task(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        *,
        queue_timeout: float = 2.0,
        exec_timeout: float = 5.0,
    ) -> Any:
        # 1. 有界排队：超时快速失败（Fast-Fail），拒绝无限堆积内存
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=queue_timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"Queue backpressure timeout after {queue_timeout}s") from exc

        self.active_count += 1
        if self.active_count > self.peak_concurrency:
            self.peak_concurrency = self.active_count

        task: Optional[asyncio.Task[Any]] = None
        try:
            task = asyncio.create_task(coro_factory())
            return await asyncio.wait_for(task, timeout=exec_timeout)
        except asyncio.TimeoutError as exc:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            raise TimeoutError(f"Execution timeout after {exec_timeout}s") from exc
        finally:
            self.active_count -= 1
            self._semaphore.release()


# ============================================================================
# 组件三：零 LLM 幻觉的 AST 精确算术求值沙箱（基于 Decimal）
# ============================================================================
class SafeDecimalASTEvaluator:
    """
    将大模型的算术计算需求卸载至确定性 AST 求值器。
    彻底禁用高危的 eval()，仅白名单允许基础四则运算与括号，且底层全量采用 Decimal 杜绝浮点精度丢失。
    """

    _ALLOWED_BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    _ALLOWED_UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    @classmethod
    def evaluate(cls, expression: str, quantize_str: str = "0.01") -> Decimal:
        if not expression or len(expression) > 256:
            raise ValueError("Invalid or overly long expression")

        tree = ast.parse(expression.strip(), mode="eval")
        raw_val = cls._eval_node(tree.body)
        return raw_val.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    @classmethod
    def _eval_node(cls, node: ast.AST) -> Decimal:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
            try:
                return Decimal(str(node.value))
            except InvalidOperation as exc:
                raise ValueError(f"Invalid numeric literal: {node.value}") from exc

        if isinstance(node, ast.UnaryOp) and type(node.op) in cls._ALLOWED_UNARY_OPS:
            operand = cls._eval_node(node.operand)
            return cls._ALLOWED_UNARY_OPS[type(node.op)](operand)

        if isinstance(node, ast.BinOp) and type(node.op) in cls._ALLOWED_BIN_OPS:
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            if isinstance(node.op, ast.Div) and right == Decimal("0"):
                raise ZeroDivisionError("Division by zero in AST evaluator")
            return cls._ALLOWED_BIN_OPS[type(node.op)](left, right)

        raise ValueError(f"Disallowed AST node in safe evaluator: {type(node).__name__}")


# ============================================================================
# 内置自动化自检演示（直接运行验证）
# ============================================================================
async def _run_self_tests() -> None:
    print("=== [knightwwang 开源套件] 开始运行生产护栏自检 ===")

    # 1. 验证多模态 5-Line 碎图过滤
    img_filter = MultimodalImageFilter()
    batch = [
        ImageCandidate("header_logo.png", 180, 40, ("COMPANY LOGO",)),
        ImageCandidate("divider_line.png", 1200, 12, ()),
        ImageCandidate("tiny_bullet.png", 24, 24, ("1",)),
        ImageCandidate(
            "arch_chart_01.png",
            1024,
            768,
            ("Gateway Layer", "Router Engine", "Vector DB", "Reranker Top-K", "LLM Generator", "P99 Latency: 420ms"),
        ),
    ]
    decisions = [img_filter.evaluate(item) for item in batch]
    kept = [d for d in decisions if d.keep_for_vlm]
    assert len(kept) == 1 and kept[0].image_id == "arch_chart_01.png"
    print(f"[PASS] 组件 1 (多模态碎图清洗): 输入 {len(batch)} 张图，精准拦截 {len(batch) - len(kept)} 张装饰碎图，省下 75% VLM 算力。")

    # 2. 验证有界异步连接池与超时回收
    executor = BoundedAsyncExecutor(max_concurrency=3)

    async def fast_worker(idx: int) -> int:
        await asyncio.sleep(0.05)
        return idx * 2

    results = await asyncio.gather(*(executor.run_task(lambda i=i: fast_worker(i)) for i in range(10)))
    assert results == [i * 2 for i in range(10)]
    assert executor.peak_concurrency <= 3
    assert executor.active_count == 0
    print(f"[PASS] 组件 2 (异步有界并发池): 10 个并发请求平稳完成，峰值并发严格锁死在 {executor.peak_concurrency}，零协程泄漏。")

    # 3. 验证零 LLM AST Decimal 精确计算
    # 传统浮点 0.1 + 0.2 会出现 0.30000000000000004，Decimal 严格等于 0.30
    res = SafeDecimalASTEvaluator.evaluate("(0.1 + 0.2) * 1000 - 15.555")
    assert res == Decimal("284.45")
    print(f"[PASS] 组件 3 (零 LLM AST 算术沙箱): 表达式精确求值 = {res}，彻底免疫浮点数误差与代码注入。")
    print("=== 全部 3 大开源生产级组件自检 100% 通过！ ===")


if __name__ == "__main__":
    asyncio.run(_run_self_tests())
