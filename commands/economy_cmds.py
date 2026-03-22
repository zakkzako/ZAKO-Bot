import discord
from discord import app_commands
import economy
import math
import datetime
import jst
import logging
import database
import views.EconomyApplication as EconomyApplicationViews
from _images_ import Imgs

logger = logging.getLogger(__name__)
JST = jst.get_jst()
NOTIFICATION_TYPE_WORK = 'work'
WORK_COOLDOWN_MINUTES = 45

async def _schedule_work_notification(user_id: int, channel_id: int, cooldown_minutes: int) -> None:
    """通知をDBに予約する内部関数"""
    try:
        now = datetime.datetime.now(JST)
        target_time = now + datetime.timedelta(minutes=cooldown_minutes)

        # 既存の予約（workタイプ）があるか確認
        row = await database.fetch_one(
            "SELECT id FROM reminders WHERE user_id = ? AND notification_type = ?", 
            (user_id, NOTIFICATION_TYPE_WORK)
        )

        if row:
            return  # すでに予約があれば何もしない

        # 新規予約を挿入
        await database.execute_query(
            "INSERT INTO reminders (user_id, channel_id, target_time, cooldown_min, notification_type) VALUES (?, ?, ?, ?, ?)",
            (user_id, channel_id, target_time.isoformat(), cooldown_minutes, NOTIFICATION_TYPE_WORK)
        )
    except Exception as e:
        logger.error(f"Failed to schedule work notification for user {user_id}: {e}")

@app_commands.command(name="money", description="所持ECを確認します")
async def money(interaction: discord.Interaction):
    row = await database.fetch_one("SELECT balance FROM users WHERE user_id = ?", (interaction.user.id,))
    balance = row['balance'] if row else 0.0
    rate = await economy.get_current_rate()
    embed = discord.Embed(title="あなたの所持金", color=0x00ff00)
    embed.add_field(name="所持EC", value=f"{balance:.2f} EC")
    embed.add_field(name="本家換算額", value=f"約 {math.floor(balance * rate)} コイン")
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="rate", description="現在のレートを確認します")
async def rate(interaction: discord.Interaction):
    r = await economy.get_current_rate()
    await interaction.response.send_message(f"📈 換金レート: **1 EC = {r:.4f} コイン**")

@app_commands.command(name="economy", description="経済統計を確認します")
async def economy_stats(interaction: discord.Interaction):
    total_supply = await economy.get_total_supply()
    rate = await economy.get_current_rate()
    embed = discord.Embed(title="経済統計", color=0x00ffff)
    embed.add_field(name="総発行EC", value=f"{total_supply:,.2f} EC", inline=False)
    embed.add_field(name="交換レート", value=f"1 EC = {rate:.4f} Money", inline=False)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="ec_work", description="ECを獲得します（45分に1回）")
