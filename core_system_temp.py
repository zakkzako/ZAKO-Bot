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
import general_commands
import admin_commands
import economy_commands
import gambling_commands
import jst
import logging

JST = jst.get_jst()
logger = logging.getLogger(__name__)

async def process_message_event(bot, message):
    """メッセージ送信・編集の両方から呼ばれる検知ロジック"""
    target_keyword = "給料:"
    is_detected = False
    detected_embed = None

    # 1. 本文チェック
    if target_keyword in message.content:
        is_detected = True

    # 2. 埋め込みチェック (後から中身が入るBot対策)
    if not is_detected and message.embeds:
        for embed in message.embeds:
            content = ""
            if embed.title: content += embed.title
            if embed.description: content += embed.description
            if target_keyword in content:
                is_detected = True
                detected_embed = embed
                break

    if is_detected:
        # work.py の検知ロジックを呼び出し
        importlib.reload(work)
        await work.handle_work_detection(bot, message, detected_embed)

# --- 以下の既存関数(init_system, check_reminders等)は元のファイルを保持 ---
