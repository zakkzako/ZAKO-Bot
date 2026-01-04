import discord
from discord import app_commands
import datetime
import pytz
import importlib
import os
import json
import work
import updater

JST = pytz.timezone('Asia/Tokyo')
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

async def init_system(bot):
    try: await bot.tree.sync()
    except Exception as e: print(f"Sync Error: {e}")

async def check_reminders(bot):
    # 自動更新
    await updater.perform_full_update(["updater", "work", "core_system"])
    
    now = datetime.datetime.now(JST)
    if not os.path.exists("reminders.json"): return

    with open("reminders.json", "r") as f:
        try: queue = json.load(f)
        except: queue = []

    updated_queue = []
    for r in queue:
        target_time = datetime.datetime.fromisoformat(r['target_time'])
        if now >= target_time:
            # チャンネル宛に通知を送る
            channel = bot.get_channel(r.get('channel_id'))
            user = bot.get_user(r['user_id'])
            
            if channel and user:
                try:
                    # メンション付きでチャンネルに送信
                    await channel.send(f"{user.mention} workから{r['cooldown_min']}分が経過しました。workが再度実行できます")
                    print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name}への通知を完了")
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

@app_commands.command(name="admin", description="管理者用コマンド")
async def admin(interaction: discord.Interaction, action: str):
    if interaction.user.id not in ADMIN_IDS: return
    if action == "reload":
        importlib.reload(work)
        await interaction.response.send_message("再読み込み完了", ephemeral=True)

def register_to_tree(bot):
    if not any(cmd.name == "admin" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(admin)
