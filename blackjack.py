import random
import datetime
import jst
import logging
import database

JST = jst.get_jst()
logger = logging.getLogger(__name__)

async def save_result(user_id, result_type, amount_change):
    # まずユーザーの戦績レコードが存在するか確認し、無ければ作成
    await database.execute_query("INSERT OR IGNORE INTO blackjack_stats (user_id) VALUES (?)", (user_id,))
    
    # 勝敗を引き分け・勝ち・負けの対応するカラムに+1し、利益を更新
    query = f"UPDATE blackjack_stats SET {result_type} = {result_type} + 1, total_profit = total_profit + ? WHERE user_id = ?"
    await database.execute_query(query, (amount_change, user_id))

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
