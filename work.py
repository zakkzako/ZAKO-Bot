import discord
import datetime
import pytz
import requests

JST = pytz.timezone('Asia/Tokyo')

# 画像に基づいた職業・クールタイムマッピング (APIの英語名に対応)
JOB_MAP = {
    "none": {"name": "無職", "time": 10},
    "gambler": {"name": "ギャンブラー", "time": 10},
    "chick_taxonomist": {"name": "ひよこ鑑定士", "time": 10},
    "freeter": {"name": "フリーター", "time": 15},
    "farmer": {"name": "農家", "time": 20},
    "influencer": {"name": "インフルエンサー", "time": 5},
    "architect": {"name": "建築家", "time": 45},
    "investor": {"name": "投資家", "time": 30},
    "engineer": {"name": "エンジニア", "time": 60},
    "doctor": {"name": "医師", "time": 60}
}

async def handle_work_detection(bot, message, embed, queue):
    """work検知時のメイン処理"""
    now = datetime.datetime.now(JST)
    
    # ユーザー特定
    user_id = None
    if message.interaction:
        user_id = message.interaction.user.id
    elif message.mentions:
        user_id = message.mentions[0].id
    
    if not user_id:
        return

    # ログ出力: work検知
    print(f"[{now.strftime('%Y/%m/%d %H:%M:%S')}] Work Detected: {user_id}")

    # APIから職業取得
    cd_min = 60 # デフォルト
    try:
        r = requests.get(f"https://api.takasumibot.com/v3/profile/{user_id}", timeout=10)
        if r.status_code == 200:
            job_key = r.json().get("jobType", "unknown").lower()
            if job_key in JOB_MAP:
                cd_min = JOB_MAP[job_key]["time"]
                job_name = JOB_MAP[job_key]["name"]
            else:
                cd_min = 60
                job_name = f"不明({job_key})"
            
            # ログ出力: 職業特定
            print(f"[{datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')}] Job Identified: {job_name}")
        else:
            print(f"[{now.strftime('%Y/%m/%d %H:%M:%S')}] API Error: Default to 60m")
    except Exception as e:
        print(f"[{now.strftime('%Y/%m/%d %H:%M:%S')}] API Request Failed: {e}")

    # 通知キューに追加
    target_time = now + datetime.timedelta(minutes=cd_min)
    queue.append({
        'user_id': user_id,
        'target_time': target_time,
        'cooldown_min': cd_min
    })

    # チャンネルへ埋め込み応答
    res_embed = discord.Embed(
        description=f"workを検知しました。{cd_min}分後にDMで通知します",
        color=0x00ff00
    )
    await message.channel.send(embed=res_embed)
