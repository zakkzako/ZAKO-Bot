import discord
from discord import app_commands
import economy
import aiohttp
import datetime
import pytz
import json
import os

JST = pytz.timezone('Asia/Tokyo')

# ユーザー向け経済コマンド
@app_commands.command(name="money", description="所持ECと本家マネー換算額を確認します")
async def money(interaction: discord.Interaction):
    users = economy.load_json("users.json", {})
    balance = users.get(str(interaction.user.id), {}).get("balance", 0.0)
    rate = economy.get_current_rate()
    embed = discord.Embed(title="💰 資産状況", color=0x00ff00)
    embed.add_field(name="所持EC", value=f"{balance:.2f} EC", inline=True)
    embed.add_field(name="本家換算額", value=f"約 {balance * rate:.0f} Money", inline=True)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="rate", description="現在の1ECあたりの価値を確認します")
async def rate(interaction: discord.Interaction):
    r = economy.get_current_rate()
    await interaction.response.send_message(f"📈 現在の換金レート: **1 EC = {r:.4f} TakasumiMoney**")

@app_commands.command(name="work", description="ECを獲得します（20分に1回）")
async def ec_work(interaction: discord.Interaction):
    success, res = economy.process_work(interaction.user.id)
    if success:
        await interaction.response.send_message(f"⛏ **{res} EC** を獲得しました！")
    else:
        min_left = int(res.total_seconds() // 60)
        
        # 通知予約を登録（20分後）
        now = datetime.datetime.now(JST)
        target_time = now + datetime.timedelta(minutes=20)
        
        new_data = {
            'user_id': interaction.user.id,
            'channel_id': interaction.channel_id,
            'target_time': target_time.isoformat(),
            'cooldown_min': 20,
            'notification_type': 'work'
        }
        
        queue = []
        if os.path.exists("reminders.json"):
            with open("reminders.json", "r") as f:
                try: 
                    queue = json.load(f)
                except (json.JSONDecodeError, ValueError): 
                    queue = []
        
        # 同じユーザー&通知タイプの既存予約を削除（重複防止）
        queue = [
            r for r in queue 
            if not (r.get('user_id') == interaction.user.id and r.get('notification_type') == 'work')
        ]
        queue.append(new_data)
        
        with open("reminders.json", "w") as f:
            json.dump(queue, f, indent=4)
        
        await interaction.response.send_message(
            f"☕ 休憩中... あと {min_left}分 お待ちください。\n"
            f"20分後にこのチャンネルで通知します。",
            ephemeral=True
        )

@app_commands.command(name="exchange", description="ECを本家マネーに換金申請します")
async def exchange(interaction: discord.Interaction, amount: float):
    if amount <= 0: return
    rate = economy.get_current_rate()
    # 本家資産チェック
    has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, amount * rate)
    if not has_assets:
        await interaction.response.send_message(f"本家資産が不足しています（信頼性確保のため、申請額の10倍の資産が必要です）", ephemeral=True)
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
            await interaction.response.send_message("申請を送信しました。管理者の承認をお待ちください。")
    else:
        await interaction.response.send_message("EC残高が足りません。", ephemeral=True)

@app_commands.command(name="buy_ec", description="本家マネーでECを購入申請します")
async def buy_ec(interaction: discord.Interaction, amount: float):
    if amount <= 0: return
    rate = economy.get_current_rate()
    cost = amount * rate
    has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, cost)
    if not has_assets:
        await interaction.response.send_message(f"本家資産が不足しています。", ephemeral=True)
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
        await interaction.response.send_message(f"購入申請を送信しました。管理者に {cost:.0f} Moneyを送金してください。")

def setup_economy_commands(bot):
    cmds = [money, rate, ec_work, exchange, buy_ec]
    for c in cmds:
        if c.name not in [cmd.name for cmd in bot.tree.get_commands()]:
            bot.tree.add_command(c)