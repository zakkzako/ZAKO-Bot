import discord
import datetime
import requests
import json
import os
import jst
import re
import logging

JST = jst.get_jst()
logger = logging.getLogger(__name__)

# Notification type constants
NOTIFICATION_TYPE_EXTERNAL_WORK = 'external_work'

# 職業データ
JOB_MAP = {
    "none": {"name": "無職", "time": 10, "base": 100, "bonus": 0},
    "gambler": {"name": "ギャンブラー", "time": 10, "base": 80, "bonus": 0.8},
    "chick_taxonomist": {"name": "ひよこ鑑定士", "time": 10, "base": 300, "bonus": 0},
    "freeter": {"name": "フリーター", "time": 15, "base": 500, "bonus": 0.1},
    "farmer": {"name": "農家", "time": 20, "base": 1000, "bonus": 0.1},
    "influencer": {"name": "インフルエンサー", "time": 5, "base": 300, "bonus": 0.3},
    "architect": {"name": "建築家", "time": 45, "base": 3000, "bonus": 0.1},
    "investor": {"name": "投資家", "time": 30, "base": 3000, "bonus": 0.5},
    "engineer": {"name": "エンジニア", "time": 60, "base": 10000, "bonus": 0.3},
    "doctor": {"name": "医師", "time": 60, "base": 12000, "bonus": 0.1}
}

async def handle_work_detection(bot, message, embed):
    now = datetime.datetime.now(JST)

    # interaction_metadata を使用してユーザーを特定 （警告回避）
    user = None
    if message.interaction_metadata:
        user = message.interaction_metadata.user
    elif message.mentions:
        user = message.mentions[0]

    if not user:
        return

    logger.info(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name}のworkを検知")

    # クールタイム取得ロジック
    cd_min = 60
    job_info = {"name": "不明", "time": 60, "base": 0, "bonus": 0}

    try:
        r = requests.get(f"https://api.takasumibot.com/v3/profile/{user.id}", timeout=10)
        if r.status_code == 200:
            job_key = r.json().get("jobType", "unknown").lower()
            if job_key in JOB_MAP:
                job_info = JOB_MAP[job_key]
                cd_min = job_info["time"]
            logger.info(f"【{datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')}】{user.name}の職業:{job_info['name']}")
    except:
        logger.warning(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】APIエラー: 60分後に設定")

    # 通知予約データの作成
    target_time = now + datetime.timedelta(minutes=cd_min)
    new_data = {
        'user_id': user.id,
        'channel_id': message.channel.id,
        'target_time': target_time.isoformat(),
        'cooldown_min': cd_min,
        'notification_type': NOTIFICATION_TYPE_EXTERNAL_WORK
    }
    
    queue = []
    if os.path.exists("reminders.json"):
        with open("reminders.json", "r") as f:
            try: queue = json.load(f)
            except json.JSONDecodeError: queue = []
    
    queue.append(new_data)
    with open("reminders.json", "w") as f:
        json.dump(queue, f, indent=4)

    # 応答
    res_embed = discord.Embed(description=f"`/work` を検知しました。\n{cd_min}分後にこのチャンネルで通知します", color=0x00ff00)
    await message.channel.send(embed=res_embed)

    if "失業保険" in description and "購入しました" in description:
        # ユーザー特定ロジックは既存のものを流用（適宜変数名を合わせてください）
        user = None
        if message.interaction_metadata: user = message.interaction_metadata.user
        elif message.mentions: user = message.mentions[0]
        
        if user:
            await handle_unemployment_detection(bot, message, user, description)
            return

async def handle_unemployment_detection(bot, message, user, description):
    """失業保険のメッセージから日時を抽出して予約する"""
    # 正規表現で「有効期限はYYYY/M/D H:M:S」を抽出
    match = re.search(r'有効期限は(\d{4}/\d{1,2}/\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})', description)
    
    if match:
        expiry_str = match.group(1)
        # 文字列を日時に変換してタイムゾーン(JST)を設定
        target_time = datetime.datetime.strptime(expiry_str, '%Y/%m/%d %H:%M:%S')
        target_time = JST.localize(target_time)

        new_data = {
            'user_id': user.id,
            'channel_id': message.channel.id,
            'target_time': target_time.isoformat(),
            'notification_type': 'unemployment_insurance' # 新しいタイプ
        }
        
        # 既存の保存ロジック（work.py内にあるはずの処理）を流用
        queue = []
        if os.path.exists("reminders.json"):
            with open("reminders.json", "r") as f:
                try: queue = json.load(f)
                except: queue = []
        
        queue.append(new_data)
        with open("reminders.json", "w") as f:
            json.dump(queue, f, indent=4)

        await message.channel.send(f"失業保険を検知。{expiry_str} に通知します。")
