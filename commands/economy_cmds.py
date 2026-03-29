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

@app_commands.command(name="money", description="所持ECと TakasumiBOT コイン 換算額を確認します")
async def money(interaction: discord.Interaction):
    row = await database.fetch_one("SELECT balance FROM users WHERE user_id = ?", (interaction.user.id,))
    balance = row['balance'] if row else 0.0
    rate = await economy.get_current_rate()
    
    embed = discord.Embed(title="あなたの所持金", color=0x00ff00)
    embed.add_field(name="所持EC", value=f"{balance:.2f} EC", inline=True)
    takasumimoney = math.floor(balance * rate)
    embed.add_field(name="本家換算額", value=f"約 {takasumimoney} コイン" if takasumimoney else "0 コイン", inline=True)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="rate", description="現在の1ECあたりの価値を確認します")
async def rate(interaction: discord.Interaction):
    r = await economy.get_current_rate()
    await interaction.response.send_message(f"📈 現在の換金レート: **1 EC = {r:.4f} コイン**")

@app_commands.command(name="economy", description="経済システムの統計情報を確認します")
async def economy_stats(interaction: discord.Interaction):
    total_supply = await economy.get_total_supply()
    rate = await economy.get_current_rate()
    
    embed = discord.Embed(title="経済統計", color=0x00ffff)
    embed.add_field(name="総発行EC", value=f"{total_supply:,.2f} EC", inline=False)
    embed.add_field(name="交換レート", value=f"1 EC = {rate:.4f} Money", inline=False)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="ec_work", description="ECを獲得します（45分に1回）")
async def ec_work(interaction: discord.Interaction):
    success, res = await economy.process_work(interaction.user.id)
    
    if success:
        await interaction.response.send_message(
            f"⛏ **{res} EC** を獲得しました！\n"
            f"{WORK_COOLDOWN_MINUTES}分後に `/ec_work` が再度利用可能になったタイミングで通知を送ります。"
        )
        await _schedule_work_notification(interaction.user.id, interaction.channel_id, WORK_COOLDOWN_MINUTES)
    else:
        min_left = int(res.total_seconds() // 60)
        await _schedule_work_notification(interaction.user.id, interaction.channel_id, min_left)
        await interaction.response.send_message(
            f"クールタイム中 あと {min_left}分 お待ちください。\n"
            f"{min_left}分後にこのチャンネルで通知します。",
            ephemeral=True
        )

@app_commands.command(name="exchange_on_dev", description="（開発用）交換申請をします")
@app_commands.describe(type="交換の種類")
@app_commands.choices(type=[
    app_commands.Choice(name="EC -> TakasumiBOT コイン", value="ec_to_tc"),
    app_commands.Choice(name="TakasumiBOT コイン -> EC", value="tc_to_ec"),
])
async def exchange_dev(interaction: discord.Interaction, type: app_commands.Choice[str], amount: float):
    if interaction.channel_id != 1458677806388220006:
        return await interaction.response.send_message("このコマンドは管理者のテスト用のチャンネルでのみ使用できます。", ephemeral=True)
    
    if amount <= 0:
        return await interaction.response.send_message("金額は **0** より大きくしてください。", ephemeral=True)

    rate = await economy.get_current_rate()
    
    # ログ用チャンネルの取得
    row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
    log_ch_id = int(row['value']) if row else 1457893837824331786
    log_ch = interaction.client.get_channel(log_ch_id) or await interaction.client.fetch_channel(log_ch_id)

    if type.value == "ec_to_tc":
        is_ok, remaining = await economy.check_exchange_limit(interaction.user.id, amount, rate)
        if not is_ok:
            return await interaction.response.send_message(f"❌ 上限オーバーです。\n本日の残り枠: {remaining:.0f} Money", ephemeral=True)
        
        success, _ = await economy.collect_ec_for_exchange(interaction.user.id, amount)
        if not success:
            return await interaction.response.send_message("❌ ECが不足しています（手数料10%が必要です）", ephemeral=True)

        # 管理者ログ
        log_embed = discord.Embed(title="交換申請 (EC -> TC)", color=0xffa500)
        log_embed.add_field(name="ユーザー", value=interaction.user.mention)
        log_embed.add_field(name="換金額", value=f"{amount} EC")
        log_embed.add_field(name="換算額", value=f"{amount * rate:,.0f} コイン")
        log_embed.add_field(name="状態", value="-# 保留中")
        await log_ch.send(embed=log_embed, view=EconomyApplicationViews.EC_to_TC(interaction.client))

        # ユーザー応答
        embed = discord.Embed(title="✅ 換金申請を受理しました", color=0x00ff00)
        embed.description = f"**{amount} EC**（約 {amount * rate:,.0f} コイン）の換金申請を受け付けました。\n管理者が承認するまでお待ちください。"
        embed.set_footer(text="手数料10%をあわせた金額を徴収しました")
        await interaction.response.send_message(embed=embed)

    elif type.value == "tc_to_ec":
        total_money_needed = amount * rate * 1.10  # 10% 手数料込み
        has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, amount * rate)
        if not has_assets:
            embed_no_assets = discord.Embed(description=f"信頼性確保のため、換金相当額の1.5倍（{math.ceil(amount * rate * 1.5)} コイン）の資産が必要です。", color=0xff0000)
            embed_no_assets.set_author(name="TakasumiBOT コイン が不足しています", icon_url=Imgs.CROSS)
            return await interaction.response.send_message(embed=embed_no_assets, ephemeral=True)

        # 管理者ログ
        log_embed = discord.Embed(title="交換申請 (TC -> EC)", color=0x00ffff)
        log_embed.add_field(name="ユーザー", value=interaction.user.mention)
        log_embed.add_field(name="発行額", value=f"{amount} EC")
        log_embed.add_field(name="合計請求額", value=f"{total_money_needed:,.0f} コイン")
        log_embed.add_field(name="状態", value="-# 保留中")
        await log_ch.send(embed=log_embed, view=EconomyApplicationViews.TC_to_EC(interaction.client))
        await interaction.response.send_message("申請を送信しました。")

