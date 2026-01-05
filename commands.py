import discord
from discord import app_commands
import json
import os
import importlib
import work
import jikoku

# 管理者IDの取得
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

@app_commands.command(name="admin_reload", description="最新のファイルを読み込みます(Git更新後)")
async def admin_reload(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    
    # ここで各モジュールを手動リロード
    try:
        importlib.reload(work)
        importlib.reload(jikoku)
        # core_systemは自分自身(commands)を呼び出しているため、慎重にリロードが必要
        await interaction.response.send_message("すべてのモジュールを最新の状態に更新しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"リロードエラー: {e}", ephemeral=True)

@app_commands.command(name="admin_jikoku", description="時報を送るチャンネルをここに設定します")
async def admin_jikoku(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return

    config = {}
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            try: config = json.load(f)
            except: config = {}

    config["announcement_channel"] = interaction.channel_id

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

    await interaction.response.send_message(f"時報チャンネルを {interaction.channel.name} に設定しました。", ephemeral=True)

def setup_admin_commands(bot):
    """単体コマンドとして登録"""
    # 既存の同名コマンドがなければ追加
    if not any(cmd.name == "admin_reload" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(admin_reload)
    if not any(cmd.name == "admin_jikoku" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(admin_jikoku)
