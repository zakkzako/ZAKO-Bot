import discord
import datetime
import pytz
import requests
import json
import os

JST = pytz.timezone('Asia/Tokyo')
JOB_MAP = {
    "none": {"name": "無職", "time": 10}, "gambler": {"name": "ギャンブラー", "time": 10},
    "engineer": {"name": "エンジニア", "time": 60} # 以前の表に基づいて適宜追加してください
}

async def handle_work_detection(bot, message, embed):
    now = datetime.datetime.now(JST)
    user = message.interaction.user if message.interaction else (message.mentions[0] if message.mentions else None)
    if not user: return

    # ログ形式: 【日本時刻】〇〇のworkを検知
    print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name}のworkを検知")

    cd_min = 60
    job_name = "不明"
    try:
        r = requests.get(f"https://api.takasumibot.com/v3/profile/{user.id}", timeout=10)
        if r.status_code == 200:
            job_key = r.json().get("jobType", "unknown").lower()
            if job_key in JOB_MAP:
                cd_min = JOB_MAP[job_key]["time"]
                job_name = JOB_MAP[job_key]["name"]
            # ログ形式: 【日本時刻】〇〇の職業:〇〇
            print(f"【{datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')}】{user.name}の職業:{job_name}")
    except:
        print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】APIエラー: 60分通知を予約")

    # JSON保存処理
    target_time = now + datetime.timedelta(minutes=cd_min)
    new_data = {'user_id': user.id, 'target_time': target_time.isoformat(), 'cooldown_min': cd_min}
    
    queue = []
    if os.path.exists("reminders.json"):
        with open("reminders.json", "r") as f:
            try: queue = json.load(f)
            except: queue = []
    queue.append(new_data)
    with open("reminders.json", "w") as f:
        json.dump(queue, f, indent=4)

    res_embed = discord.Embed(description=f"workを検知しました。{cd_min}分後にDMで通知します", color=0x00ff00)
    await message.channel.send(embed=res_embed)