async def ec_work(interaction: discord.Interaction):
    """EC獲得コマンドの本体"""
    success, res = await economy.process_work(interaction.user.id)
    if success:
        # 1. 成功時のメッセージ
        await interaction.response.send_message(
            f"⛏ **{res} EC** を獲得しました！\n"
            f"{WORK_COOLDOWN_MINUTES}分後に `/ec_work` が再度利用可能になったタイミングで通知を送ります。"
        )
        # 2. 通知をスケジュール
        await _schedule_work_notification(
            interaction.user.id,
            interaction.channel_id,
            WORK_COOLDOWN_MINUTES
        )
    else:
        # クールダウン中の処理
        min_left = int(res.total_seconds() // 60)

        # 1. クールダウン終了時の通知をスケジュール（現在の残り時間で予約）
        await _schedule_work_notification(
            interaction.user.id,
            interaction.channel_id,
            min_left
        )
        # 2. ユーザーへの応答
        await interaction.response.send_message(
            f"クールタイム中 あと {min_left}分 お待ちください。\n"
            f"{min_left}分後にこのチャンネルで通知します。",
            ephemeral=True
        )


@app_commands.command(name="exchange_on_dev", description="（開発用）交換申請")
@app_commands.describe(type="交換の種類")
@app_commands.choices(type=[
    app_commands.Choice(name="EC -> TC", value="ec_to_tc"),
    app_commands.Choice(name="TC -> EC", value="tc_to_ec"),
])
async def exchange_dev(interaction: discord.Interaction, type: app_commands.Choice[str], amount: float):
    if interaction.channel_id != 1458677806388220006:
        return await interaction.response.send_message("テスト用ch専用です。", ephemeral=True)
    
    rate = await economy.get_current_rate()
    if type.value == "ec_to_tc":
        is_ok, rem = await economy.check_exchange_limit(interaction.user.id, amount, rate)
        if not is_ok: return await interaction.response.send_message(f"上限オーバー。残り: {rem:.0f} Money", ephemeral=True)
        success, _ = await economy.collect_ec_for_exchange(interaction.user.id, amount)
        if not success: return await interaction.response.send_message("EC不足です。", ephemeral=True)
        
        row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
        ch_id = int(row['value']) if row else 1457893837824331786
        ch = interaction.client.get_channel(ch_id) or await interaction.client.fetch_channel(ch_id)
        
        embed = discord.Embed(title="交換申請 (EC -> TC)", color=0xffa500)
        embed.add_field(name="ユーザー", value=interaction.user.mention)
        embed.add_field(name="金額", value=f"{amount} EC ({amount*rate:,.0f} TC)")
        await ch.send(embed=embed, view=EconomyApplicationViews.EC_to_TC(interaction.client))
        await interaction.response.send_message("申請を受理しました。")
    else:
        has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, amount * rate)
        if not has_assets: return await interaction.response.send_message("本家資産が足りません。", ephemeral=True)
        
        row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
        ch_id = int(row['value']) if row else 1457893837824331786
        ch = interaction.client.get_channel(ch_id) or await interaction.client.fetch_channel(ch_id)
        
        embed = discord.Embed(title="交換申請 (TC -> EC)", color=0x00ffff)
        embed.add_field(name="ユーザー", value=interaction.user.mention)
        embed.add_field(name="発行額", value=f"{amount} EC")
        await ch.send(embed=embed, view=EconomyApplicationViews.TC_to_EC(interaction.client))
        await interaction.response.send_message("申請を送信しました。")

@app_commands.command(name="exchange", description="換金申請")
async def exchange(interaction: discord.Interaction, amount: float):
    await interaction.response.defer()
    rate = await economy.get_current_rate()
    is_ok, rem = await economy.check_exchange_limit(interaction.user.id, amount, rate)
    if not is_ok: return await interaction.followup.send(f"上限オーバー。残り: {rem:.0f} Money")
    
    success, _ = await economy.collect_ec_for_exchange(interaction.user.id, amount)
    if success:
        await economy.add_exchange_record(interaction.user.id, amount, rate)
        row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
        ch_id = int(row['value']) if row else None
        if ch_id:
            ch = interaction.client.get_channel(ch_id)
            embed = discord.Embed(title="💰 換金申請", color=0xffa500)
            embed.add_field(name="ユーザー", value=interaction.user.mention)
            embed.add_field(name="金額", value=f"{amount} EC")
            msg = await ch.send(embed=embed)
            await msg.add_reaction("✅")
        await interaction.followup.send("申請を受理しました。")
    else:
        await interaction.followup.send("EC不足です。", ephemeral=True)

@app_commands.command(name="buy_ec", description="EC購入申請")
async def buy_ec(interaction: discord.Interaction, amount: float):
    rate = await economy.get_current_rate()
    has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, amount * rate)
    if not has_assets: return await interaction.response.send_message("資産不足です。", ephemeral=True)
    
    row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
    ch_id = int(row['value']) if row else None
    if ch_id:
        ch = interaction.client.get_channel(ch_id)
        embed = discord.Embed(title="💎 EC購入申請", color=0x00ffff)
        embed.add_field(name="ユーザー", value=interaction.user.mention)
        embed.add_field(name="発行額", value=f"{amount} EC")
        msg = await ch.send(embed=embed)
        await msg.add_reaction("✅")
    await interaction.response.send_message("申請を送信しました。")

def setup_economy_commands(bot):
    cmds = [money, rate, ec_work, economy_stats, exchange, buy_ec, exchange_dev]
    for c in cmds:
        if c.name not in [cmd.name for cmd in bot.tree.get_commands()]:
            bot.tree.add_command(c)
