import discord
import datetime
import pytz
import json
import os

JST = pytz.timezone('Asia/Tokyo')

async def announce_time(bot):
    """毎正時に実行される時報処理"""
    if not os.path.exists("config.json"):
        return

    with open("config.json", "r") as f:
        try:
            config = json.load(f)
        except:
            return

    channel_id = config.get("announcement_channel")
    if not channel_id:
        return

    now = datetime.datetime.now(JST)
    # 00分であることを確認（30秒間隔のループで呼ばれる想定）
    if now.minute == 0:
        channel = bot.get_channel(channel_id)
        if channel:
            # 午前/午後の判定
            period = "午前" if now.hour < 12 else "午後"
            # 12時間制の時間を取得
            hour_12 = now.hour % 12
            if hour_12 == 0: hour_12 = 12
            
            msg = f"{period}{hour_12}時をお知らせします"
            try:
                await channel.send(msg)
                print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】時報を送信しました: {msg}")
            except Exception as e:
                print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】時報送信エラー: {e}")
