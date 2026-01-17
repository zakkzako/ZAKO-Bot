import general_commands, admin_commands, economy_commands, gambling_commands
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
import economy
import jst
import logging

JST = jst.get_jst()
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []
logger = logging.getLogger(__name__)

NOTIFICATION_TYPE_WORK = 'work'
NOTIFICATION_TYPE_EXTERNAL_WORK = 'external_work'
WORK_COOLDOWN_MINUTES = 20

async def init_system(bot):
    try: await bot.tree.sync()
    except Exception as e: logger.error(f"Sync Error: {e}")

async def check_reminders(bot):
    updater.perform_full_update()
    try: await jikoku.announce_time(bot)
    except Exception as e: logger.error(f"Jihou Error: {e}")

    now = datetime.datetime.now(JST)
    if not os.path.exists("reminders.json"): return
    with open("reminders.json", "r") as f:
        try: queue = json.load(f)
        except: queue = []

    updated_queue = []
    for r in queue:
        target_time = datetime.datetime.fromisoformat(r['target_time'])
        if now >= target_time:
            channel_id = int(r.get('channel_id'))
            user_id = int(r['user_id'])
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
            try: user = await bot.fetch_user(user_id)
            except: user = None

            if channel and user:
                try: 
                    notification_type = r.get('notification_type', NOTIFICATION_TYPE_EXTERNAL_WORK)
                    if notification_type == NOTIFICATION_TYPE_WORK:
                        await channel.send(f"{user.mention} `/work` から20分が経過しました。")
                    else:
                        await channel.send(f"{user.mention} workから20分が経過しました。\n</work:1132868147519692871> が再度実行できます")
                except Exception as e: logger.error(f"Notify error: {e}")
            continue
        updated_queue.append(r)
    with open("reminders.json", "w") as f: json.dump(updated_queue, f, indent=4)

async def process_message_event(bot, message):
    if not message.author.bot or message.author.id == bot.user.id:
        return
    
    for embed in message.embeds:
        author_name = embed.author.name if embed.author else ""
        desc = embed.description or ""

        # あなたがコピペしてくれた「給料:」の形式に完全対応
        if "コインを手に入れました" in author_name and "給料" in desc:
            logger.debug(f"Work detected in message ID {message.id} by {message.author.id}")
            importlib.reload(work)
            await work.handle_work_detection(bot, message, embed)
            break

async def handle_reaction_event(bot, payload):
    if payload.user_id not in ADMIN_IDS or str(payload.emoji) != "✅": return
    channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
    try:
        message = await channel.fetch_message(payload.message_id)
        if not (message.author.id == bot.user.id and message.embeds): return
        embed = message.embeds[0]
        importlib.reload(economy)
        user_id = int(embed.fields[0].value.replace("<@", "").replace(">", "").replace("!", ""))
        amount = float(embed.fields[1].value.split(" ")[0])
        if embed.title == "💰 換金申請":
            new_rate = await economy.confirm_exchange_burn(amount)
            await message.edit(content=f"✅ **換金完了** (レート: {new_rate:.4f})", embed=None)
        elif embed.title == "💎 EC購入申請":
            new_rate = await economy.confirm_buy_issue(user_id, amount)
            await message.edit(content=f"✅ **購入完了** (レート: {new_rate:.4f})", embed=None)
    except Exception as e: logger.error(f"Reaction Error: {e}")

def register_to_tree(bot):
    try:
        importlib.reload(general_commands)
        importlib.reload(admin_commands)
        importlib.reload(economy_commands)
        importlib.reload(gambling_commands)
        general_commands.setup_general_commands(bot)
        admin_commands.setup_admin_commands(bot)
        economy_commands.setup_economy_commands(bot)
        gambling_commands.setup_gambling_commands(bot)
        bot.loop.create_task(bot.tree.sync())
    except Exception as e: logger.error(f"Reg Error: {e}")
