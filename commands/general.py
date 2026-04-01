import discord
from discord import app_commands
import importlib
import logging
import time
import datetime
import pytz
import jst

JST = jst.get_jst()

@app_commands.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    try:
        raw_ping = interaction.client.latency * 1000
        start_time = time.perf_counter()
        await interaction.response.send_message("計測中...")
        end_time = time.perf_counter()
        message_latency = (end_time - start_time) * 1000

        embed = discord.Embed(title="Pong!", color=0x00ff00)
        embed.add_field(name="Raw Latency", value=f"{raw_ping:.2f}ms")
        embed.add_field(name="Message Latency", value=f"{message_latency:.2f}ms")
        await interaction.edit_original_response(content=None, embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}")
        logging.error(f"Error in ping command: {e}")

def setup_general_commands(bot):
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [ping]
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)
