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
import database
import json # db-viewのJSON整形用に追加

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
        commit_hash = updater.get_current_version()
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


# === ここから新規追加のDB管理コマンド ===

@admin_group.command(name="db-view", description="［ Bot 管理者専用 ］ ユーザーのDBデータをJSON風に確認します")
@app_commands.describe(user="確認したいユーザー")
async def db_view(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("権限がありません", ephemeral=True)

    uid = user.id
    data = {}

    u_row = await database.fetch_one("SELECT * FROM users WHERE user_id = ?", (uid,))
    if u_row: data["users"] = dict(u_row)

    b_row = await database.fetch_one("SELECT * FROM blackjack_stats WHERE user_id = ?", (uid,))
    if b_row: data["blackjack_stats"] = dict(b_row)

    n_row = await database.fetch_one("SELECT * FROM notification_settings WHERE user_id = ?", (uid,))
    if n_row: data["notification_settings"] = dict(n_row)

    r_rows = await database.fetch_all("SELECT * FROM reminders WHERE user_id = ?", (uid,))
    if r_rows: data["reminders"] = [dict(r) for r in r_rows]

    if not data:
        return await interaction.response.send_message("このユーザーのデータはデータベースに見つかりませんでした。", ephemeral=True)

    json_text = json.dumps(data, indent=2, ensure_ascii=False)
    await interaction.response.send_message(f"```json\n{json_text}\n```", ephemeral=True)


@admin_group.command(name="db-edit", description="［ Bot 管理者専用 ］ DBの特定の値を直接書き換えます")
@app_commands.describe(user="対象ユーザー", column="変更する項目", value="新しい値")
@app_commands.choices(table=[
    app_commands.Choice(name="users (所持金, 換金履歴など)", value="users"),
    app_commands.Choice(name="blackjack_stats (カジノ戦績など)", value="blackjack_stats"),
    app_commands.Choice(name="notification_settings (通知ON/OFF)", value="notification_settings")
])
async def db_edit(interaction: discord.Interaction, user: discord.Member, table: app_commands.Choice[str], column: str, value: str):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("権限がありません", ephemeral=True)

    allowed_columns = {
        "users": ["balance", "daily_exchange_total", "last_exchange_date", "last_work"],
        "blackjack_stats": ["win", "loss", "draw", "total_profit"],
        "notification_settings": ["work", "external_work", "unemployment_insurance", "steal"]
    }

    table_name = table.value
    if column not in allowed_columns.get(table_name, []):
        available = ", ".join(allowed_columns[table_name])
        return await interaction.response.send_message(f"許可されていない項目名です。利用可能な項目: {available}", ephemeral=True)

    try:
        if column in ["balance", "daily_exchange_total", "total_profit"]:
            val = float(value)
        elif column in ["win", "loss", "draw", "work", "external_work", "unemployment_insurance", "steal"]:
            val = int(value)
        else:
            val = str(value)
    except ValueError:
        return await interaction.response.send_message("値の形式（数字など）が間違っています。", ephemeral=True)

    query = f"UPDATE {table_name} SET {column} = ? WHERE user_id = ?"
    await database.execute_query(query, (val, user.id))

    await interaction.response.send_message(f"更新完了: {table_name} の {column} を {val} に変更しました。", ephemeral=True)


@admin_group.command(name="db-backup", description="［ Bot 管理者専用 ］ 現在のDBファイルをダウンロードします")
async def db_backup(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("権限がありません", ephemeral=True)

    if not os.path.exists(database.DB_FILE):
        return await interaction.response.send_message("データベースファイルが存在しません。", ephemeral=True)

    file = discord.File(database.DB_FILE, filename=f"bot_data_backup_{datetime.datetime.now(JST).strftime('%Y%m%d_%H%M')}.db")
    await interaction.response.send_message("現在のデータベースファイルのバックアップです。PC上の「DB Browser for SQLite」などのソフトで直接開いて編集・確認が可能です。", file=file, ephemeral=True)

def setup_admin_commands(bot):
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [admin_group]
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)
