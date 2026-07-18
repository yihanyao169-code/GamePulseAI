from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any

from src.claude_client import ClaudeClient
from src.models import AnalysisResult, ClassifiedReview, REVIEW_CATEGORIES, ReviewItem


CLASSIFICATION_PROMPT_VERSION = "compact_v2_1"
CLASSIFICATION_SCHEMA_VERSION = "eval_v2_labels"
CLASSIFICATION_MAX_TOKENS = 4096
SUMMARY_MAX_TOKENS = 2048
RISK_CATEGORIES = {"BUG", "性能优化", "UI体验", "氪金", "新手引导"}
STRENGTH_TAGS = {"核心玩法", "美术表现", "角色设计", "剧情内容", "活动运营", "社区体验", "音乐表现"}


@dataclass(frozen=True)
class BatchClassificationResult:
    batch_index: str
    input_count: int
    prompt_length: int
    payload: Any
    raw_preview: str
    raw_returned: bool
    json_success: bool
    response_type: str
    classified_reviews_type: str
    returned_count: int
    parsed_count: int
    success: bool
    error: str = ""
    retry_count: int = 0
    api_called: bool = True
    elapsed_seconds: float = 0.0
    api_started_at: str = ""
    api_ended_at: str = ""
    api_elapsed_seconds: float = 0.0
    json_parse_seconds: float = 0.0
    prompt_tokens_estimate: int = 0
    response_tokens_estimate: int = 0
    queue_wait_seconds: float = 0.0
    retry_sleep_seconds: float = 0.0
    error_type: str = ""
    total_seconds: float = 0.0


def build_classification_prompt(reviews: list[ReviewItem], start_review_id: int = 1) -> str:
    review_lines = "\n".join(
        f'{start_review_id + index}. rating={review.score or "unknown"} text="{review.content}"'
        for index, review in enumerate(reviews)
    )
    categories = "、".join(REVIEW_CATEGORIES)
    strengths = "、".join(sorted(STRENGTH_TAGS))

    return f"""
你是资深游戏用户研究分析师。请为 Google Play 游戏评论输出紧凑结构化标签。

只返回纯 JSON，不要 Markdown，不要代码块，不要解释。
根对象必须是数组，每个元素对应一条输入评论。

字段：
- review_id：必须等于输入编号。
- category：只能是 {categories}。
- sentiment：只能是 positive、neutral、negative。
- severity：风险类别输出 S1/S2/S3/S4；非风险类别输出 null。
- is_blocking：仅无法登录、持续崩溃、数据丢失、核心功能不可用等阻塞核心流程时为 true。
- strength_tags：正面评论有明确优势时输出，可选 {strengths}；否则 []。

风险类别：BUG、性能优化、UI体验、氪金、新手引导。
严重度：
S1 轻微：影响体验但不影响核心功能。
S2 中等：造成明显不便，但存在绕过方法。
S3 严重：影响核心玩法体验，难以绕过。
S4 阻塞：导致玩家无法继续游戏，如闪退、无法登录、数据丢失、核心功能失效。

输出示例：
[
  {{"review_id": 1, "category": "BUG", "sentiment": "negative", "severity": "S3", "is_blocking": false, "strength_tags": []}}
]

评论：
{review_lines}
""".strip()


