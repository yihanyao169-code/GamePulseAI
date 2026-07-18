from __future__ import annotations

from collections import Counter
import re

from src.models import AnalysisResult
from src.reporting import sort_category_counts

FRAMEWORK_NAME = "GamePulse AI Evaluation Framework"
FRAMEWORK_VERSION = "v2.0"

SATISFACTION_WEIGHT = 0.55
HEALTH_WEIGHT = 0.45
STRENGTH_BONUS_MAX = 5.0
CONFIDENCE_MIN = 0.70
CONFIDENCE_MAX = 1.00

# 初始经验参数，尚未经过历史数据回归校准。
HEALTH_RISK_NORMALIZATION_FACTOR = 8.0
S4_PENALTY_MULTIPLIER = 200.0
S4_PENALTY_MAX = 15.0
BLOCKING_PENALTY_FLOOR = 3.0

RISK_CATEGORIES = {"BUG", "性能优化", "UI体验", "氪金", "新手引导"}
SEVERITY_WEIGHTS = {"S1": 1, "S2": 3, "S3": 7, "S4": 15}
STRENGTH_TAGS = {"核心玩法", "美术表现", "角色设计", "剧情内容", "活动运营", "社区体验", "音乐表现"}
GENERIC_SHORT_REVIEWS = {"good", "nice", "ok", "okay", "good game", "不错", "好玩", "挺好玩"}
GENERIC_TERMS = {
    "Google",
    "Google Play",
    "Play",
    "Play Store",
    "App",
    "Game",
    "Good",
    "Nice",
    "Okay",
    "Update",
    "Review",
    "Player",
    "Android",
    "Mobile",
    "Arknights",
    "YOSTAR",
    "Please Make",
}
ENGLISH_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "to", "of", "for", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "being", "it", "its", "it's", "they",
    "them", "their", "theirs", "they're", "this", "that", "these", "those", "i",
    "i'm", "i've", "me", "my", "we", "you", "he", "she", "would", "could", "should",
    "can", "may", "might", "very", "really", "just", "still", "also", "thanks",
    "thank", "please", "make", "ve", "ll", "re", "d", "s",
}
PLATFORM_TERMS = {"google", "google play", "play store", "app", "game"}
EVIDENCE_PHRASE_PATTERNS = [
    "login failure",
    "account lost",
    "connection error",
    "crash after login",
    "frame drops",
    "loading time",
    "low gacha rates",
    "expensive packs",
    "pay to win",
    "reward reduction",
    "small text",
    "confusing menu",
    "button placement",
    "navigation issue",
]
EVIDENCE_ANCHOR_WORDS = {
    "login", "failure", "account", "lost", "connection", "error", "crash", "lag",
    "overheating", "loading", "frame", "drops", "gacha", "rates", "expensive",
    "packs", "reward", "reduction", "pay", "win", "text", "menu", "button",
    "placement", "navigation", "issue", "bug", "bugs", "stutter", "freeze",
}
SPECIFIC_KEYWORDS = [
    "角色",
    "英雄",
    "NPC",
    "武器",
    "地图",
    "副本",
    "Boss",
    "BOSS",
    "活动",
    "卡池",
    "玩法",
    "模式",
    "系统",
    "页面",
    "商店",
    "公会",
    "PVP",
    "PvP",
    "赛季",
    "版本",
    "功能",
    "SSR",
    "保底",
    "抽卡",
    "Live2D",
    "登录",
    "闪退",
    "存档",
    "崩溃",
    "地牢",
]

GRADE_SCALE = [
    (90, "S", "优秀"),
    (80, "A", "良好"),
    (70, "B", "中上"),
    (60, "C", "一般"),
    (0, "D", "建议重点优化"),
]


def build_single_market_report(result: AnalysisResult, sample_size: int, excluded_evidence_terms: list[str] | None = None) -> dict:
    import time

    started = time.perf_counter()
    sentiments = _sentiment_percentages(result)
    score_parts = build_evaluation_score(result, sample_size, sentiments)
    category_sentiment_table = build_category_sentiment_table(result)
    evidence = build_game_evidence(result, excluded_terms=excluded_evidence_terms)
    report = {
        **score_parts,
        "confidence": score_parts.get("confidence_level", "未知"),
        "score_reason": _score_reason_with_evidence(score_parts, evidence),
        "evaluation_summary": _evaluation_summary_with_evidence(score_parts, evidence),
        "game_evidence": evidence,
        "overall_summary": _overall_summary(result, sentiments, sample_size, score_parts, evidence),
        "category_insights": _category_insights(result, evidence),
        "strengths": _strengths(result, evidence),
        "pain_points": _pain_points(result, evidence),
        "recommendations": _recommendations(result, evidence),
        "category_sentiment_table": category_sentiment_table,
        "top_negative_categories": _top_negative_categories(category_sentiment_table, 5),
        "sentiment_conclusion": _sentiment_conclusion(result, sentiments, sample_size),
        "analyzed_count": len(result.classified_reviews),
        "failed_count": len(getattr(result, "failed_review_ids", []) or []),
    }
    report["_evaluation_elapsed_seconds"] = time.perf_counter() - started
    return report


