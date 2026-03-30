import discord
import datetime
import requests
import os
import jst
import re
import logging
import database
import httpx
from _notification_types_ import NOTIFICATION_TYPES

JST = jst.get_jst()
logger = logging.getLogger(__name__)

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
    now = jst.now()

    user = None
    if message.interaction_metadata:
        user = message.interaction_metadata.user
    elif message.mentions:
        user = message.mentions[0]

    if not user:
        return

    logger.debug(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name} のworkを検知")

    # クールタイム取得ロジック
    cd_min = 60
    job_info = {"name": "不明", "time": 60, "base": 0, "bonus": 0}

    try:
        r = await fetch_user_profile(user.id)
        if r.status_code == 200:
            job_key = r.json().get("jobType", "unknown").lower()
            if job_key in JOB_MAP:
                job_info = JOB_MAP[job_key]
                cd_min = job_info["time"]
            logger.debug(f"【{jst.now().strftime('%Y/%m/%d %H:%M:%S')}】{user.name} の職業: {job_info['name']}")
    except Exception as e:
        logger.warning(f"【{jst.now().strftime('%Y/%m/%d %H:%M:%S')}】APIエラー: {e}")

    # 通知予約データの作成とDBへの保存
    target_time = now + datetime.timedelta(minutes=cd_min)
    
    await database.execute_query(
        "INSERT INTO reminders (user_id, channel_id, target_time, cooldown_min, notification_type) VALUES (?, ?, ?, ?, ?)",
        (user.id, message.channel.id, target_time.isoformat(), cd_min, NOTIFICATION_TYPES.EXTERNAL_WORK)
    )

    # 応答
    res_embed = discord.Embed(description=f"`/work` を検知しました。\n{cd_min}分後にこのチャンネルで通知します", color=0x00ff00)
    await message.channel.send(embed=res_embed)

async def fetch_user_profile(user_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.takasumibot.com/v3/profile/{user_id}", timeout=10)
        return response

async def handle_unemployment_detection(bot, message, user, description):
    """失業保険のメッセージから日時を抽出して予約する"""
    match = re.search(r'有効期限は(\d{4}/\d{1,2}/\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})', description)

    if match:
        logger.debug(f"【{datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')}】{user.name} の失業保険の購入を検知")

        expiry_str = match.group(1)
        target_time = datetime.datetime.strptime(expiry_str, '%Y/%m/%d %H:%M:%S')
        target_time = JST.localize(target_time)

        notification_tyme = target_time - datetime.timedelta(minutes=1)

        target_channel = message.channel.id
        if message.guild.id == 1455450215313309763:
            target_channel = 1473864813506465903

        # DBへの保存
        await database.execute_query(
            "INSERT INTO reminders (user_id, channel_id, target_time, cooldown_min, notification_type) VALUES (?, ?, ?, ?, ?)",
            (user.id, target_channel, notification_tyme.isoformat(), 0, NOTIFICATION_TYPES.UNEMPLOYMENT_INSURANCE)
        )

        embed = discord.Embed(description=f"失業保険の購入を検知しました\n失効前に通知します\n-# 失効： {expiry_str}", color=0x00ff00)
        await message.channel.send(embed=embed)

async def handle_steal_detection(bot, message):
    now = jst.now()

    user = None
    if message.interaction_metadata:
        user = message.interaction_metadata.user
    elif message.mentions:
        user = message.mentions[0]
    if not user:
        return

    logger.info(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name} のstealを検知")

    target_time = now + datetime.timedelta(hours=2)
    
    # DBへの保存
    await database.execute_query(
        "INSERT INTO reminders (user_id, channel_id, target_time, cooldown_min, notification_type) VALUES (?, ?, ?, ?, ?)",
        (user.id, message.channel.id, target_time.isoformat(), 120, NOTIFICATION_TYPES.STEAL)
    )

    res_embed = discord.Embed(description=f"`/steal` を検知しました。\n2時間後にこのチャンネルで通知します", color=0x00ff00)
    await message.channel.send(embed=res_embed)
