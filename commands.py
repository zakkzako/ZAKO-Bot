import discord
from discord import app_commands
import json
import os
import importlib
import work
import jikoku
import time
import economy # 追加：config.jsonの操作用

admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

@app_commands.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
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
        import core_system
        importlib.reload(core_system)
        importlib.reload(work)
        importlib.reload(jikoku)
        importlib.reload(economy) # 追加：経済ロジックのリロード
        
        # 自身を含むスラッシュコマンドの再登録
        core_system.register_to_tree(interaction.client)
        
        await interaction.response.send_message("リロードが完了しました。システムファイルは再起動なしで更新されました。", ephemeral=True)
        print(f"[{jikoku.get_jst_now()}] [Admin] System reloaded by {interaction.user}") # 日本時刻でログ [cite: 2026-01-03]
    except Exception as e:
        await interaction.response.send_message(f"エラー: {e}", ephemeral=True)

@app_commands.command(name="admin_jikoku", description="時報チャンネルを設定します")
async def admin_jikoku(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    
    config = economy.load_json("config.json", {}) # economyモジュールの関数で統一
    config["announcement_channel"] = interaction.channel_id
    economy.save_json("config.json", config)
    
    await interaction.response.send_message(f"時報チャンネルを設定しました", ephemeral=True)

@app_commands.command(name="admin_log", description="【管理者用】申請ログチャンネルを設定します")
async def admin_log(interaction: discord.Interaction):
    """経済システムのログチャンネル設定を追加"""
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    
    config = economy.load_json("config.json", {})
    config["log_channel"] = interaction.channel_id
    economy.save_json("config.json", config)
    
    await interaction.response.send_message(f"✅ 申請ログチャンネルを設定しました", ephemeral=True)

def setup_admin_commands(bot):
    # 重複登録を避けて単体コマンドを追加
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [ping, admin_reload, admin_jikoku, admin_log] # admin_logを追加
    
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)