def build_evaluation_score(result: AnalysisResult, sample_size: int, sentiments: dict[str, float] | None = None) -> dict:
    sentiments = sentiments or _sentiment_percentages(result)
    if not has_v2_annotations(result):
        return _legacy_unavailable_score()

    player_satisfaction = _player_satisfaction(sentiments)
    health_parts = _product_health(result)
    strength_parts = _strength_bonus(result)
    confidence_parts = _confidence_factor(result, sample_size)
    base_score = min(
        100.0,
        SATISFACTION_WEIGHT * player_satisfaction
        + HEALTH_WEIGHT * health_parts["product_health"]
        + strength_parts["strength_bonus"],
    )
    overall_score = _clamp(base_score * confidence_parts["confidence_factor"], 0, 100)
    grade, grade_label = _grade(overall_score)
    return {
        "framework_name": FRAMEWORK_NAME,
        "framework_version": FRAMEWORK_VERSION,
        "evaluation_available": True,
        "player_satisfaction": round(player_satisfaction, 1),
        "satisfaction_score": round(player_satisfaction, 1),
        "product_health": round(health_parts["product_health"], 1),
        "health_score": round(health_parts["product_health"], 1),
        "strength_bonus": round(strength_parts["strength_bonus"], 1),
        "strength_sources": strength_parts["strength_sources"],
        "base_score": round(base_score, 1),
        "confidence_factor": round(confidence_parts["confidence_factor"], 2),
        "confidence_level": confidence_parts["confidence_level"],
        "confidence_reason": confidence_parts["confidence_reason"],
        "confidence_breakdown": confidence_parts["confidence_breakdown"],
        "overall_score": round(overall_score, 1),
        "overall_score_int": int(round(overall_score)),
        "grade": grade,
        "grade_label": grade_label,
        "score_reason": _score_reason_v2(result, sentiments, health_parts, strength_parts, confidence_parts),
        "evaluation_summary": _evaluation_summary_v2(result, overall_score, confidence_parts),
        "severity_distribution": health_parts["severity_distribution"],
        "raw_risk": health_parts["raw_risk"],
        "risk_ratio": round(health_parts["risk_ratio"], 3),
        "risk_penalty": round(health_parts["risk_penalty"], 1),
        "blocking_penalty": round(health_parts["blocking_penalty"], 1),
        "s4_blocking_ratio": round(health_parts["s4_blocking_ratio"], 3),
        "s4_ratio": round(health_parts["s4_ratio"], 3),
        "s4_penalty": round(health_parts["s4_penalty"], 1),
        "blocking_count": health_parts["blocking_count"],
        "strength_breakdown": strength_parts["strength_breakdown"],
        "score_breakdown": {
            "player_satisfaction": round(SATISFACTION_WEIGHT * player_satisfaction, 1),
            "product_health": round(HEALTH_WEIGHT * health_parts["product_health"], 1),
            "strength_bonus": round(strength_parts["strength_bonus"], 1),
            "base_score": round(base_score, 1),
            "confidence_factor": round(confidence_parts["confidence_factor"], 2),
            "overall_score": round(overall_score, 1),
        },
    }


def has_v2_annotations(result: AnalysisResult) -> bool:
    if not result.classified_reviews:
        return True
    missing_new_fields = 0
    for review in result.classified_reviews:
        if not hasattr(review, "is_blocking") or not hasattr(review, "strength_tags") or not hasattr(review, "severity"):
            missing_new_fields += 1
    return missing_new_fields < len(result.classified_reviews)


def _legacy_unavailable_score() -> dict:
    return {
        "framework_name": FRAMEWORK_NAME,
        "framework_version": FRAMEWORK_VERSION,
        "evaluation_available": False,
        "overall_score": 0.0,
        "overall_score_int": 0,
        "player_satisfaction": 0.0,
        "satisfaction_score": 0.0,
        "product_health": 0.0,
        "health_score": 0.0,
        "strength_bonus": 0.0,
        "strength_sources": [],
        "base_score": 0.0,
        "confidence_factor": 0.0,
        "confidence_level": "旧版标注不可用",
        "confidence_reason": "该分析使用旧版标注，需重新运行分析后才能生成 v2.0 评分。",
        "grade": "N/A",
        "grade_label": "需重新分析",
        "score_reason": "该分析使用旧版标注，缺少 severity、is_blocking 或 strength_tags，需重新运行分析后才能生成 v2.0 评分。",
        "evaluation_summary": "该分析使用旧版标注，需重新运行分析后才能生成 v2.0 评分。",
        "severity_distribution": {"S1": 0, "S2": 0, "S3": 0, "S4": 0},
        "raw_risk": 0,
        "risk_ratio": 0.0,
        "risk_penalty": 0.0,
        "blocking_penalty": 0.0,
        "s4_blocking_ratio": 0.0,
        "s4_ratio": 0.0,
        "s4_penalty": 0.0,
        "blocking_count": 0,
        "strength_breakdown": {"coverage": 0.0, "diversity": 0.0, "evidence": 0.0},
        "confidence_breakdown": {"sample_factor": 0.0, "success_factor": 0.0, "specificity_factor": 0.0, "generic_review_ratio": 0.0},
        "category_sentiment_table": [],
        "top_negative_categories": [],
        "score_breakdown": {},
    }


def _sentiment_percentages(result: AnalysisResult) -> dict[str, float]:
    total = max(len(result.classified_reviews), 1)
    counts = Counter(_normalize_sentiment(review.sentiment) for review in result.classified_reviews)
    return {key: counts.get(key, 0) / total for key in ["正面", "中性", "负面"]}


