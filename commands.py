import discord
from discord import app_commands
import json
import os
import importlib
import work
import jikoku
import time # 追加

admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

@app_commands.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    # レイテンシ（ms）を計算
    raw_ping = interaction.client.latency * 1000
    
    embed = discord.Embed(title="Pong!", color=0x00ff00)
    embed.add_field(name="Latency", value=f"{raw_ping:.2f}ms")
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="admin_reload", description="最新ファイルを反映します")
async def admin_reload(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    try:
        importlib.reload(work)
        importlib.reload(jikoku)
        # 自身(commands)のリロードはcore_system側で行われるため、ここではロジック反映を通知
        await interaction.response.send_message("リロードが完了しました。新しいコマンドを追加した場合はBotを再起動してください。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラー: {e}", ephemeral=True)

@app_commands.command(name="admin_jikoku", description="時報チャンネルを設定します")
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
    await interaction.response.send_message(f"時報チャンネルを設定しました", ephemeral=True)

def setup_admin_commands(bot):
    # 重複登録を避けて単体コマンドを追加
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    if "ping" not in existing:
        bot.tree.add_command(ping)
    if "admin_reload" not in existing:
        bot.tree.add_command(admin_reload)
    if "admin_jikoku" not in existing:
        bot.tree.add_command(admin_jikoku)
