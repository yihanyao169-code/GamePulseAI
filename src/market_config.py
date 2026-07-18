from __future__ import annotations


# Single source of truth for Google Play market display and default review language.
REGION_MARKETS = {
    "东亚": {
        "jp": "日本",
        "kr": "韩国",
        "tw": "中国台湾",
        "hk": "中国香港",
    },
    "东南亚": {
        "sg": "新加坡",
        "my": "马来西亚",
        "id": "印度尼西亚",
        "th": "泰国",
        "vn": "越南",
        "ph": "菲律宾",
    },
    "欧洲": {
        "gb": "英国",
        "de": "德国",
        "fr": "法国",
        "es": "西班牙",
        "it": "意大利",
        "pl": "波兰",
    },
    "北美": {
        "us": "美国",
        "ca": "加拿大",
    },
    "拉美": {
        "br": "巴西",
        "mx": "墨西哥",
        "ar": "阿根廷",
        "cl": "智利",
        "co": "哥伦比亚",
    },
    "大洋洲": {
        "au": "澳大利亚",
        "nz": "新西兰",
    },
}


MARKET_CONFIG = {
    "jp": {"label": "日本", "default_language": "ja", "region": "东亚"},
    "kr": {"label": "韩国", "default_language": "ko", "region": "东亚"},
    "tw": {"label": "中国台湾", "default_language": "zh", "region": "东亚"},
    "hk": {"label": "中国香港", "default_language": "zh", "region": "东亚"},
    "sg": {"label": "新加坡", "default_language": "en", "region": "东南亚"},
    "my": {"label": "马来西亚", "default_language": "ms", "region": "东南亚"},
    "id": {"label": "印度尼西亚", "default_language": "id", "region": "东南亚"},
    "th": {"label": "泰国", "default_language": "th", "region": "东南亚"},
    "vn": {"label": "越南", "default_language": "vi", "region": "东南亚"},
    "ph": {"label": "菲律宾", "default_language": "en", "region": "东南亚"},
    "gb": {"label": "英国", "default_language": "en", "region": "欧洲"},
    "de": {"label": "德国", "default_language": "de", "region": "欧洲"},
    "fr": {"label": "法国", "default_language": "fr", "region": "欧洲"},
    "es": {"label": "西班牙", "default_language": "es", "region": "欧洲"},
    "it": {"label": "意大利", "default_language": "it", "region": "欧洲"},
    "pl": {"label": "波兰", "default_language": "pl", "region": "欧洲"},
    "us": {"label": "美国", "default_language": "en", "region": "北美"},
    "ca": {"label": "加拿大", "default_language": "en", "region": "北美"},
    "br": {"label": "巴西", "default_language": "pt", "region": "拉美"},
    "mx": {"label": "墨西哥", "default_language": "es", "region": "拉美"},
    "ar": {"label": "阿根廷", "default_language": "es", "region": "拉美"},
    "cl": {"label": "智利", "default_language": "es", "region": "拉美"},
    "co": {"label": "哥伦比亚", "default_language": "es", "region": "拉美"},
    "au": {"label": "澳大利亚", "default_language": "en", "region": "大洋洲"},
    "nz": {"label": "新西兰", "default_language": "en", "region": "大洋洲"},
}


def market_label(country: str) -> str:
    return MARKET_CONFIG[country]["label"]


def market_region(country: str) -> str:
    return MARKET_CONFIG[country]["region"]


def default_language(country: str, fallback: str = "en") -> str:
    return MARKET_CONFIG.get(country, {}).get("default_language", fallback)
