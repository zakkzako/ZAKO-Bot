import discord
import datetime
import pytz
import importlib
import os
import json
import work
import updater
import commands
import jikoku # 新規追加

JST = pytz.timezone('Asia/Tokyo')
last_announcement_hour = -1

async def init_system(bot):
    commands.setup_commands(bot)
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Sync Error: {e}")

async def check_reminders(bot):
    global last_announcement_hour
    # システム全体を自動更新対象に
    await updater.perform_full_update(["updater", "work", "core_system", "commands", "jikoku"])
    
    now = datetime.datetime.now(JST)
    
    # 時報チェック（ロジックを jikoku.py に委譲）
    if now.minute == 0 and last_announcement_hour != now.hour:
        importlib.reload(jikoku) # 常に最新のメッセージ設定を反映
        jikoku.send_hourly_announcement(bot, now)
        last_announcement_hour = now.hour

    # work通知チェック (reminders.json)
    if not os.path.exists("reminders.json"): return
    with open("reminders.json", "r") as f:
        try: queue = json.load(f)
        except: queue = []

    updated_queue = []
    for r in queue:
        target_time = datetime.datetime.fromisoformat(r['target_time'])
        if now >= target_time:
            channel = bot.get_channel(r.get('channel_id'))
            user = bot.get_user(r['user_id'])
            if channel and user:
                try:
                    await channel.send(f"{user.mention} workから{r['cooldown_min']}分が経過しました。再度実行可能です。")
                except: pass
            continue
        updated_queue.append(r)

    with open("reminders.json", "w") as f:
        json.dump(updated_queue, f, indent=4)

async def process_message_event(bot, message):
    if message.author.bot and message.embeds:
        for embed in message.embeds:
            desc = embed.description or ""
            fields_text = "".join([f.value for f in embed.fields])
            if "給料:" in desc or "給料:" in fields_text:
                importlib.reload(work)
                await work.handle_work_detection(bot, message, embed)
