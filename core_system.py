import discord
from discord import app_commands
import datetime
import pytz
import importlib
import os
import json
import work
import updater
from dotenv import load_dotenv

load_dotenv()
JST = pytz.timezone('Asia/Tokyo')

# 管理者ID（環境変数から取得、なければデフォルト）
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else [123456789012345678]

async def init_system(bot):
    """起動時の同期処理"""
    try:
        await bot.tree.sync()
        now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
        print(f'[{now}] System Initialized & Commands Synced')
    except Exception as e:
        print(f"Sync Error: {e}")

async def check_reminders(bot):
    """30秒ごとの監視と全ファイル更新チェック"""
    # updater自身、work、そしてこのcore_systemをリロード対象に含める
    # (Main.py側のループでcore_systemのリロードが実行されます)
    await updater.perform_full_update(["updater", "work", "core_system"])
    
    now = datetime.datetime.now(JST)
    
    if not os.path.exists("reminders.json"):
        return

    try:
        with open("reminders.json", "r") as f:
            queue = json.load(f)
    except:
        queue = []

    updated_queue = []
    for reminder in queue:
        target_time = datetime.datetime.fromisoformat(reminder['target_time'])
        
        if now >= target_time:
            user = bot.get_user(reminder['user_id']) or await bot.fetch_user(reminder['user_id'])
            if user:
                try:
                    await user.send(f"workから{reminder['cooldown_min']}分が経過しました。workが再度実行できます")
                    log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
                    print(f"[{log_time}] [LOG] 通知送信完了: {user.id}")
                except Exception as e:
                    print(f"DM Send Error: {e}")
            continue # 送信済みはリストに戻さない
        
        updated_queue.append(reminder)

    with open("reminders.json", "w") as f:
        json.dump(updated_queue, f, indent=4)

async def process_message_event(bot, message):
    """work検知の仲介"""
    if message.author.bot and message.embeds:
        for embed in message.embeds:
            desc = embed.description or ""
            # Field内も念のためチェック
            fields_text = "".join([f.value for f in embed.fields])
            
            if "給料:" in desc or "給料:" in fields_text:
                importlib.reload(work)
                # work.py内のロジックでreminders.jsonへ保存
                await work.handle_work_detection(bot, message, embed)

@app_commands.command(name="admin", description="管理者用コマンド")
async def admin(interaction: discord.Interaction, action: str):
    """手動での強制リロード"""
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません。", ephemeral=True)
        return

    if action == "reload":
        try:
            importlib.reload(updater)
            importlib.reload(work)
            # core_system自体はMain.pyが次のループで自動リロードします
            await interaction.response.send_message("システムファイルを更新リストに追加しました。次回のループで反映されます。")
        except Exception as e:
            await interaction.response.send_message(f"更新エラー: {e}")

def register_to_tree(bot):
    """コマンド登録"""
    if not any(cmd.name == "admin" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(admin)
        