def _player_satisfaction(sentiments: dict[str, float]) -> float:
    # PDF v2.0: Positive 越高满意度越高，Neutral 计为部分正向。
    return _clamp(100 * (sentiments["正面"] + 0.5 * sentiments["中性"]), 0, 100)


def _product_health(result: AnalysisResult) -> dict:
    valid_count = max(len(result.classified_reviews), 1)
    severity_distribution = {key: 0 for key in ["S1", "S2", "S3", "S4"]}
    raw_risk = 0
    s4_count = 0
    blocking_count = 0
    for review in result.classified_reviews:
        if review.category not in RISK_CATEGORIES:
            continue
        severity = getattr(review, "severity", None)
        if severity in SEVERITY_WEIGHTS:
            severity_distribution[severity] += 1
            raw_risk += SEVERITY_WEIGHTS[severity]
        if severity == "S4":
            s4_count += 1
        if getattr(review, "is_blocking", False):
            blocking_count += 1
    risk_ratio = raw_risk / valid_count
    risk_penalty = risk_ratio * HEALTH_RISK_NORMALIZATION_FACTOR
    s4_ratio = s4_count / valid_count
    s4_penalty = min(S4_PENALTY_MAX, s4_ratio * S4_PENALTY_MULTIPLIER)
    blocking_penalty = max(s4_penalty, BLOCKING_PENALTY_FLOOR if blocking_count > 0 else 0.0)
    product_health = max(0.0, 100 - risk_penalty - blocking_penalty)
    return {
        "product_health": _clamp(product_health, 0, 100),
        "severity_distribution": severity_distribution,
        "raw_risk": raw_risk,
        "risk_ratio": risk_ratio,
        "risk_penalty": risk_penalty,
        "blocking_penalty": blocking_penalty,
        "s4_blocking_ratio": s4_ratio,
        "s4_ratio": s4_ratio,
        "s4_penalty": s4_penalty,
        "blocking_count": blocking_count,
    }


def _strength_bonus(result: AnalysisResult) -> dict:
    tag_counts: Counter[str] = Counter()
    evidence = 0
    for review in result.classified_reviews:
        if _normalize_sentiment(review.sentiment) != "正面":
            continue
        content = review.content.strip().lower()
        if content in GENERIC_SHORT_REVIEWS:
            continue
        tags = [tag for tag in getattr(review, "strength_tags", ()) if tag in STRENGTH_TAGS]
        if tags:
            evidence += 1
            tag_counts.update(tags)
    if not tag_counts:
        return {
            "strength_bonus": 0.0,
            "strength_sources": [],
            "strength_breakdown": {"coverage": 0.0, "diversity": 0.0, "evidence": 0.0},
        }
    valid_count = max(len(result.classified_reviews), 1)
    strength_review_ratio = evidence / valid_count
    top_strength_count = max(tag_counts.values())
    coverage_score = min(2.0, strength_review_ratio * 8)
    diversity_score = min(1.5, len(tag_counts) * 0.3)
    evidence_score = min(1.5, top_strength_count / valid_count * 10)
    bonus = min(STRENGTH_BONUS_MAX, coverage_score + diversity_score + evidence_score)
    return {
        "strength_bonus": round(bonus, 1),
        "strength_sources": [f"{tag}（{count}条）" for tag, count in tag_counts.most_common(3)],
        "strength_breakdown": {
            "coverage": round(coverage_score, 2),
            "diversity": round(diversity_score, 2),
            "evidence": round(evidence_score, 2),
        },
    }


def _confidence_factor(result: AnalysisResult, sample_size: int) -> dict:
    success_count = len(result.classified_reviews)
    attempted_count = max(sample_size, success_count + len(getattr(result, "failed_review_ids", []) or []), 1)
    sample_factor = _clamp(success_count / 100, 0, 1)
    success_factor = _clamp(success_count / attempted_count, 0, 1)
    total = max(sum(result.category_counts.values()), 1)
    generic_ratio = result.category_counts.get("整体评价", 0) / total
    specificity_factor = _clamp(1 - generic_ratio, 0, 1)
    raw_confidence = 0.45 * sample_factor + 0.30 * success_factor + 0.25 * specificity_factor
    factor = _clamp(CONFIDENCE_MIN + (CONFIDENCE_MAX - CONFIDENCE_MIN) * raw_confidence, CONFIDENCE_MIN, CONFIDENCE_MAX)
    reasons = [
        f"样本量得分{sample_factor:.2f}",
        f"分类成功率{success_factor:.1%}",
        f"泛化评论占比{generic_ratio:.1%}",
    ]
    if factor < 0.80:
        level = "数据不足，仅供参考"
    elif factor < 0.90:
        level = "数据基本充分，可作为辅助参考"
    else:
        level = "数据充分，可信度较高"
    reasons.append("语言分布完整统计尚未实现")
    return {
        "confidence_factor": factor,
        "confidence_level": level,
        "confidence_reason": "；".join(reasons),
        "confidence_breakdown": {
            "sample_factor": round(sample_factor, 3),
            "success_factor": round(success_factor, 3),
            "specificity_factor": round(specificity_factor, 3),
            "generic_review_ratio": round(generic_ratio, 3),
        },
    }


def _grade(score: float) -> tuple[str, str]:
    for threshold, grade, label in GRADE_SCALE:
        if score >= threshold:
            return grade, label
    return "D", "建议重点优化"


