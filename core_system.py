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
import economy
import economy_commands

JST = pytz.timezone('Asia/Tokyo')
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

# Notification type constants
NOTIFICATION_TYPE_WORK = 'work'
NOTIFICATION_TYPE_EXTERNAL_WORK = 'external_work'
WORK_COOLDOWN_MINUTES = 20

async def init_system(bot):
    try: await bot.tree.sync()
    except Exception as e: print(f"Sync Error: {e}")

async def check_reminders(bot):
    await updater.perform_full_update()
    try: await jikoku.announce_time(bot)
    except Exception as e: print(f"Jikoku Error: {e}")

    now = datetime.datetime.now(JST)
    if not os.path.exists("reminders.json"): return
    with open("reminders.json", "r") as f:
        try: queue = json.load(f)
        except json.JSONDecodeError: queue = []

    updated_queue = []
    for r in queue:
        target_time = datetime.datetime.fromisoformat(r['target_time'])
        if now >= target_time:
            channel = bot.get_channel(r.get('channel_id'))
            user = bot.get_user(r['user_id'])
            if channel and user:
                try: 
                    notification_type = r.get('notification_type', NOTIFICATION_TYPE_EXTERNAL_WORK)
                    if notification_type == NOTIFICATION_TYPE_WORK:
                        # 内部workコマンドの通知
                        await channel.send(f"{user.mention} workから{WORK_COOLDOWN_MINUTES}分が経過しました。再度 `/work` を実行できます！")
                    else:
                        # 外部bot（Takasumi）のwork検知による通知
                        await channel.send(f"{user.mention} workから{r.get('cooldown_min', WORK_COOLDOWN_MINUTES)}分が経過しました。workが再度実行できます")
                except Exception as e:
                    print(f"Notification send error: {e}")
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

async def handle_reaction_event(bot, payload):
    if payload.user_id not in ADMIN_IDS or str(payload.emoji) != "✅":
        return

    channel = bot.get_channel(payload.channel_id)
    try: message = await channel.fetch_message(payload.message_id)
    except: return

    if not (message.author.id == bot.user.id and message.embeds): return
    embed = message.embeds[0]

    try:
        # 最新の経済ロジックを読み込み
        importlib.reload(economy)
        user_mention = embed.fields[0].value
        user_id = int(user_mention.replace("<@", "").replace(">", "").replace("!", ""))
        amount = float(embed.fields[1].value.split(" ")[0])

        if embed.title == "💰 換金申請":
            new_rate = economy.confirm_exchange_burn(amount)
            await message.edit(content=f"✅ **換金完了** (レート: {new_rate:.4f})", embed=None)
        elif embed.title == "💎 EC購入申請":
            new_rate = economy.confirm_buy_issue(user_id, amount)
            await message.edit(content=f"✅ **購入完了** (レート: {new_rate:.4f})", embed=None)
            
        print(f"【{datetime.datetime.now(JST)}】[Economy] Confirmed: {embed.title} for {user_id}")
    except Exception as e:
        print(f"Reaction Process Error: {e}")

def register_to_tree(bot):
    try:
        importlib.reload(commands)
        importlib.reload(economy_commands) 
        commands.setup_admin_commands(bot)
        economy_commands.setup_economy_commands(bot)
        # 必要に応じて同期も行う
        bot.loop.create_task(bot.tree.sync())
        print("Modules reloaded and tree synced.")
    except Exception as e:
        print(f"Registration Error: {e}")
