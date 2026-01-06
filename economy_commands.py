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
        await interaction.response.send_message("本家資産が不足しています（申請額の10倍必要）", ephemeral=True)
        return
    if economy.request_exchange_lock(interaction.user.id, amount):
        config = economy.load_json("config.json", {})
        log_ch = interaction.client.get_channel(config.get("log_channel"))
        if log_ch:
            embed = discord.Embed(title="💰 換金申請", color=0xffa500)
            embed.add_field(name="ユーザー", value=interaction.user.mention)
            embed.add_field(name="枚数", value=f"{amount} EC")
            embed.add_field(name="送金額", value=f"{amount * rate:.0f} Money")
            msg = await log_ch.send(embed=embed)
            await msg.add_reaction("✅")
            await interaction.response.send_message("申請を送信しました。")
    else:
        await interaction.response.send_message("EC残高不足です。", ephemeral=True)

@app_commands.command(name="buy_ec", description="本家マネー → EC 購入申請")
async def buy_ec(interaction: discord.Interaction, amount: float):
    rate = economy.get_current_rate()
    cost = amount * rate
    has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, cost)
    if not has_assets:
        await interaction.response.send_message("本家資産が不足しています。", ephemeral=True)
        return
    config = economy.load_json("config.json", {})
    log_ch = interaction.client.get_channel(config.get("log_channel"))
    if log_ch:
        embed = discord.Embed(title="💎 EC購入申請", color=0x00ffff)
        embed.add_field(name="ユーザー", value=interaction.user.mention)
        embed.add_field(name="購入", value=f"{amount} EC")
        embed.add_field(name="支払い", value=f"{cost:.0f} Money")
        msg = await log_ch.send(embed=embed)
        await msg.add_reaction("✅")
        await interaction.response.send_message(f"申請完了。管理者に {cost:.0f} Moneyを送金してください。")

@app_commands.command(name="economy", description="現在の経済状況を確認します")
async def economy_info(interaction: discord.Interaction):
    data = economy.load_json(economy.ECONOMY_FILE, {"total_supply": economy.INITIAL_SUPPLY})
    total_supply = data["total_supply"]
    rate = economy.get_current_rate()
    embed = discord.Embed(title="📊 経済統計", color=0x3498db)
    embed.add_field(name="総発行枚数", value=f"{total_supply:,.2f} EC", inline=False)
    embed.add_field(name="現在のレート", value=f"1 EC = {rate:.4f} Money", inline=False)
    await interaction.response.send_message(embed=embed)

def setup_economy_commands(bot):
    cmds = [money, rate, ec_work, exchange, buy_ec, economy_info]
    for c in cmds:
        if c.name not in [cmd.name for cmd in bot.tree.get_commands()]:
            bot.tree.add_command(c)
