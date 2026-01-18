import os
import json
import datetime
import logging
import jst

JST = jst.get_jst()
DATA_FILE = "blackjack_stats.json"
logger = logging.getLogger(__name__)

def load_stats():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading blackjack stats: {e}")
        return {}

def save_result(user_id, result_type, amount_change):
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"win": 0, "loss": 0, "draw": 0, "total_profit": 0.0}
    if result_type not in ("win", "loss", "draw"):
        logger.warning(f"Invalid blackjack result_type: {result_type}")
        return
    stats[uid][result_type] += 1
    stats[uid]["total_profit"] += amount_change
    tmp = f"{DATA_FILE}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        logger.error(f"Error saving stats: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

    log_now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{log_now}】BJ記録: User:{user_id} Result:{result_type} Change:{amount_change}")
