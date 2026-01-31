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

def user_exists(user_id):
    users = load_json(USER_DATA_FILE, {})
    return str(user_id) in users

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
        logger.error(f"API Fetch Error (BasePool): {e}")
    
    # 失敗時は以前の基準値（約3.8億）をフォールバックとして返す
    return 380300000

async def get_current_rate():
    """動的なベースプールを使用して最新レートを計算（async化）"""
    data = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    # await を使って最新のベースプールを取得
    current_base = await get_dynamic_base_pool()
    return current_base / data["total_supply"]

async def check_takasumi_assets(user_id, required_amount):
    """本家APIで資産チェック（購入用：必要額の1.5倍あるか）"""
    url = f"https://api.takasumibot.com/v3/profile/{user_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: return False, 0
                data = await resp.json()
                assets = data.get("assets", 0)
                # 仕様変更：換金額の1.5倍が必要
                return assets >= (required_amount * 1.5), assets
    except:
        return False, 0

def add_money(user_id, amount):
    """ユーザーのEC残高を増やす"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    if uid not in users: users[uid] = {"balance": 0.0}
    users[uid]["balance"] += amount
    save_json(USER_DATA_FILE, users)

def remove_money(user_id, amount):
    """ユーザーのEC残高を減らす"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    if uid not in users: return False
    if users[uid]["balance"] < amount: return False
    users[uid]["balance"] -= amount
    save_json(USER_DATA_FILE, users)

def set_money(user_id, amount):
    """ユーザーのEC残高を設定する"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    if uid not in users: users[uid] = {"balance": 0.0}
    users[uid]["balance"] = amount
    save_json(USER_DATA_FILE, users)

def process_work(user_id):
    """40分おきのEC獲得処理"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    now = datetime.datetime.now()

    if uid in users and "last_work" in users[uid]:
        last_time = datetime.datetime.fromisoformat(users[uid]["last_work"])
        if now < last_time + datetime.timedelta(minutes=40):
            return False, (last_time + datetime.timedelta(minutes=40) - now)

    reward = round(random.uniform(10, 20), 2)
    econ = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    econ["total_supply"] += reward
    save_json(ECONOMY_FILE, econ)

    if uid not in users: users[uid] = {"balance": 0.0}
    users[uid]["balance"] += reward
    users[uid]["last_work"] = now.isoformat()
    save_json(USER_DATA_FILE, users)

    logger.info(f"User {user_id} earned {reward} EC")
    return True, reward

def collect_ec_for_exchange(user_id, amount_ec):
    """換金申請用：手数料10%を含めたECを即座に徴収する"""
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    # 換金希望額 + 手数料10%
    total_needed = amount_ec * 1.1
    
    if uid not in users or users[uid]["balance"] < total_needed:
        return False, 0
        
    users[uid]["balance"] -= total_needed
    save_json(USER_DATA_FILE, users)
    return True, total_needed

# 古い request_exchange_lock は新しい collect_ec_for_exchange に統合されました

async def confirm_exchange(amount, to, user_id=None):
    if to == "ec":
        rate = await confirm_buy_issue(user_id, amount)
        return rate
    elif to == "tc":
        rate = await confirm_exchange_burn(amount)
        return rate
    else:
        raise ValueError("Invalid exchange target")

async def confirm_exchange_burn(amount):
    """
    換金承認時：回収済みのECを供給量から減らし（バーン）、レートを上昇させる
    """
    econ = load_json(ECONOMY_FILE, {"total_supply": INITIAL_SUPPLY})
    # 回収されたECの分だけ、総発行枚数を減らす
    econ["total_supply"] -= amount
    save_json(ECONOMY_FILE, econ)
    
    # 最新レートを計算して返す
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

def check_exchange_limit(user_id, amount_ec, current_rate):
    """
    1日の換金制限(20,000 Money)をチェックする
    """
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    requested_money = amount_ec * current_rate
    limit_money = 20000.0

    if uid not in users:
        users[uid] = {"balance": 0.0, "last_exchange_date": "", "daily_exchange_total": 0.0}

    user_data = users[uid]
    
    # 日付が変わっていたら累計をリセット
    if user_data.get("last_exchange_date") != now_date:
        user_data["last_exchange_date"] = now_date
        user_data["daily_exchange_total"] = 0.0

    # 制限チェック
    if user_data["daily_exchange_total"] + requested_money > limit_money:
        remaining = limit_money - user_data["daily_exchange_total"]
        return False, remaining

    return True, 0

def add_exchange_record(user_id, amount_ec, current_rate):
    """
    換金成功時にその日の累計額を加算して保存する
    """
    users = load_json(USER_DATA_FILE, {})
    uid = str(user_id)
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    requested_money = amount_ec * current_rate

    # 確実にデータ構造がある状態にする
    if uid not in users: return 

    users[uid]["daily_exchange_total"] = users[uid].get("daily_exchange_total", 0.0) + requested_money
    users[uid]["last_exchange_date"] = now_date
    save_json(USER_DATA_FILE, users)
    