def parse_json_response(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    array_start = cleaned.find("[")
    object_start = cleaned.find("{")
    starts = [index for index in [array_start, object_start] if index >= 0]
    if not starts:
        raise ValueError("Claude 返回内容不是有效 JSON。")
    start = min(starts)
    if cleaned[start] == "[":
        end = cleaned.rfind("]")
    else:
        end = cleaned.rfind("}")
    if end <= start:
        raise ValueError("Claude 返回内容不是有效 JSON。")
    return json.loads(cleaned[start : end + 1])


def classify_reviews(
    reviews: list[ReviewItem],
    claude_client: ClaudeClient,
    batch_size: int = 25,
    max_workers: int | None = None,
    country: str = "",
) -> AnalysisResult:
    started = time.perf_counter()
    if not reviews:
        return AnalysisResult([], {category: 0 for category in REVIEW_CATEGORIES}, [], [], "", [])

    worker_count = _resolve_worker_count(max_workers)
    indexed_reviews = list(enumerate(reviews, start=1))
    batches = [indexed_reviews[start : start + batch_size] for start in range(0, len(indexed_reviews), batch_size)]

    classified_reviews: list[ClassifiedReview] = []
    batch_diagnostics: list[dict] = []
    failed_review_ids: list[int] = []

    with ThreadPoolExecutor(max_workers=min(worker_count, len(batches))) as executor:
        pending = {}
        next_batch_index = 0
        serial_fallback = False

        def submit_next_batch() -> None:
            nonlocal next_batch_index
            batch_number = next_batch_index + 1
            batch = batches[next_batch_index]
            future = executor.submit(_classify_batch_with_recovery, str(batch_number), batch, claude_client, country, time.perf_counter())
            pending[future] = batch_number
            next_batch_index += 1

        while next_batch_index < min(worker_count, len(batches)):
            submit_next_batch()

        while pending:
            done, _pending = wait(pending.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                pending.pop(future, None)
                reviews_out, diagnostics, failed_ids = future.result()
                classified_reviews.extend(reviews_out)
                batch_diagnostics.extend(diagnostics)
                failed_review_ids.extend(failed_ids)
                if any(item.get("error_type") == "rate_limit" for item in diagnostics):
                    serial_fallback = True

            target_pending = 1 if serial_fallback else worker_count
            while next_batch_index < len(batches) and len(pending) < target_pending:
                submit_next_batch()

    classified_reviews.sort(key=lambda review: int(review.review_id or 0))
    counts = Counter(item.category for item in classified_reviews)
    category_counts = {category: counts.get(category, 0) for category in REVIEW_CATEGORIES}
    positives, negatives = _derive_summary_points(classified_reviews)

    return AnalysisResult(
        classified_reviews=classified_reviews,
        category_counts=category_counts,
        most_satisfied=positives,
        most_unsatisfied=negatives,
        summary="",
        batch_diagnostics=sorted(batch_diagnostics, key=lambda item: _diagnostic_sort_key(str(item["batch"]))),
        failed_review_ids=sorted(set(failed_review_ids)),
        classify_calls=sum(1 for item in batch_diagnostics if item.get("api_called")),
        elapsed_seconds=time.perf_counter() - started,
    )


def summarize_single_market_report(summary_payload: dict, claude_client: ClaudeClient) -> dict:
    prompt = f"""
你是资深游戏产品与发行运营分析师。请基于以下 Python 已计算好的统计结果生成中文管理层总结。
不要计算分数，不要编造输入中没有依据的结论。

最高优先级：
- 所有结论必须优先引用评论中出现的具体游戏内容，例如角色/英雄/NPC/武器/地图/副本/Boss/活动/卡池/玩法模式/系统/UI页面/商店/公会/PVP/赛季/版本/功能/具体错误或事件。
- 优先使用数据中的 game_evidence、top_negative_categories、representative_positive、representative_negative。
- 如果评论没有提供稳定的具体名称，不要编造名称；可以退回到“角色成长系统”“多人副本”“赛季玩法”“抽卡保底机制”等类别级表达。
- 禁止空泛表达，例如“玩法丰富”“角色优秀”“体验良好”“优化空间较大”。每一句都必须能从输入数据或代表评论找到证据。

只返回 JSON：
{{
  "overview": "120-200字整体概括",
  "strengths": ["具体优点1", "具体优点2"],
  "pain_points": ["具体痛点1", "具体痛点2"]
}}

数据：
{json.dumps(summary_payload, ensure_ascii=False)}
""".strip()
    response = claude_client.complete(prompt, max_tokens=SUMMARY_MAX_TOKENS)
    payload = parse_json_response(response)
    if not isinstance(payload, dict):
        raise ValueError("AI Summary 返回 JSON 不是对象。")
    return payload


def summarize_market_comparison(market_summaries: list[dict], claude_client: ClaudeClient) -> str:
    payload = json.dumps(market_summaries, ensure_ascii=False, indent=2)
    prompt = f"""
你是资深游戏发行和本地化分析师。请只基于输入统计数据输出中文跨市场 Overall Insight。

硬性输出规则：
- 不要输出任何报告标题、模板标题或题目复述。
- 不要出现“总结报告”“第一部分”“第二部分”“一、”“二、”“三、”“以下是”“总结如下”“报告如下”。
- 只输出三个小节，且小节名必须严格为：共同优点、共同问题、机会与风险。
- 每个小节输出 2-3 条 bullet，使用 “- ” 开头。
- 每条 bullet 必须引用实际统计数据，优先包含市场名称、类别、满意度、健康度、风险类别、负面率或氪金/BUG/性能占比。
- 不允许编造输入中没有的结论。

输出格式示例（只表示格式，不要照抄内容）：
共同优点
- 美国和英国的玩家满意度较高，正面反馈主要集中在游戏玩法。

共同问题
- 日本的 BUG 占比高于其他市场，产品健康度承压。

机会与风险
- 韩国氪金占比较高，需要关注商业化接受度风险。

数据：
{payload}
""".strip()
    return _clean_market_summary_output(claude_client.complete(prompt, max_tokens=2048))


def _clean_market_summary_output(text: str) -> str:
    banned_prefixes = (
        "跨市场评论分析总结报告",
        "跨市场分析总结报告",
        "总结报告",
        "报告如下",
        "总结如下",
        "以下是",
    )
    cleaned_lines: list[str] = []
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(line.startswith(prefix) for prefix in banned_prefixes):
            continue
        line = re.sub(r"^(第[一二三四五六七八九十]+部分[:：]?\s*)", "", line)
        line = re.sub(r"^[一二三四五六七八九十]+[、.．]\s*", "", line)
        if not line:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _classify_batch_with_recovery(
    batch_index: str,
    batch: list[tuple[int, ReviewItem]],
    claude_client: ClaudeClient,
    country: str,
    submitted_at: float | None = None,
) -> tuple[list[ClassifiedReview], list[dict], list[int]]:
    result = _call_classification_batch(batch_index, batch, claude_client, country, submitted_at)
    if result[0] or len(batch) <= 10:
        return result

    diagnostics = result[1]
    failed_ids: list[int] = []
    classified: list[ClassifiedReview] = []
    for sub_index, start in enumerate(range(0, len(batch), 10), start=1):
        sub_batch = batch[start : start + 10]
        sub_result, sub_diagnostics, sub_failed = _call_classification_batch(f"{batch_index}.{sub_index}", sub_batch, claude_client, country, time.perf_counter())
        classified.extend(sub_result)
        diagnostics.extend(sub_diagnostics)
        failed_ids.extend(sub_failed)
    return classified, diagnostics, failed_ids


def _call_classification_batch(
    batch_index: str,
    batch: list[tuple[int, ReviewItem]],
    claude_client: ClaudeClient,
    country: str,
    submitted_at: float | None = None,
) -> tuple[list[ClassifiedReview], list[dict], list[int]]:
    worker_started = time.perf_counter()
    queue_wait_seconds = max(0.0, worker_started - submitted_at) if submitted_at else 0.0
    first_review_id = batch[0][0]
    reviews = [review for _review_id, review in batch]
    prompt = build_classification_prompt(reviews, first_review_id)
    raw_preview = ""
    last_error = ""
    retry_sleep_seconds = 0.0
    started = worker_started

    for attempt in range(3):
        try:
            api_started_at = time.strftime("%H:%M:%S")
            api_started = time.perf_counter()
            response = claude_client.complete(prompt, max_tokens=CLASSIFICATION_MAX_TOKENS)
            api_ended = time.perf_counter()
            api_ended_at = time.strftime("%H:%M:%S")
            raw_preview = str(response)[:1000]
            parse_started = time.perf_counter()
            payload = parse_json_response(response)
            json_parse_seconds = time.perf_counter() - parse_started
            items = payload.get("classified_reviews", payload) if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                raise ValueError("Claude 返回 JSON 不是数组。")
            classified, failed_ids = _merge_labels(batch_index, batch, items, country)
            diagnostic = BatchClassificationResult(
                batch_index=batch_index,
                input_count=len(batch),
                prompt_length=len(prompt),
                payload=payload,
                raw_preview=raw_preview,
                raw_returned=bool(response),
                json_success=True,
                response_type=type(payload).__name__,
                classified_reviews_type=type(items).__name__,
                returned_count=len(items),
                parsed_count=len(classified),
                success=not failed_ids,
                error="" if not failed_ids else f"缺失或无效 review_id: {failed_ids}",
                retry_count=attempt,
                elapsed_seconds=time.perf_counter() - started,
                api_started_at=api_started_at,
                api_ended_at=api_ended_at,
                api_elapsed_seconds=api_ended - api_started,
                json_parse_seconds=json_parse_seconds,
                prompt_tokens_estimate=_estimate_tokens(prompt),
                response_tokens_estimate=_estimate_tokens(str(response)),
                queue_wait_seconds=queue_wait_seconds,
                retry_sleep_seconds=retry_sleep_seconds,
                error_type="",
                total_seconds=time.perf_counter() - started,
            )
            return classified, [_batch_log(diagnostic, len(classified))], failed_ids
        except Exception as exc:
            last_error = str(exc)
            if attempt < 2:
                retry_sleep_seconds += _sleep_before_retry(last_error, attempt)

    failed_ids = [review_id for review_id, _review in batch]
    diagnostic = BatchClassificationResult(
        batch_index=batch_index,
        input_count=len(batch),
        prompt_length=len(prompt),
        payload=None,
        raw_preview=raw_preview,
        raw_returned=bool(raw_preview),
        json_success=False,
        response_type="",
        classified_reviews_type="",
        returned_count=0,
        parsed_count=0,
        success=False,
        error=last_error,
        retry_count=2,
        elapsed_seconds=time.perf_counter() - started,
        prompt_tokens_estimate=_estimate_tokens(prompt),
        response_tokens_estimate=_estimate_tokens(raw_preview),
        queue_wait_seconds=queue_wait_seconds,
        retry_sleep_seconds=retry_sleep_seconds,
        error_type=_error_type(last_error),
        total_seconds=time.perf_counter() - started,
    )
    return [], [_batch_log(diagnostic, 0)], failed_ids


def _merge_labels(
    batch_index: str,
    batch: list[tuple[int, ReviewItem]],
    items: list[dict],
    country: str,
) -> tuple[list[ClassifiedReview], list[int]]:
    review_map = {review_id: review for review_id, review in batch}
    labels: dict[int, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            review_id = int(item.get("review_id"))
        except (TypeError, ValueError):
            continue
        if review_id in review_map and review_id not in labels:
            labels[review_id] = item

    output: list[ClassifiedReview] = []
    failed_ids = [review_id for review_id in review_map if review_id not in labels]
    for review_id, label in labels.items():
        review = review_map[review_id]
        category = str(label.get("category") or "其他")
        if category not in REVIEW_CATEGORIES:
            category = "其他"
        sentiment = _normalize_sentiment(str(label.get("sentiment", "neutral")))
        severity = label.get("severity")
        severity = str(severity).upper() if severity is not None else None
        if category not in RISK_CATEGORIES or severity not in {"S1", "S2", "S3", "S4"}:
            severity = None
        is_blocking = bool(label.get("is_blocking")) if label.get("is_blocking") is not None else False
        tags = label.get("strength_tags") or []
        if not isinstance(tags, list):
            tags = []
        output.append(
            ClassifiedReview(
                content=review.content,
                category=category,
                sentiment=sentiment,
                reason="",
                severity=severity,
                is_blocking=is_blocking,
                strength_tags=tuple(str(tag) for tag in tags if str(tag) in STRENGTH_TAGS),
                source_batch=_batch_number(batch_index),
                review_id=review_id,
                score=review.score,
                date=review.date,
                version=getattr(review, "version", ""),
                country=country,
                schema_version=CLASSIFICATION_SCHEMA_VERSION,
            )
        )
    return output, failed_ids


def _derive_summary_points(reviews: list[ClassifiedReview]) -> tuple[list[str], list[str]]:
    positives = Counter(tag for review in reviews if _normalize_sentiment(review.sentiment) == "正面" for tag in review.strength_tags)
    negative_categories = Counter(review.category for review in reviews if _normalize_sentiment(review.sentiment) == "负面")
    strengths = [f"{tag}获得正向反馈（{count}条）" for tag, count in positives.most_common(5)]
    pains = [f"{category}负面反馈较集中（{count}条）" for category, count in negative_categories.most_common(5)]
    return strengths, pains


def _batch_log(batch_result: BatchClassificationResult, parsed_count: int) -> dict:
    return {
        "batch": batch_result.batch_index,
        "input_count": batch_result.input_count,
        "prompt_length": batch_result.prompt_length,
        "api_called": batch_result.api_called,
        "raw_returned": batch_result.raw_returned,
        "raw_preview": batch_result.raw_preview,
        "json_success": batch_result.json_success,
        "response_type": batch_result.response_type,
        "classified_reviews_type": batch_result.classified_reviews_type,
        "returned_count": batch_result.returned_count,
        "parsed_count": parsed_count,
        "success": batch_result.success,
        "error": batch_result.error,
        "retry_count": batch_result.retry_count,
        "elapsed_seconds": round(batch_result.elapsed_seconds, 2),
        "api_started_at": batch_result.api_started_at,
        "api_ended_at": batch_result.api_ended_at,
        "api_elapsed_seconds": round(batch_result.api_elapsed_seconds, 3),
        "json_parse_seconds": round(batch_result.json_parse_seconds, 4),
        "prompt_tokens_estimate": batch_result.prompt_tokens_estimate,
        "response_tokens_estimate": batch_result.response_tokens_estimate,
        "queue_wait_seconds": round(batch_result.queue_wait_seconds, 3),
        "retry_sleep_seconds": round(batch_result.retry_sleep_seconds, 3),
        "error_type": batch_result.error_type,
        "total_seconds": round(batch_result.total_seconds or batch_result.elapsed_seconds, 3),
    }


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(str(text)) / 4))


def _resolve_worker_count(max_workers: int | None) -> int:
    if max_workers is not None:
        return max(1, min(2, max_workers))
    try:
        return max(1, min(2, int(os.getenv("CLAUDE_MAX_WORKERS", "2"))))
    except ValueError:
        return 2


def _sleep_before_retry(error: str, attempt: int) -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    if not _should_backoff(error):
        return 0.0
    seconds = 2 if attempt == 0 else 5
    time.sleep(seconds)
    return float(seconds)


def _should_backoff(error: str) -> bool:
    lowered = error.lower()
    return any(term in lowered for term in ["connection", "timeout", "rate", "overload", "temporar"])


def _error_type(error: str) -> str:
    lowered = str(error).lower()
    if "rate" in lowered:
        return "rate_limit"
    if "timeout" in lowered:
        return "timeout"
    if "connection" in lowered:
        return "connection"
    if "overload" in lowered:
        return "overload"
    if "temporar" in lowered:
        return "temporary"
    return "unknown" if error else ""


def _diagnostic_sort_key(value: str) -> tuple[int, int]:
    head, _, tail = value.partition(".")
    return (int(head), int(tail or 0))


def _batch_number(value: str) -> int:
    head, *_rest = value.split(".")
    return int(head)


def _normalize_sentiment(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "positive": "正面",
        "neutral": "中性",
        "negative": "负面",
        "正面": "正面",
        "中性": "中性",
        "负面": "负面",
    }
    return mapping.get(normalized, "中性")


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
