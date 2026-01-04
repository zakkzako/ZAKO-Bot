import discord
import datetime
import pytz
import requests
import json
import os

JST = pytz.timezone('Asia/Tokyo')

# 職業データはそのまま維持
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
    
    # interaction_metadata を使用してユーザーを特定 (警告回避)
    user = None
    if message.interaction_metadata:
        user = message.interaction_metadata.user
    elif message.mentions:
        user = message.mentions[0]

    if not user:
        return

    print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name}のworkを検知")

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
            print(f"【{datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')}】{user.name}の職業:{job_info['name']}")
    except:
        print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】APIエラー: 60分後に設定")

    # 通知予約データの作成
    target_time = now + datetime.timedelta(minutes=cd_min)
    new_data = {
        'user_id': user.id,
        'channel_id': message.channel.id,
        'target_time': target_time.isoformat(),
        'cooldown_min': cd_min
    }
    
    queue = []
    if os.path.exists("reminders.json"):
        with open("reminders.json", "r") as f:
            try: queue = json.load(f)
            except: queue = []
    
    queue.append(new_data)
    with open("reminders.json", "w") as f:
        json.dump(queue, f, indent=4)

    # 応答
    res_embed = discord.Embed(description=f"workを検知しました。{cd_min}分後にこのチャンネルで通知します", color=0x00ff00)
    await message.channel.send(embed=res_embed)
