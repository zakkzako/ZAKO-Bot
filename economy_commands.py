import discord
from discord import app_commands
import economy
import os

@app_commands.command(name="money", description="所持ECと本家マネー換算額を確認")
async def money(interaction: discord.Interaction):
    users = economy.load_json("users.json", {})
    balance = users.get(str(interaction.user.id), {}).get("balance", 0.0)
    rate = economy.get_current_rate()
    embed = discord.Embed(title="💰 資産状況", color=0x00ff00)
    embed.add_field(name="所持EC", value=f"{balance:.2f} EC")
    embed.add_field(name="本家換算額", value=f"約 {balance * rate:.0f} Money")
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="rate", description="現在のレートを確認")
async def rate(interaction: discord.Interaction):
    r = economy.get_current_rate()
    await interaction.response.send_message(f"📈 現在のレート: **1 EC = {r:.4f} TakasumiMoney**")

@app_commands.command(name="work", description="ECを獲得 (20分毎)")
async def ec_work(interaction: discord.Interaction):
    success, res = economy.process_work(interaction.user.id)
    if success: await interaction.response.send_message(f"⛏ **{res} EC** 獲得！")
    else: await interaction.response.send_message(f"あと{int(res.total_seconds()//60)}分お待ちください。", ephemeral=True)

@app_commands.command(name="exchange", description="EC → 本家マネーに換金申請")
async def exchange(interaction: discord.Interaction, amount: float):
    rate = economy.get_current_rate()
    has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, amount * rate)
    if not has_assets:

