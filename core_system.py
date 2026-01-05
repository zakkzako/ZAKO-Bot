import discord
from discord import app_commands
import datetime
import pytz
import importlib
import os
import json
import work
import updater
import jikoku
import commands

JST = pytz.timezone('Asia/Tokyo')

async def init_system(bot):
    try: 
        await bot.tree.sync()
        print("【System】コマンド同期完了")
    except Exception as e: 
        print(f"Sync Error: {e}")

async def check_reminders(bot):
    # 引数は「なし」で呼び出す
    await updater.perform_full_update()

    try:
        await jikoku.announce_time(bot)
    except Exception as e:
        print(f"Jikoku Error: {e}")

    now = datetime.datetime.now(JST)
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
                    await channel.send(f"{user.mention} workから{r['cooldown_min']}分が経過しました。workが再度実行できます")
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
                await work.handle_work_detection(bot, message, embed)

def register_to_tree(bot):
    commands.setup_admin_commands(bot)
 Registration Error: {e}")

