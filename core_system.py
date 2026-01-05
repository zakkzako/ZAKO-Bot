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

async def check_reminders(bot):
    # 1. 自動ダウンロードのみ実行（リロードはしない）
    await updater.perform_full_update()

    # 2. 時報機能の実行（ここは稼働させる必要があります）
    # ※jikoku.py自体を編集した場合は /admin_reload するまで旧ロジックで動きます
    try:
        await jikoku.announce_time(bot)
    except Exception as e:
        print(f"Jikoku Error: {e}")

    # 3. work通知チェック (以下、変更なし)
    now = datetime.datetime.now(JST)
    if not os.path.exists("reminders.json"): return
    # ... (中略：既存のreminders.jsonチェック処理) ...

def register_to_tree(bot):
    try:
        # 単体コマンドを登録
        commands.setup_admin_commands(bot)
    except Exception as e:
        print(f"Command Registration Error: {e}")

