import json
import os
import datetime
import random
import aiohttp

STATISTICS_URL = "https://api.takasumibot.com/v3/statistics"
INITIAL_SUPPLY = 10000000.0
ECONOMY_FILE = "economy_data.json"
USER_DATA_FILE = "users.json"

def load_json(path, default):
    if not os.path.exists(path): return default
    with open(path, "r") as f:
        try: return json.load(f)
        except: return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

async def get_dynamic_base_pool():
    """本家APIの統計データ(userカテゴリ)からベースプールを算出"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STATISTICS_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # 2057.pngの構造通り、user > totalEarn / totalUse を取得
                    user_stats = data.get("user", {})
                    earn = user_stats.get("totalEarn", 0)
                    use = user_stats.get("totalUse", 0)
                    
                    pool = earn - use
                    # 異常値ガード（最低100万を下回らないようにする）
                    return max(pool, 1000000)
    except Exception as e:
        print(f"API Fetch Error (BasePool): {e}")
    
    # 失敗時は以前の基準値（約3.8億）をフォールバックとして返す
    return 380300000

async def get_current_rate():
    """動的なベースプールを使用して最新レートを計算（async化）"""
    data = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    # await を使って最新のベースプールを取得
    current_base = await get_dynamic_base_pool()
    return current_base / data["total_supply"]

async def check_takasumi_assets(user_id, required_amount):
    """本家APIで資産チェック（必要額の10倍あるか）"""
    url = f"https://api.takasumibot.com/v3/profile/{user_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: return False, 0
                data = await resp.json()
                assets = data.get("assets", 0)
                return assets >= (required_amount * 10), assets
    except:
        return False, 0

def process_work(user_id):
    """20分おきのEC獲得処理"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    now = datetime.datetime.now()

    if uid in users and "last_work" in users[uid]:
        last_time = datetime.datetime.fromisoformat(users[uid]["last_work"])
        if now < last_time + datetime.timedelta(minutes=20):
            return False, (last_time + datetime.timedelta(minutes=20) - now)

    reward = round(random.uniform(10, 20), 2)
    econ = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    econ["total_supply"] += reward
    save_json(ECONOMY_FILE, econ)

    if uid not in users: users[uid] = {"balance": 0.0}
    users[uid]["balance"] += reward
    users[uid]["last_work"] = now.isoformat()
    save_json(USER_DATA_FILE, users)
    return True, reward

def request_exchange_lock(user_id, amount):
    """換金申請時のECロック"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    if uid not in users or users[uid]["balance"] < amount:
        return False
    users[uid]["balance"] -= amount
    save_json(USER_DATA_FILE, users)
    return True

async def confirm_exchange_burn(amount):
    """換金承認時：ECを消滅させレートを上げる"""
    econ = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    econ["total_supply"] -= amount
    save_json(ECONOMY_FILE, econ)
    return await get_current_rate()

async def confirm_buy_issue(user_id, amount):
    """購入承認時：ECを新規発行しレートを下げる"""
    econ = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    econ["total_supply"] += amount
    save_json(ECONOMY_FILE, econ)

    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    if uid not in users: users[uid] = {"balance": 0.0}
    users[uid]["balance"] += amount
    save_json(USER_DATA_FILE, users)
    return await get_current_rate()

def sync_game_result_to_supply(amount_change):
    """
    ゲームの結果（損益）を総発行枚数に反映させる。
    amount_changeがプラス（ユーザーの勝利）なら発行枚数が増え、レートが下がる。
    amount_changeがマイナス（ユーザーの敗北）なら発行枚数が減り、レートが上がる。
    """
    econ = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    econ["total_supply"] += amount_change
    # 発行枚数が極端な値にならないようガード（最小100ECなど）
    if econ["total_supply"] < 100: econ["total_supply"] = 100
    save_json(ECONOMY_FILE, econ)
