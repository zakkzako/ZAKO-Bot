import random
import json
import os
import datetime
import pytz
import jst
import logging

JST = jst.get_jst()
DATA_FILE = "blackjack_data.json"
logger = logging.getLogger(__name__)

def load_stats():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_result(user_id, result_type, amount_change):
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"win": 0, "loss": 0, "draw": 0, "total_profit": 0.0}
    stats[uid][result_type] += 1
    stats[uid]["total_profit"] += amount_change
    with open(DATA_FILE, "w") as f:
        json.dump(stats, f, indent=4)

    log_now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{log_now}】BJ記録: User:{user_id} Result:{result_type} Change:{amount_change}")

def get_deck():
    suits = ['♠', '♣', '♥', '♦']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [{'suit': s, 'rank': r} for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def calculate_score(hand):
    score = 0
    aces = 0
    for card in hand:
        if card['rank'] in ['J', 'Q', 'K']: score += 10
        elif card['rank'] == 'A':
            aces += 1
            score += 11
        else: score += int(card['rank'])
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def format_hand(hand):
    if not hand: return "なし"
    return " ".join([f"`{c['suit']}{c['rank']}`" for c in hand])