@app_commands.command(name="exchange", description="ECを換金申請します（1日2万Moneyまで）")
async def exchange(interaction: discord.Interaction, amount: float):
    await interaction.response.defer()
    
    if amount <= 0:
        return await interaction.followup.send("金額は0より大きくしてください。", ephemeral=True)

    rate = await economy.get_current_rate()
    is_ok, remaining = await economy.check_exchange_limit(interaction.user.id, amount, rate)
    if not is_ok:
        return await interaction.followup.send(f"❌ 上限オーバーです。本日の残り枠: {remaining:.0f} Money")
    
    success, _ = await economy.collect_ec_for_exchange(interaction.user.id, amount)
    if success:
        await economy.add_exchange_record(interaction.user.id, amount, rate)
        
        row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
        ch_id = int(row['value']) if row else None
        
        if ch_id:
            ch = interaction.client.get_channel(ch_id) or await interaction.client.fetch_channel(ch_id)
            log_embed = discord.Embed(title="💰 換金申請", color=0xffa500)
            log_embed.add_field(name="ユーザー", value=interaction.user.mention)
            log_embed.add_field(name="換金額", value=f"{amount} EC")
            log_embed.add_field(name="換算額", value=f"{amount * rate:,.0f} Money")
            msg = await ch.send(embed=log_embed)
            await msg.add_reaction("✅")

        # ユーザーへの詳細フィードバック
        embed = discord.Embed(title="✅ 換金申請を受理しました", color=0x00ff00)
        embed.description = f"**{amount} EC** (約 {amount * rate:,.0f} Money) の換金申請を受け付けました。\n管理者が承認するまでお待ちください。"
        embed.set_footer(text="※手数料10%が含まれた金額が既に差し引かれています")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ ECが不足しています（手数料10%が必要です）", ephemeral=True)

@app_commands.command(name="buy_ec", description="Takasumi moneyでECを購入申請します（手数料5%）")
async def buy_ec(interaction: discord.Interaction, amount: float):
    if amount <= 0:
        return await interaction.response.send_message("金額は0より大きくしてください。", ephemeral=True)

    rate = await economy.get_current_rate()
    base_cost = amount * rate
    fee = base_cost * 0.05
    total_money = base_cost + fee

    # 1.5倍の資産チェック
    has_assets, _ = await economy.check_takasumi_assets(interaction.user.id, base_cost)
    if not has_assets:
        return await interaction.response.send_message(
            f"❌ Takasumi moneyが不足しています。\n"
            f"（信頼性確保のため、換金相当額の1.5倍（{base_cost * 1.5:,.0f} Money）の資産が必要です）", 
            ephemeral=True
        )
    
    row = await database.fetch_one("SELECT value FROM system_config WHERE key = 'log_channel'")
    ch_id = int(row['value']) if row else None
    
    if ch_id:
        ch = interaction.client.get_channel(ch_id) or await interaction.client.fetch_channel(ch_id)
        log_embed = discord.Embed(title="💎 EC購入申請", color=0x00ffff)
        log_embed.add_field(name="ユーザー", value=interaction.user.mention)
        log_embed.add_field(name="発行額", value=f"{amount} EC")
        log_embed.add_field(name="合計請求額", value=f"{total_money:,.0f} Money")
        msg = await ch.send(embed=log_embed)
        await msg.add_reaction("✅")

    # ユーザーへの詳細案内
    embed = discord.Embed(title="🛒 購入申請を受け付けました", color=0xffff00)
    embed.add_field(name="購入希望額", value=f"{amount} EC", inline=True)
    embed.add_field(name="レート", value=f"1 EC = {rate:.4f}", inline=True)
    embed.add_field(name="本家送金額", value=f"{base_cost:,.0f} Money", inline=True)
    embed.add_field(name="手数料(5%)", value=f"{fee:,.0f} Money", inline=True)
    embed.add_field(name="**合計振込額**", value=f"**{total_money:,.0f} Money**", inline=False)
    embed.description = "上記合計金額を管理人に送金してください。入金確認後、ECが発行されます。"
    await interaction.response.send_message(embed=embed)

def setup_economy_commands(bot):
    cmds = [money, rate, ec_work, economy_stats, exchange, buy_ec, exchange_dev]
    for c in cmds:
        if c.name not in [cmd.name for cmd in bot.tree.get_commands()]:
            bot.tree.add_command(c)
