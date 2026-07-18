from __future__ import annotations

from src import theme


def prepare_chart_category_data(category_counts: dict[str, int], top_n: int = 6) -> list[dict]:
    items = [
        (category, count)
        for category, count in category_counts.items()
        if count > 0 and category != "其他"
    ]
    items.sort(key=lambda item: (-item[1], item[0]))
    other_count = category_counts.get("其他", 0)

    top_items = items[:top_n]
    merged_other = other_count + sum(count for _, count in items[top_n:])
    if merged_other > 0:
        top_items.append(("其他类别", merged_other))

    total = sum(count for _, count in top_items) or 1
    output = []
    for index, (category, count) in enumerate(top_items):
        output.append(
            {
                "category": category,
                "count": count,
                "percent": count / total * 100,
                "color": theme.CHART_PALETTE[index % len(theme.CHART_PALETTE)],
            }
        )
    return output
