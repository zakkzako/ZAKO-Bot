import discord
from discord import app_commands
import importlib
import economy
import datetime
import pytz
import os
import jst
import logging

JST = jst.get_jst()

def _parse_admin_ids(env_val):
    """
    環境変数 ADMIN_ID をパースして int のリストを返す。
    例: "123,456" や "123" に対応。空なら空リスト。
    """
    if not env_val:
        return []
    parts = [p.strip().strip('"').strip("'") for p in env_val.split(',') if p.strip()]
    ids = []
    for p in parts:
        try:
            ids.append(int(p))
        except ValueError:
            logging.warning(f"Invalid ADMIN_ID entry ignored: {p}")
    return ids

admin_ids_env = os.getenv('ADMIN_ID')
ADMIN_IDS = _parse_admin_ids(admin_ids_env) or [1158268839721717781, 1160453651660288041]

admin_group = app_commands.Group(name="admin", description="[Bot 管理者専用] 管理者用コマンド")

def is_admin(user_id):
    return user_id in ADMIN_IDS

@admin_group.command(name="reload", description="[Bot 管理者専用] 最新ファイルを反映します")
async def admin_reload(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("このコマンドを実行するための権限がありません", ephemeral=True)
        return
    try:
        import core_system
        importlib.reload(core_system)
        importlib.reload(economy)
        core_system.register_to_tree(interaction.client)
        now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
        await interaction.response.send_message(f"✅ リロード完了 ({now})", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ エラーが発生しました: {e}", ephemeral=True)

@admin_group.command(name="time-signal", description="[Bot 管理者専用] 時報チャンネルを設定します")
async def admin_jikoku(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    config = economy.load_json("config.json", {})
    config["announcement_channel"] = interaction.channel_id
    economy.save_json("config.json", config)
    await interaction.response.send_message(f"時報チャンネルを設定しました", ephemeral=True)
