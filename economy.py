import json
import os
import datetime
import random
import aiohttp
import logging

STATISTICS_URL = "https://api.takasumibot.com/v3/statistics"
INITIAL_SUPPLY = 10000000.0
ECONOMY_FILE = "economy_data.json"
USER_DATA_FILE = "users.json"

logger = logging.getLogger(__name__)

def load_json(path, default):
    if not os.path.exists(path): return default
    with open(path, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            return default

def save_json(path, data):
    """
    原子書き込みを行う: 一時ファイルを書き込み後 os.replace で置換
    """
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        # cleanup tmp if exists
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

async def get_dynamic_base_pool():
    """本家APIの統計データ(userカテゴリ)からベースプールを算出"""
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(STATISTICS_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user_stats = data.get("user", {})
                    earn = user_stats.get("totalEarn", 0)
                    use = user_stats.get("totalUse", 0)
                    pool = earn - use
                    return max(pool, 1000000)
                else:
                    logger.error(f"API returned non-200 status: {resp.status}")
    except Exception as e:
        logger.error(f"API Fetch Error (BasePool): {e}")
    return 380300000

async def get_current_rate():
    """動的なベースプールを使用して最新レートを計算（async化）"""
    data = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    current_base = await get_dynamic_base_pool()
    return current_base / data["total_supply"]

async def check_takasumi_assets(user_id, required_amount):
    """本家APIで資産チェック（購入用：必要額の1.5倍あるか）"""
    url = f"https://api.takasumibot.com/v3/profile/{user_id}"
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200: 
                    logger.error(f"check_takasumi_assets: non-200 status {resp.status}")
                    return False, 0
                data = await resp.json()
                assets = data.get("assets", 0)
                return assets >= (required_amount * 1.5), assets
    except Exception as e:
        logger.error(f"check_takasumi_assets error: {e}")
        return False, 0

def process_work(user_id):
    # 既存実装を維持（必要に応じてここも安全化）
    pass