def build_game_evidence(result: AnalysisResult, excluded_terms: list[str] | None = None) -> dict:
    term_counts: Counter[str] = Counter()
    category_terms: dict[str, Counter[str]] = {}
    category_phrases: dict[str, Counter[str]] = {}
    strength_terms: dict[str, Counter[str]] = {}
    blocking_phrases: Counter[str] = Counter()
    excluded = _normalized_excluded_terms(excluded_terms or [])
    for review in result.classified_reviews:
        terms = _extract_specific_terms(review.content, excluded)
        phrases = _extract_specific_phrases(review.content, excluded)
        for term in terms:
            term_counts[term] += 1
            category_terms.setdefault(review.category, Counter())[term] += 1
            for tag in getattr(review, "strength_tags", ()) or ():
                strength_terms.setdefault(tag, Counter())[term] += 1
        for phrase in phrases:
            category_phrases.setdefault(review.category, Counter())[phrase] += 1
            if getattr(review, "is_blocking", False) or getattr(review, "severity", None) == "S4":
                blocking_phrases[phrase] += 1
    return {
        "top_terms": [{"term": term, "count": count} for term, count in term_counts.most_common(12)],
        "by_category": {
            category: [{"term": term, "count": count} for term, count in counts.most_common(5)]
            for category, counts in category_terms.items()
        },
        "phrases_by_category": {
            category: [{"phrase": phrase, "count": count} for phrase, count in counts.most_common(4)]
            for category, counts in category_phrases.items()
        },
        "by_strength": {
            tag: [{"term": term, "count": count} for term, count in counts.most_common(4)]
            for tag, counts in strength_terms.items()
        },
        "blocking_examples": [{"phrase": phrase, "count": count} for phrase, count in blocking_phrases.most_common(4)],
        "fallback_note": "未识别到足够稳定的角色、系统、活动或具体事件名称时，报告仅使用类别级证据，不编造专有名词。",
    }


def _extract_specific_terms(text: str, excluded_terms: set[str] | None = None) -> list[str]:
    value = str(text or "")
    candidates: list[str] = []
    candidates.extend(_extract_meaningful_english_phrases(value))
    candidates.extend(re.findall(r"[「『《\"]([^」』》\"]{2,32})[」』》\"]", value))
    candidates.extend(re.findall(r"\b[A-Z][A-Za-z0-9'_-]{2,}(?:\s+[A-Z][A-Za-z0-9'_-]{2,}){0,2}\b", value))
    candidates.extend(re.findall(r"\b(?:SSR|SR|UR|PVP|PvP|PVE|PvE|Live2D|UI|NPC|Boss|BOSS|[A-Z]{1,4}-?\d{2,5}|\d+\s*小时)\b", value))
    candidates.extend(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}(?:系统|玩法|副本|商店|卡池|活动|Boss|BOSS|公会|PVP|赛季|地牢|界面|页面|机制|补偿|保底|抽卡|存档|闪退|登录)", value))
    output: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = _clean_evidence_text(candidate)
        if not _is_specific_term(cleaned, excluded_terms or set()):
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output[:12]


def _extract_specific_phrases(text: str, excluded_terms: set[str] | None = None) -> list[str]:
    clauses = re.split(r"[。！？!?；;\n\r,.，]", str(text or ""))
    output: list[str] = []
    for clause in clauses:
        cleaned = _clean_evidence_text(clause)
        if len(cleaned) < 4 or len(cleaned) > 48:
            continue
        if _is_excluded_evidence(cleaned, excluded_terms or set()):
            continue
        if any(keyword.lower() in cleaned.lower() for keyword in SPECIFIC_KEYWORDS):
            output.append(cleaned[:42])
    return output[:8]


def _clean_evidence_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip(" -_:：，。,.!！?？\"'“”‘’"))


def _extract_meaningful_english_phrases(text: str) -> list[str]:
    value = str(text or "").lower()
    phrases: list[str] = []
    for phrase in EVIDENCE_PHRASE_PATTERNS:
        if re.search(rf"\b{re.escape(phrase)}\b", value):
            phrases.append(phrase)
    words = re.findall(r"[a-z][a-z']{2,}", value)
    filtered = [word for word in words if not _is_stop_or_platform_word(word)]
    for size in (3, 2):
        for index in range(0, max(0, len(filtered) - size + 1)):
            candidate = " ".join(filtered[index:index + size])
            if _has_meaningful_english_anchor(candidate):
                phrases.append(candidate)
    return phrases[:12]


def _normalized_excluded_terms(terms: list[str]) -> set[str]:
    output = set()
    for term in terms:
        normalized = _normalize_evidence_key(term)
        if not normalized:
            continue
        output.add(normalized)
        output.update(part for part in re.split(r"[\s._-]+", normalized) if len(part) > 2)
    return output


def _is_excluded_evidence(term: str, excluded_terms: set[str]) -> bool:
    normalized = _normalize_evidence_key(term)
    if not normalized:
        return True
    if normalized in excluded_terms:
        return True
    if normalized in {_normalize_evidence_key(item) for item in GENERIC_TERMS}:
        return True
    if normalized in GENERIC_SHORT_REVIEWS:
        return True
    words = re.findall(r"[a-z][a-z']*", normalized)
    if any(word in excluded_terms for word in words) and not _has_meaningful_english_anchor(normalized):
        return True
    if words and all(_is_stop_or_platform_word(word) or word in excluded_terms for word in words):
        return True
    if len(words) == 1 and (_is_stop_or_platform_word(words[0]) or len(words[0]) < 4):
        return True
    compact = normalized.replace(" ", "")
    return compact in {item.replace(" ", "") for item in excluded_terms}


