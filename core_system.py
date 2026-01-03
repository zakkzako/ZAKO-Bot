import discord
from discord import app_commands
import datetime
import pytz
import importlib
import work
import os
from dotenv import load_dotenv
load_dotenv()

ADMIN_IDS = [int(os.getenv('ADMIN_ID', 0))] 


# --- 設定エリア ---
JST = pytz.timezone('Asia/Tokyo')
ADMIN_IDS = [123456789012345678] # あなたのDiscordユーザーIDに書き換えてください
reminder_queue = [] # 通知待ちリスト（メモリ管理）

async def init_system(bot):
    """起動時のスラッシュコマンド同期"""
    try:
        await bot.tree.sync()
        now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
        print(f'[{now}] Logged in as {bot.user.name} & Synced Commands')
    except Exception as e:
        print(f"Sync Error: {e}")

async def check_reminders(bot):
    """30秒ごとに実行される時刻監視ロジック"""
    now = datetime.datetime.now(JST)
    for reminder in reminder_queue[:]:
        # 現在時刻が通知予定時刻を過ぎているか確認
        if now >= reminder['target_time']:
            user = bot.get_user(reminder['user_id']) or await bot.fetch_user(reminder['user_id'])
            if user:
                try:
                    await user.send(f"workから{reminder['cooldown_min']}分が経過しました。workが再度実行できます")
                    # 送信完了ログ
                    log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
                    print(f"[{log_time}] DM Sent to: {user.id}")
                except Exception as e:
                    print(f"DM Send Error: {e}")
            # 送信後、または失敗後にリストから削除
            reminder_queue.remove(reminder)

async def process_message_event(bot, message):
    """TakasumiBotのwork検知仲介"""
    if message.author.bot and message.embeds:
        for embed in message.embeds:
            if embed.description and "給料:" in embed.description:
                importlib.reload(work)
                await work.handle_work_detection(bot, message, embed, reminder_queue)

@app_commands.command(name="admin", description="管理者用コマンド")
@app_commands.describe(action="操作内容 (reload)")
async def admin(interaction: discord.Interaction, action: str):
    """/admin reload でシステムファイルを即時更新"""
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
        return

    if action == "reload":
        try:
            importlib.reload(work)
            await interaction.response.send_message("システムファイル(work.py)を更新しました。")
        except Exception as e:
            await interaction.response.send_message(f"更新エラー: {e}")

def register_to_tree(bot):
    """mainから呼ばれるコマンド登録処理"""
    if not any(cmd.name == "admin" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(admin)
