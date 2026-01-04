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

# 管理者設定
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

async def init_system(bot):
    """起動時の初期設定"""
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Sync Error: {e}")

async def check_reminders(bot):
    """30秒ごとの監視・更新・その他定時処理"""
    # プログラムの自動更新チェック
    await updater.perform_full_update(["updater", "work", "core_system"])
    
    now = datetime.datetime.now(JST)
    if not os.path.exists("reminders.json"):
        return

    with open("reminders.json", "r") as f:
        try:
            queue = json.load(f)
        except:
            queue = []

    updated_queue = []
    for r in queue:
        target_time = datetime.datetime.fromisoformat(r['target_time'])
        if now >= target_time:
            user = bot.get_user(r['user_id']) or await bot.fetch_user(r['user_id'])
            if user:
                try:
                    await user.send(f"workから{r['cooldown_min']}分が経過しました。workが再度実行できます")
                    # ログ形式: 【日本時刻】〇〇への通知を完了
                    print(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】{user.name}への通知を完了")
                except:
                    pass
            continue # 送信済みは除外
        updated_queue.append(r)

    with open("reminders.json", "w") as f:
        json.dump(updated_queue, f, indent=4)

async def process_message_event(bot, message):
    """メッセージイベントのハンドリング"""
    # TakasumiBotのwork検知
    if message.author.bot and message.embeds:
        for embed in message.embeds:
            desc = embed.description or ""
            fields_text = "".join([f.value for f in embed.fields])
            if "給料:" in desc or "給料:" in fields_text:
                importlib.reload(work)
                await work.handle_work_detection(bot, message, embed)
    
    # --- ここにwork以外の「便利機能(メッセージ応答等)」を追加可能 ---

# --- 管理者・一般コマンドの定義 ---

@app_commands.command(name="admin", description="管理者用コマンド")
@app_commands.describe(action="操作内容")
async def admin(interaction: discord.Interaction, action: str):
    """管理者用コマンドロジック"""
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません。", ephemeral=True)
        return

    if action == "reload":
        # 手動リロード時もログを出す
        importlib.reload(updater)
        importlib.reload(work)
        now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
        print(f"【{now}】管理コマンドによりプログラムのリロードが予約されました")
        await interaction.response.send_message("システムファイルを更新リストに追加しました。")

# --- core_system.py内に新しいコマンドを追加する例 ---
@app_commands.command(name="ping", description="疎通確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! ({round(interaction.client.latency * 1000)}ms)")

def register_to_tree(bot):
    """コマンドをBotのツリーに登録"""
    # 既存のコマンドを上書きしないように登録
    commands_to_add = [admin, ping] # 新しいコマンドを作ったらここに追加
    for cmd in commands_to_add:
        if not any(existing.name == cmd.name for existing in bot.tree.get_commands()):
            bot.tree.add_command(cmd)