def _normalize_evidence_key(term: str) -> str:
    value = str(term or "").lower()
    value = re.sub(r"'s\b", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _is_stop_or_platform_word(word: str) -> bool:
    normalized = _normalize_evidence_key(word)
    return normalized in ENGLISH_STOP_WORDS or normalized in PLATFORM_TERMS


def _has_meaningful_english_anchor(term: str) -> bool:
    words = set(re.findall(r"[a-z][a-z']*", str(term or "").lower()))
    return bool(words & EVIDENCE_ANCHOR_WORDS)


def _is_specific_term(term: str, excluded_terms: set[str] | None = None) -> bool:
    if len(term) < 2 or len(term) > 32:
        return False
    if _is_excluded_evidence(term, excluded_terms or set()):
        return False
    has_keyword = any(keyword.lower() in term.lower() for keyword in SPECIFIC_KEYWORDS)
    has_code = bool(re.search(r"[A-Z].*\d|\d+.*(?:小时|h|H)", term))
    has_name_shape = bool(re.search(r"\b[A-Z][A-Za-z0-9'_-]{2,}\b", term))
    has_meaningful_phrase = _has_meaningful_english_anchor(term)
    return has_keyword or has_code or (has_name_shape and len(term) >= 4) or has_meaningful_phrase


def _evidence_terms(evidence: dict, category: str | None = None, strength_tag: str | None = None, limit: int = 2) -> list[str]:
    if strength_tag:
        rows = evidence.get("by_strength", {}).get(strength_tag, [])
    elif category:
        rows = evidence.get("by_category", {}).get(category, [])
    else:
        rows = evidence.get("top_terms", [])
    return [str(row.get("term", "")).strip() for row in rows[:limit] if str(row.get("term", "")).strip()]


def _evidence_phrases(evidence: dict, category: str | None = None, limit: int = 2) -> list[str]:
    if category:
        rows = evidence.get("phrases_by_category", {}).get(category, [])
    else:
        rows = evidence.get("blocking_examples", [])
    return [str(row.get("phrase", "")).strip() for row in rows[:limit] if str(row.get("phrase", "")).strip()]


def _evidence_text(evidence: dict, category: str | None = None, strength_tag: str | None = None, fallback: str = "") -> str:
    terms = _evidence_terms(evidence, category=category, strength_tag=strength_tag, limit=3)
    phrases = _evidence_phrases(evidence, category=category, limit=2)
    pieces = terms or phrases
    if pieces:
        return "评论中具体提到：" + "、".join(pieces[:3]) + "。"
    return fallback or "评论中未提取到足够具体的高频证据词。"


def _score_reason_with_evidence(score_parts: dict, evidence: dict) -> str:
    base = str(score_parts.get("score_reason", ""))
    concrete = _evidence_text(evidence, fallback="当前样本未识别到稳定可引用的具体角色、系统或活动名称。")
    return f"{base}{concrete}"


def _evaluation_summary_with_evidence(score_parts: dict, evidence: dict) -> str:
    base = str(score_parts.get("evaluation_summary", ""))
    concrete = _evidence_text(evidence, fallback="当前样本未出现足够明确的专有名词证据，结论按类别统计生成。")
    return f"{base}{concrete}"


def _score_reason_v2(result: AnalysisResult, sentiments: dict[str, float], health: dict, strength: dict, confidence: dict) -> str:
    return (
        f"玩家满意度由正面{sentiments['正面'] * 100:.1f}%、中性{sentiments['中性'] * 100:.1f}%、负面{sentiments['负面'] * 100:.1f}%计算；"
        f"产品健康度扣分来自严重度风险（raw risk={health['raw_risk']}）和连续S4/阻塞扣分{health['blocking_penalty']:.1f}；"
        f"优势加成为{strength['strength_bonus']:.1f}（覆盖{strength['strength_breakdown']['coverage']:.1f}、多样性{strength['strength_breakdown']['diversity']:.1f}、证据{strength['strength_breakdown']['evidence']:.1f}）；"
        f"可信度系数为{confidence['confidence_factor']:.2f}。"
    )


def _evaluation_summary_v2(result: AnalysisResult, overall_score: float, confidence: dict) -> str:
    risks = [name for name, _count, _pct in _top_categories(result, 4) if name in RISK_CATEGORIES]
    risk_text = "、".join(risks[:2]) or "暂无集中风险"
    if overall_score >= 80:
        quality = "当前玩家满意度较高"
    elif overall_score >= 70:
        quality = "当前反馈整体尚可"
    elif overall_score >= 60:
        quality = "当前体验存在明显改进空间"
    else:
        quality = "当前体验风险较高"
    return f"{quality}，主要风险集中在{risk_text}；本次样本可信度为{confidence['confidence_level']}。"


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_sentiment(value: str) -> str:
    mapping = {"positive": "正面", "neutral": "中性", "negative": "负面", "正面": "正面", "中性": "中性", "负面": "负面"}
    return mapping.get(str(value).strip().lower(), "中性")


def _overall_summary(result: AnalysisResult, sentiments: dict[str, float], sample_size: int, score_parts: dict, evidence: dict) -> str:
    top = _top_categories(result, 3)
    top_names = "、".join(name for name, _, _ in top) or "暂无明显类别"
    positives = "；".join(result.most_satisfied[:2]) or "正向反馈暂不集中"
    pains = "；".join(result.most_unsatisfied[:2]) or "集中痛点暂不明显"
    eval_text = score_parts.get("evaluation_summary", "")
    concrete = _evidence_text(evidence, fallback="当前样本未出现足够稳定的具体角色、系统或活动名称。")
    limit = "当前有效样本量较小，结论仅反映本次抓取样本。" if sample_size < 20 else "结论反映本次抓取样本，仍需结合后续版本持续追踪。"
    return (
        f"{eval_text} {concrete} 高频反馈集中在{top_names}。玩家认可点主要包括：{positives}。"
        f"主要不满集中在：{pains}。{limit}"
    )[:240]


def _category_insights(result: AnalysisResult, evidence: dict) -> list[dict[str, str]]:
    top = _top_categories(result, 5)
    output: list[dict[str, str]] = []
    if top:
        name, count, pct = top[0]
        output.append({"title": f"{name}占比最高（{pct:.1f}%）", "detail": _category_meaning(name, count, pct, evidence)})
    for name, count, pct in top[1:3]:
        output.append({"title": f"{name}位列前列（{pct:.1f}%）", "detail": _category_meaning(name, count, pct, evidence)})
    for risk_name in ["BUG", "性能优化", "氪金"]:
        count = result.category_counts.get(risk_name, 0)
        if count and all(risk_name not in item["title"] for item in output):
            total = max(sum(result.category_counts.values()), 1)
            output.append({"title": f"{risk_name}占比为{count / total * 100:.1f}%", "detail": "该类问题会影响健康度评分，建议结合 S1–S4 严重度继续排查。" + _evidence_text(evidence, category=risk_name, fallback="")})
            break
    return output[:6]


def _strengths(result: AnalysisResult, evidence: dict) -> list[dict[str, str]]:
    tag_counts = Counter(
        tag
        for review in result.classified_reviews
        if _normalize_sentiment(review.sentiment) == "正面"
        for tag in (getattr(review, "strength_tags", ()) or ())
        if tag in STRENGTH_TAGS
    )
    if tag_counts:
        return [
            {
                "title": _theme_title_for_strength(tag),
                "detail": f"{tag}获得具体正向反馈（{count}条），是当前样本中较明确的产品优势信号。"
                + _evidence_text(evidence, strength_tag=tag, fallback=_fallback_specific_scope(tag)),
            }
            for tag, count in tag_counts.most_common(5)
        ]
    if result.most_satisfied:
        return [{"title": _short_title(item, "整体口碑"), "detail": item} for item in result.most_satisfied[:5]]
    return _category_points(result, ["游戏玩法", "美术", "活动运营"], "认可", evidence)


def _pain_points(result: AnalysisResult, evidence: dict) -> list[dict[str, str]]:
    table = build_category_sentiment_table(result)
    pain_rows = [row for row in table if row["负面"] > 0 and row["类别"] != "其他"]
    if pain_rows:
        return [
            {
                "title": _theme_title_for_category(row["类别"]),
                "detail": f"{row['类别']}负面评论{row['负面']}条，负面率{row['负面率']}，是当前样本中需要优先阅读原文确认的痛点方向。"
                + _evidence_text(evidence, category=str(row["类别"]), fallback=_fallback_specific_scope(str(row["类别"]))),
            }
            for row in pain_rows[:5]
        ]
    if result.most_unsatisfied:
        return [{"title": _short_title(item, "痛点反馈"), "detail": item} for item in result.most_unsatisfied[:5]]
    return _category_points(result, ["BUG", "UI体验", "性能优化", "氪金", "新手引导"], "问题", evidence)


def _recommendations(result: AnalysisResult, evidence: dict) -> dict[str, list[dict[str, str]]]:
    table = build_category_sentiment_table(result)
    by_category = {row["类别"]: row for row in table}
    p0: list[dict[str, str]] = []
    p1: list[dict[str, str]] = []
    p2: list[dict[str, str]] = []

    severity_counts = Counter(getattr(review, "severity", None) for review in result.classified_reviews)
    blocking_count = sum(1 for review in result.classified_reviews if getattr(review, "is_blocking", False))
    if by_category.get("BUG", {}).get("负面", 0) or severity_counts.get("S4", 0) or blocking_count:
        row = by_category.get("BUG", {"负面": 0, "负面率": "0.0%"})
        p0.append(_recommendation_for_category("BUG", row, severity_counts, blocking_count, evidence))
    if by_category.get("性能优化", {}).get("负面", 0):
        p0.append(_recommendation_for_category("性能优化", by_category["性能优化"], severity_counts, blocking_count, evidence))
    for category in ["氪金", "UI体验", "新手引导", "游戏玩法"]:
        if by_category.get(category, {}).get("合计", 0):
            p1.append(_recommendation_for_category(category, by_category[category], severity_counts, blocking_count, evidence))
    for category in ["美术", "活动运营", "社交", "整体评价"]:
        if by_category.get(category, {}).get("合计", 0):
            p2.append(_recommendation_for_category(category, by_category[category], severity_counts, blocking_count, evidence))
    if not p1:
        top = table[0] if table else {"类别": "整体评价", "合计": 0, "负面率": "0.0%"}
        p1.append(_recommendation_for_category(str(top["类别"]), top, severity_counts, blocking_count, evidence))
    if not p2:
        p2.append({
            "title": "持续追踪样本",
            "basis": "单次抓取只能反映当前评论样本。",
            "action": "按版本、活动和地区持续复盘类别、严重度、情感和可信度变化。",
            "impact": "形成长期市场反馈基线，帮助产品与发行判断趋势变化。",
        })
    return {"P0": p0[:2] or p1[:1], "P1": p1[:2], "P2": p2[:2]}


def _sentiment_conclusion(result: AnalysisResult, sentiments: dict[str, float], sample_size: int) -> str:
    top_negative = _top_negative_categories(build_category_sentiment_table(result), 1)
    focus = top_negative[0]["类别"] if top_negative else "暂无集中负面类别"
    suffix = "当前样本量较小，情感比例仅作为趋势参考。" if sample_size < 20 else ""
    return f"整体情感{_sentiment_label(sentiments)}，负面评论主要集中在{focus}。{suffix}"


def build_category_sentiment_table(result: AnalysisResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    categories = set(result.category_counts) | {review.category for review in result.classified_reviews}
    for category in categories:
        reviews = [review for review in result.classified_reviews if review.category == category]
        if not reviews:
            continue
        positive = sum(1 for review in reviews if _normalize_sentiment(review.sentiment) == "正面")
        neutral = sum(1 for review in reviews if _normalize_sentiment(review.sentiment) == "中性")
        negative = sum(1 for review in reviews if _normalize_sentiment(review.sentiment) == "负面")
        total = positive + neutral + negative
        rows.append({
            "类别": category,
            "正面": positive,
            "中性": neutral,
            "负面": negative,
            "合计": total,
            "负面率": f"{(negative / total * 100) if total else 0:.1f}%",
            "_negative_rate": negative / total if total else 0,
        })
    rows.sort(key=lambda row: (row["类别"] == "其他", -int(row["合计"]), str(row["类别"])))
    for row in rows:
        row.pop("_negative_rate", None)
    return rows


def _top_negative_categories(table: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    rows = [row for row in table if int(row.get("负面", 0)) > 0]
    rows.sort(key=lambda row: (row["类别"] == "其他", -int(row["负面"]), -int(row["合计"]), str(row["类别"])))
    return rows[:limit]


def _top_categories(result: AnalysisResult, limit: int) -> list[tuple[str, int, float]]:
    sorted_counts = sort_category_counts(result.category_counts)
    total = max(sum(sorted_counts.values()), 1)
    return [(name, count, count / total * 100) for name, count in sorted_counts.items() if count > 0][:limit]


def _category_meaning(name: str, count: int, pct: float, evidence: dict) -> str:
    meanings = {
        "整体评价": "多数评论只表达整体满意或不满，缺少具体细节，适合判断整体口碑，但不足以单独定位功能问题。",
        "UI体验": "玩家对界面、操作或信息呈现反馈集中，应优先检查交互路径、按钮布局和信息可读性。",
        "BUG": "这类问题会直接影响产品健康度，建议结合 S1–S4 严重度与阻塞标记继续追踪。",
        "氪金": "商业化争议即使规模不大，也可能影响长期口碑和付费信任。",
        "游戏玩法": "玩家正在讨论核心玩法体验，应判断反馈是认可机制还是指出平衡性与乐趣问题。",
    }
    return (
        f"共{count}条，占比{pct:.1f}%。"
        + meanings.get(name, "该类别代表玩家在这一体验维度上反馈较集中，建议结合原文拆解具体场景。")
        + _evidence_text(evidence, category=name, fallback=_fallback_specific_scope(name))
    )


def _category_points(result: AnalysisResult, categories: list[str], label: str, evidence: dict) -> list[dict[str, str]]:
    total = max(sum(result.category_counts.values()), 1)
    points = []
    for category in categories:
        count = result.category_counts.get(category, 0)
        if count:
            points.append({
                "title": f"{category}{label}",
                "detail": f"{category}相关评论共{count}条，占比{count / total * 100:.1f}%。"
                + _evidence_text(evidence, category=category, fallback=_fallback_specific_scope(category)),
            })
    return points[:5]


def _short_title(text: str, fallback: str = "反馈要点") -> str:
    cleaned = str(text).strip().replace("：", " ")
    for keyword in ["角色设计", "核心玩法", "整体口碑", "产品稳定性", "抽卡机制", "登录闪退", "资源循环", "运营内容", "UI体验", "性能优化"]:
        if keyword in cleaned:
            return keyword[:10]
    return fallback


def _theme_title_for_strength(tag: str) -> str:
    return {
        "核心玩法": "核心玩法",
        "美术表现": "美术表现",
        "角色设计": "角色设计",
        "剧情内容": "剧情内容",
        "活动运营": "运营内容",
        "社区体验": "社区生态",
        "音乐表现": "音乐表现",
    }.get(tag, "产品优势")


def _theme_title_for_category(category: str) -> str:
    return {
        "BUG": "登录闪退",
        "性能优化": "性能优化",
        "氪金": "抽卡机制",
        "UI体验": "UI体验",
        "新手引导": "新手引导",
        "游戏玩法": "核心玩法",
        "美术": "美术表现",
        "活动运营": "运营内容",
        "社交": "社区生态",
        "整体评价": "整体口碑",
        "其他": "其他反馈",
    }.get(category, category[:10] or "反馈主题")


def _recommendation_for_category(category: str, row: dict[str, object], severity_counts: Counter, blocking_count: int, evidence: dict) -> dict[str, str]:
    count = int(row.get("合计", 0) or 0)
    negative = int(row.get("负面", 0) or 0)
    negative_rate = str(row.get("负面率", "0.0%"))
    evidence_note = _evidence_text(evidence, category=category, fallback=_fallback_specific_scope(category))
    templates = {
        "BUG": {
            "title": "修复登录闪退",
            "basis": f"BUG负面评论{negative}条，负面率{negative_rate}；S3/S4共{severity_counts.get('S3', 0) + severity_counts.get('S4', 0)}条，阻塞标记{blocking_count}条。{evidence_note}",
            "action": "优先复现登录、崩溃、数据丢失和核心功能异常，按S4/S3建立修复清单并回归验证。",
            "impact": "降低崩溃与核心流程中断，提升可用性和留存。",
        },
        "性能优化": {
            "title": "优化性能稳定",
            "basis": f"性能类评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "排查卡顿、发热、掉帧、加载速度和设备兼容性，优先覆盖中低端设备场景。",
            "impact": "改善中低端设备体验，降低卡顿和闪退差评。",
        },
        "氪金": {
            "title": "优化抽卡机制",
            "basis": f"氪金类评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "检查抽卡预期、保底透明度、礼包价值感和福利节奏，优先处理负面评论中的共性表达。",
            "impact": "缓解付费抵触，提升付费信任与长期口碑。",
        },
        "游戏玩法": {
            "title": "优化核心玩法",
            "basis": f"玩法讨论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "结合代表评论拆解战斗节奏、关卡目标、数值压力和长期循环，优先处理高频体验断点。",
            "impact": "提升核心玩法满意度与长期留存。",
        },
        "新手引导": {
            "title": "优化新手引导",
            "basis": f"新手引导评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "梳理前30分钟教程、成长目标、功能解锁和失败反馈，减少理解成本。",
            "impact": "降低学习成本与前期流失。",
        },
        "UI体验": {
            "title": "优化UI体验",
            "basis": f"UI体验评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "检查高频入口、按钮命名、信息层级和返回路径，优先修复影响任务/活动/付费操作的界面问题。",
            "impact": "提升操作效率与信息理解。",
        },
        "美术": {
            "title": "强化美术表现",
            "basis": f"美术评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "保留受认可的角色与画面风格，同时定位负面评论中对清晰度、辨识度或资源品质的具体反馈。",
            "impact": "巩固视觉辨识度和内容传播力。",
        },
        "活动运营": {
            "title": "丰富运营内容",
            "basis": f"活动运营评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "复盘活动奖励、节奏、目标压力和版本内容供给，优先修复参与成本与奖励感知不匹配的问题。",
            "impact": "提升回访动力和版本期活跃稳定性。",
        },
        "社交": {
            "title": "优化社区生态",
            "basis": f"社交评论{count}条，负面率{negative_rate}。{evidence_note}",
            "action": "检查公会、好友、聊天、组队与社区反馈链路，改善协作和表达场景。",
            "impact": "提升玩家关系沉淀和长期留存。",
        },
    }
    return templates.get(category, {
        "title": _theme_title_for_category(category),
        "basis": f"{category}评论{count}条，负面率{negative_rate}。{evidence_note}",
        "action": "优先阅读该类别代表性评论，拆解具体场景并形成可执行任务。",
        "impact": "把用户反馈转化为明确的版本优化方向。",
    })


def _fallback_specific_scope(category_or_tag: str) -> str:
    mapping = {
        "核心玩法": "未识别到稳定专有名词，建议回看核心战斗、Build组合或关卡循环相关原文。",
        "游戏玩法": "未识别到稳定专有名词，建议回看核心战斗、Build组合或关卡循环相关原文。",
        "美术表现": "未识别到稳定专有名词，建议回看角色视觉、立绘、动画或演出相关原文。",
        "美术": "未识别到稳定专有名词，建议回看角色视觉、立绘、动画或演出相关原文。",
        "角色设计": "未识别到稳定角色名，建议回看角色成长、配音、演出或外观相关原文。",
        "活动运营": "未识别到稳定活动名，建议回看活动奖励、版本节奏或赛季内容相关原文。",
        "社区体验": "未识别到稳定社交系统名，建议回看公会、好友、聊天或组队相关原文。",
        "社交": "未识别到稳定社交系统名，建议回看公会、好友、聊天或组队相关原文。",
        "BUG": "未识别到稳定错误码或功能名，建议回看登录、闪退、存档和核心功能异常原文。",
        "性能优化": "未识别到稳定设备或场景名，建议回看卡顿、发热、掉帧和加载场景原文。",
        "氪金": "未识别到稳定卡池或礼包名，建议回看抽卡、保底、价格和重复补偿相关原文。",
        "UI体验": "未识别到稳定页面名，建议回看主界面、商店、活动入口和操作路径相关原文。",
        "新手引导": "未识别到稳定教程名，建议回看新手任务、功能解锁和前期成长相关原文。",
    }
    return mapping.get(category_or_tag, "当前样本未识别到稳定可引用的具体名称，结论按类别统计生成。")


def _sentiment_label(sentiments: dict[str, float]) -> str:
    if sentiments["正面"] >= max(sentiments["中性"], sentiments["负面"]):
        return "偏正面"
    if sentiments["负面"] >= max(sentiments["正面"], sentiments["中性"]):
        return "偏负面"
    return "偏中性"
