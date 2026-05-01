import os
import datetime
import random
import aiohttp
import logging
import database

STATISTICS_URL = "https://api.takasumibot.com/v3/statistics"
INITIAL_SUPPLY = 10000000.0

logger = logging.getLogger(__name__)

async def user_exists(user_id):
    row = await database.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    return row is not None

async def get_total_supply():
    """総発行枚数をDBから取得するヘルパー関数"""
    row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'total_supply'")
    if row:
        return float(row['value'])
    return INITIAL_SUPPLY

async def set_total_supply(amount):
    """総発行枚数をDBに保存するヘルパー関数"""
    amount = max(amount, 100.0) # 最小100ECのガード
    await database.execute_query("UPDATE system_config SET value = ? WHERE key = 'total_supply'", (str(amount),))

async def get_dynamic_base_pool():
    """本家APIの統計データ(userカテゴリ)からベースプールを算出"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STATISTICS_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user_stats = data.get("user", {})
                    earn = user_stats.get("totalEarn", 0)
                    use = user_stats.get("totalUse", 0)
                    pool = earn - use
                    return max(pool, 1000000)
    except Exception as e:
        logger.error(f"API Fetch Error (BasePool): {e}")
    return 380300000

async def get_current_rate(force_refresh: bool = False):
    """キャッシュ優先でレートを返す。
    デフォルトでは DB(system_config.key='rate') に保存された値を優先して返す。
    `force_refresh=True` の場合は常に動的に計算して返す（更新ループ用）。
    フォールバックで動的計算を行う。"""
    if not force_refresh:
        try:
            row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'rate'")
            if row and row['value'] is not None:
                try:
                    return float(row['value'])
                except Exception:
                    logger.debug("Failed to parse cached rate; falling back to dynamic calculation")
        except Exception as e:
            logger.error(f"Failed to read cached rate: {e}")

    # フォールバック／強制再計算: 動的計算
    total_supply = await get_total_supply()
    current_base = await get_dynamic_base_pool()
    return current_base / total_supply


async def get_cached_rate():
    """DBに保存されたキャッシュ値を返す。キャッシュが存在しない場合は None を返す。"""
    try:
        row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'rate'")
        if row and row['value'] is not None:
            try:
                return float(row['value'])
            except Exception:
                logger.debug("Failed to parse cached rate")
        return None
    except Exception as e:
        logger.error(f"Failed to read cached rate: {e}")
        return None

async def check_takasumi_assets(user_id, required_amount):
    """本家APIで資産チェック（購入用：必要額の1.5倍あるか）"""
    url = f"https://api.takasumibot.com/v3/profile/{user_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: return False, 0
                data = await resp.json()
                assets = data.get("assets", 0)
                return assets >= (required_amount * 1.5), assets
    except:
        return False, 0

async def add_money(user_id, amount):
    """ユーザーのEC残高を増やす"""
    await database.execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    await database.execute_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

async def remove_money(user_id, amount):
    """ユーザーのEC残高を減らす"""
    row = await database.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    if not row or row['balance'] < amount:
        return False
    await database.execute_query("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    return True

async def set_money(user_id, amount):
    """ユーザーのEC残高を設定する"""
    await database.execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    await database.execute_query("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))

async def process_work(user_id):
    """45分おきのEC獲得処理"""
    now = datetime.datetime.now()

    row = await database.fetch_one("SELECT last_work FROM users WHERE user_id = ?", (user_id,))

    if row and row['last_work']:
        last_time = datetime.datetime.fromisoformat(row['last_work'])
        if now < last_time + datetime.timedelta(minutes=45):
            return False, (last_time + datetime.timedelta(minutes=45) - now)

    reward = round(random.uniform(10, 20), 2)

    current_supply = await get_total_supply()
    await set_total_supply(current_supply + reward)

    await database.execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    await database.execute_query(
        "UPDATE users SET balance = balance + ?, last_work = ? WHERE user_id = ?",
        (reward, now.isoformat(), user_id)
    )

    logger.debug(f"User {user_id} earned {reward} EC")
    return True, reward

async def collect_ec_for_exchange(user_id, amount_ec):
    """換金申請用：手数料10%を含めたECを即座に徴収する"""
    total_needed = amount_ec * 1.1
    row = await database.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))

    if not row or row['balance'] < total_needed:
        return False, 0

    await database.execute_query("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_needed, user_id))
    return True, total_needed

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
    """換金承認時：回収済みのECを供給量から減らし（バーン）、レートを上昇させる"""
    current_supply = await get_total_supply()
    await set_total_supply(current_supply - amount)
    return await get_current_rate()

async def confirm_buy_issue(user_id, amount):
    """購入承認時：ECを新規発行しレートを下げる"""
    current_supply = await get_total_supply()
    await set_total_supply(current_supply + amount)

    await database.execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    await database.execute_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    return await get_current_rate()

async def sync_game_result_to_supply(amount_change):
    """ゲームの結果（損益）を総発行枚数に反映させる。"""
    current_supply = await get_total_supply()
    await set_total_supply(current_supply + amount_change)

async def check_exchange_limit(user_id, amount_ec, current_rate):
    """1日の換金制限(20,000 Money)をチェックする"""
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    requested_money = amount_ec * current_rate
    limit_money = 20000.0

    await database.execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    row = await database.fetch_one("SELECT daily_exchange_total, last_exchange_date FROM users WHERE user_id = ?", (user_id,))

    daily_total = row['daily_exchange_total'] if row else 0.0
    last_date = row['last_exchange_date'] if row else ""

    if last_date != now_date:
        daily_total = 0.0

    if daily_total + requested_money > limit_money:
        remaining = limit_money - daily_total
        return False, remaining

    return True, 0

async def add_exchange_record(user_id, amount_ec, current_rate):
    """換金成功時にその日の累計額を加算して保存する"""
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    requested_money = amount_ec * current_rate

    await database.execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    row = await database.fetch_one("SELECT daily_exchange_total, last_exchange_date FROM users WHERE user_id = ?", (user_id,))

    daily_total = row['daily_exchange_total'] if row else 0.0
    last_date = row['last_exchange_date'] if row else ""

    if last_date != now_date:
        daily_total = 0.0

    new_total = daily_total + requested_money
    await database.execute_query(
        "UPDATE users SET daily_exchange_total = ?, last_exchange_date = ? WHERE user_id = ?",
        (new_total, now_date, user_id)
    )
