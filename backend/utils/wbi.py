"""B 站 WBI 签名工具

B 站 2025-05-26 起对 live API 强制要求 WBI 签名。
签名流程：获取 img_key + sub_key → 计算 mixin key → 参数排序 → MD5 → w_rid
"""

import functools
import hashlib
import time
import urllib.parse
from typing import Any

import httpx

# WBI mixin key 映射表（固定，来自 B 站前端）
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 44, 34,
]

# WBI 密钥获取地址
NAV_API = "https://api.bilibili.com/x/web-interface/nav"

# 缓存的 mixin key，避免每次请求都调 nav API
_cachedMixinKey: str | None = None
_cacheExpireTime: float = 0
CACHE_TTL = 3600  # 缓存 1 小时


async def getMixinKey() -> str:
    """获取 WBI mixin key（带缓存）"""
    global _cachedMixinKey, _cacheExpireTime

    now = time.time()
    if _cachedMixinKey and now < _cacheExpireTime:
        return _cachedMixinKey

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
    }

    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(NAV_API)
        resp.raise_for_status()
        data = resp.json()

    wbiImg = data.get("data", {}).get("wbi_img", {})
    imgKey = wbiImg.get("img_url", "")
    subKey = wbiImg.get("sub_url", "")

    if not imgKey or not subKey:
        raise RuntimeError(f"获取 WBI 密钥失败: img_key={imgKey}, sub_key={subKey}")

    # 从 URL 路径中提取纯 key（去掉 /bfs/wbi/... 前缀和扩展名）
    imgKey = imgKey.rsplit("/", 1)[-1].split(".")[0]
    subKey = subKey.rsplit("/", 1)[-1].split(".")[0]

    rawKey = imgKey + subKey
    mixinKey = "".join(rawKey[i] for i in MIXIN_KEY_ENC_TAB if i < len(rawKey))[:32]

    _cachedMixinKey = mixinKey
    _cacheExpireTime = now + CACHE_TTL
    return mixinKey


def signParams(params: dict[str, Any], mixinKey: str) -> dict[str, Any]:
    """对请求参数进行 WBI 签名

    Args:
        params: 原始参数（不含 w_rid 和 wts）
        mixinKey: mixin key

    Returns:
        签名后的参数字典（含 w_rid 和 wts）
    """
    params["wts"] = int(time.time())

    # 按 key 字母序排序，拼接为 key=value&key=value 格式
    sortedParams = sorted(params.items(), key=lambda x: x[0])
    queryStr = urllib.parse.urlencode(sortedParams)

    # MD5(queryStr + mixinKey)
    signStr = queryStr + mixinKey
    wrid = hashlib.md5(signStr.encode("utf-8")).hexdigest()

    params["w_rid"] = wrid
    return params


@functools.lru_cache(maxsize=1)
def generateBuvid3() -> str:
    """生成本地 buvid3（合法格式，不需要登录）"""
    import uuid

    uid = uuid.uuid4().hex[:32].upper()
    return f"XX-{uid[:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:28]}-{uid[28:]}infoc"
