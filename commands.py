import discord
from discord import app_commands
import json
import os
import importlib
import work
import jikoku
import time
import economy
import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')
admin_ids_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [ int(admin_id.strip().replace('"','')) for admin_id in admin_ids_env.split(',') ] if admin_ids_env else []

@app_commands.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    raw_ping = interaction.client.latency * 1000
    embed = discord.Embed(title="Pong!", color=0x00ff00)
    embed.add_field(name="Latency", value=f"{raw_ping:.2f}ms")
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="admin_reload", description="最新ファイルを反映します")
async def admin_reload(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("このコマンドを実行するための権限がありません", ephemeral=True)
        return
    try:
        import core_system
        importlib.reload(core_system)
        importlib.reload(work)
        importlib.reload(jikoku)
        importlib.reload(economy)
        
        # core_system 側の register_to_tree を通じて全体を再登録
        core_system.register_to_tree(interaction.client)
        
        now = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
        await interaction.response.send_message(f"✅ リロード完了 ({now})", ephemeral=True)
        print(f"【{now}】[Admin] System reloaded by {interaction.user}")
    except Exception as e:
        print(f"Reload Error: {e}")
        # すでに一度応答している可能性を考慮して try-except
        try:
            await interaction.response.send_message(f"❌ エラーが発生しました: {e}", ephemeral=True)
        except:
            pass

@app_commands.command(name="admin_jikoku", description="時報チャンネルを設定します")
async def admin_jikoku(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    config = economy.load_json("config.json", {})
    config["announcement_channel"] = interaction.channel_id
    economy.save_json("config.json", config)
    await interaction.response.send_message(f"時報チャンネルを設定しました", ephemeral=True)

@app_commands.command(name="admin_log", description="【管理者用】申請ログチャンネルを設定します")
async def admin_log(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    config = economy.load_json("config.json", {})
    config["log_channel"] = interaction.channel_id
    economy.save_json("config.json", config)
    await interaction.response.send_message(f"✅ 申請ログチャンネルを設定しました", ephemeral=True)

@app_commands.command(name="admin_issue", description="【管理者用】指定したユーザーにECを発行します")
async def admin_issue(interaction: discord.Interaction, user: discord.Member, amount: float):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません", ephemeral=True)
        return
    # 発行処理
    new_rate = await economy.confirm_buy_issue(user.id, amount)
    await interaction.response.send_message(f"✅ {user.mention} に {amount} EC を発行しました。新レート: {new_rate:.4f}")

def setup_admin_commands(bot):
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [ping, admin_reload, admin_jikoku, admin_log, admin_issue]
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)
