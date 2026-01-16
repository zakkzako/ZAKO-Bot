import discord
from discord import app_commands
import importlib
import economy
import datetime
import pytz
import os
import jst

JST = jst.get_jst()

admin_ids_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [ int(admin_id.strip().replace('"','')) for admin_id in admin_ids_env.split(',') ] if admin_ids_env else [ "1158268839721717781", "1160453651660288041" ]

admin_group = app_commands.Group(name="admin", description="[Bot 管理者専用] 管理者用コマンド")

def is_admin(user_id):
    return user_id in ADMIN_IDS if ADMIN_IDS else False

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

@admin_group.command(name="ec-admin", description="[Bot 管理者専用] 申請ログチャンネルを設定します")
async def admin_log(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    config = economy.load_json("config.json", {})
    config["log_channel"] = interaction.channel_id
    economy.save_json("config.json", config)
    await interaction.response.send_message(f"✅ 申請ログチャンネルを設定しました", ephemeral=True)


admin_money_group = app_commands.Group(name="money", description="[Bot 管理者専用] 金銭操作コマンド", parent=admin_group)

@admin_money_group.command(name="add", description="[Bot 管理者専用] ユーザーの金額を追加します")
async def money_add(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    if not economy.user_exists(user.id):
        await interaction.response.send_message("ユーザーが見つかりません", ephemeral=True)
        return
    economy.add_money(user.id, amount)
    await interaction.response.send_message(f"✅ {user.mention} に {amount} を追加しました。", ephemeral=True)

@admin_money_group.command(name="remove", description="[Bot 管理者専用] ユーザーの金額を剥奪します")
async def money_remove(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    if not economy.user_exists(user.id):
        await interaction.response.send_message("ユーザーが見つかりません", ephemeral=True)
        return
    economy.remove_money(user.id, amount)
    await interaction.response.send_message(f"✅ {user.mention} から {amount} を剥奪しました。", ephemeral=True)

@admin_money_group.command(name="set", description="[Bot 管理者専用] ユーザーの金額を設定します")
async def money_set(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    if not economy.user_exists(user.id):
        await interaction.response.send_message("ユーザーが見つかりません", ephemeral=True)
        return
    economy.set_money(user.id, amount)
    await interaction.response.send_message(f"✅ {user.mention} の金額を {amount} に設定しました。", ephemeral=True)

def setup_admin_commands(bot):
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [admin_group]
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)
