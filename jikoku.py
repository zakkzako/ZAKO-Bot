
import discord
import datetime
import json
import os

def send_hourly_announcement(bot, now):
    """毎時0分の時報処理 (午前/午後形式)"""
    if not os.path.exists("config.json"):
        return

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            channel_id = config.get("announcement_channel")
            
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                # 午前/午後の判定と12時間制への変換
                ampm = "午前" if now.hour < 12 else "午後"
                hour_12 = now.hour % 12
                if hour_12 == 0: hour_12 = 12 # 0時は12時と表示
                
                msg = f"🕒 {ampm}{hour_12}時をお知らせします。"
                
                # 非同期で送信
                bot.loop.create_task(channel.send(msg))
                print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】時報送信完了: {ampm}{hour_12}時")
    except Exception as e:
        print(f"【時報エラー】{e}")
