import discord
from discord import app_commands
import importlib
import economy
import datetime
import pytz
import os
import jst
import core_system
import updater
import logging
import database # これを追加

logger = logging.getLogger(__name__)

JST = jst.get_jst()

admin_ids_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [ 1158268839721717781, 1160453651660288041 ]  # 管理者チェックの一時的ハードコーディング

admin_group = app_commands.Group(name="admin", description="［ Bot 管理者専用 ］ 管理者用コマンド")

def is_admin(user_id):
    return user_id in ADMIN_IDS if ADMIN_IDS else False

@admin_group.command(name="reload", description="［ Bot 管理者専用 ］ 最新ファイルを反映します")
async def admin_reload(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("このコマンドを実行するための権限がありません", ephemeral=True)
        return
    try:
        commit_hash = await updater.get_current_version()
        importlib.reload(core_system)
        importlib.reload(economy)
        core_system.register_to_tree(interaction.client)
        if commit_hash['local'] == commit_hash['remote']:
            await interaction.response.send_message(f"すでに最新の状態です\nコミット：`{commit_hash['remote']}`", ephemeral=True)
            return
        await updater.perform_full_update()
        importlib.reload(core_system)
        importlib.reload(economy)
        core_system.register_to_tree(interaction.client)
        now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
        await interaction.response.send_message(f"リロード完了 ({now})\nコミット：`{commit_hash['remote']}`", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
        logger.error(f"Error during admin reload: {e}")

@admin_group.command(name="time-signal", description="［ Bot 管理者専用 ］ 時報チャンネルを設定します")
async def admin_jikoku(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    # JSONの代わりにデータベースへ保存
    await database.execute_query("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", ('announcement_channel', str(interaction.channel_id)))
    await interaction.response.send_message(f"時報チャンネルを設定しました", ephemeral=True)

@admin_group.command(name="ec-admin", description="［ Bot 管理者専用 ］ 申請ログチャンネルを設定します")
async def admin_log(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    # JSONの代わりにデータベースへ保存
    await database.execute_query("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", ('log_channel', str(interaction.channel_id)))
    await interaction.response.send_message(f"申請ログチャンネルを設定しました", ephemeral=True)

admin_money_group = app_commands.Group(name="money", description="［ Bot 管理者専用 ］ 金銭操作コマンド")
admin_group.add_command(admin_money_group)

@admin_money_group.command(name="add", description="［ Bot 管理者専用 ］ ユーザーの所持金を追加します")
@app_commands.describe(user="対象のユーザー", amount="追加する金額")
async def money_add(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    # await を追加
    exists = await economy.user_exists(user.id)
    if not exists:
        await interaction.response.send_message("ユーザーが見つかりません", ephemeral=True)
        return
    # await を追加し、user.id を渡す
    await economy.add_money(user.id, amount)
    await interaction.response.send_message(f"{user.mention} に {amount} を追加しました。", ephemeral=True)

@admin_money_group.command(name="remove", description="［ Bot 管理者専用 ］ ユーザーの所持金を剥奪します")
@app_commands.describe(user="対象のユーザー", amount="剥奪する金額")
async def money_remove(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    # await を追加
    exists = await economy.user_exists(user.id)
    if not exists:
        await interaction.response.send_message("ユーザーが見つかりません", ephemeral=True)
        return
    # await を追加
    success = await economy.remove_money(user.id, amount)
    if success:
        await interaction.response.send_message(f"{user.mention} から {amount} を剥奪しました。", ephemeral=True)
    else:
        await interaction.response.send_message(f"残高が不足しているため、剥奪できませんでした。", ephemeral=True)

@admin_money_group.command(name="set", description="［ Bot 管理者専用 ］ ユーザーの所持金を設定します")
@app_commands.describe(user="対象のユーザー", amount="設定する金額")
async def money_set(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    # await を追加
    exists = await economy.user_exists(user.id)
    if not exists:
        await interaction.response.send_message("ユーザーが見つかりません", ephemeral=True)
        return
    # await を追加
    await economy.set_money(user.id, amount)
    await interaction.response.send_message(f"{user.mention} の金額を {amount} に設定しました。", ephemeral=True)

def setup_admin_commands(bot):
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [admin_group]
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)
