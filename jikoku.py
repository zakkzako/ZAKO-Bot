import discord
import datetime
import json
import os
import jst
import logging

JST = jst.get_jst()

# 直近の送信時刻を記録する変数（時刻の重複送信を防ぐ）
last_sent_hour = None

logger = logging.getLogger(__name__)

async def announce_time(bot):
    """毎正時に実行される時報処理"""
    if not os.path.exists("config.json"):
        return

    with open("config.json", "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON Decode Error: {e}")
            return

    channel_id = config.get("announcement_channel")
    if not channel_id:
        return

    now = datetime.datetime.now(JST)
    # 00分であることを確認（30秒間隔のループで呼ばれる想定）
    if now.minute == 0:
        # 通知済みチェック: 既にこの時刻に送信済みであれば送信しない
        global last_sent_hour
        current_hour_key = (now.year, now.month, now.day, now.hour)
        if last_sent_hour == current_hour_key:
            return
        
        channel = bot.get_channel(channel_id)
        if channel:
            # 24時間制で表示
            msg = f"{now.hour}時をお知らせします"
            try:
                await channel.send(msg)
                # 送信成功後、この時刻を記録
                last_sent_hour = current_hour_key
                logger.info(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】時報を送信しました: {msg}")
            except discord.errors.DiscordException as e:
                logger.error(f"Discord API Error: {e}")
