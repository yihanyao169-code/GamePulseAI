from __future__ import annotations


def sort_category_counts(category_counts: dict[str, int]) -> dict[str, int]:
    other_count = category_counts.get("其他")
    non_zero_items = [
        (category, count)
        for category, count in category_counts.items()
        if category != "其他" and count > 0
    ]
    zero_items = [
        (category, count)
        for category, count in category_counts.items()
        if category != "其他" and count == 0
    ]
    sorted_items = sorted(non_zero_items, key=lambda item: (-item[1], item[0]))
    sorted_items.extend(sorted(zero_items, key=lambda item: item[0]))
    if other_count is not None:
        sorted_items.append(("其他", other_count))
    return dict(sorted_items)
