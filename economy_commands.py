import discord
from discord import app_commands
import economy
import aiohttp
import datetime
import pytz
import json
import math
import os
import jst
import logging
import views.EconomyApplication as EconomyApplicationViews
from _images_ import Imgs

logger = logging.getLogger(__name__)

JST = jst.get_jst()

# Notification type constants
NOTIFICATION_TYPE_WORK = 'work'
WORK_COOLDOWN_MINUTES = 45

def _schedule_work_notification(user_id: int, channel_id: int, cooldown_minutes: int, context: str) -> None:
    """
    Helper function to schedule work notifications
    
    Args:
        user_id: Discord user ID
        channel_id: Discord channel ID
        cooldown_minutes: Minutes until notification should be sent
        context: Context for error logging ('success' or 'cooldown')
    """
    try:
        now = datetime.datetime.now(JST)
        target_time = now + datetime.timedelta(minutes=cooldown_minutes)

        # 1. データを準備
        new_data = {
            'user_id': user_id,
            'channel_id': channel_id,
            'target_time': target_time.isoformat(),
            'cooldown_min': cooldown_minutes,
            'notification_type': NOTIFICATION_TYPE_WORK
        }

        # 2. ファイルを読み込んで queue を作成
        queue = []
        if os.path.exists("reminders.json"):
            with open("reminders.json", "r") as f:
                try:
                    queue = json.load(f)
                except json.JSONDecodeError:
                    queue = []

        # 3. 既存の予約があるか確認
        if any(r.get('user_id') == user_id and r.get('notification_type') == NOTIFICATION_TYPE_WORK for r in queue):
            return  # 予約があればここで終了

        # 4. 重複がなければ追加
        queue.append(new_data)

        with open("reminders.json", "w") as f:
            json.dump(queue, f, indent=4)
    except (OSError, json.JSONDecodeError) as e:
        # 通知スケジューリングの失敗は無視し、メイン機能に影響を与えない
        print(f"Failed to schedule {context} notification for user {user_id}: {e}")

# ユーザー向け経済コマンド
@app_commands.command(name="money", description="所持ECと TakasumiBOT コイン 換算額を確認します")
async def money(interaction: discord.Interaction):
    users = economy.load_json("users.json", {})
    balance = users.get(str(interaction.user.id), {}).get("balance", 0.0)
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
    # 現在の経済データを読み込み
    data = economy.load_json("economy_data.json", {"total_supply": 10000000.0})
    total_supply = data["total_supply"]
    rate = await economy.get_current_rate()

    embed = discord.Embed(title="経済統計", color=0x00ffff)
    embed.add_field(name="総発行EC", value=f"{total_supply:,.2f} EC", inline=False)
    embed.add_field(name="交換レート", value=f"1 EC = {rate:.4f} Money", inline=False)
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="work", description="ECを獲得します（45分に1回）")
async def ec_work(interaction: discord.Interaction):
    success, res = economy.process_work(interaction.user.id)

    if success:
        # 成功メッセージ（クールダウン終了時に通知が届くことを明示）
        await interaction.response.send_message(
            f"⛏ **{res} EC** を獲得しました！\n"
            f"{WORK_COOLDOWN_MINUTES}分後に `/work` が再度利用可能になったタイミングで通知を送ります。"
        )

        # 通知をスケジュール
        _schedule_work_notification(
            interaction.user.id,
            interaction.channel_id,
            WORK_COOLDOWN_MINUTES,
            'success'
        )

    else:
        # クールダウン中 - 残り時間で通知をスケジュール
        min_left = int(res.total_seconds() // 60)
        
        # 通知をスケジュール
        _schedule_work_notification(
            interaction.user.id,
            interaction.channel_id,
            min_left,
            'cooldown'
        )

        await interaction.response.send_message(
            f"クールタイム中 あと {min_left}分 お待ちください。\n"
            f"{min_left}分後にこのチャンネルで通知します。",
            ephemeral=True
        )

exchange_dev__choices___type = [
    app_commands.Choice(name="EC -> TakasumiBOT コイン", value="ec_to_tc"),
    app_commands.Choice(name="TakasumiBOT コイン -> EC", value="tc_to_ec"),
]
@app_commands.command(name="exchange_on_dev", description="（開発用）交換申請をします")
@app_commands.describe(type="交換の種類")
@app_commands.choices(type=exchange_dev__choices___type)
async def exchange_dev(interaction: discord.Interaction, type: app_commands.Choice[str], amount: float):
    # テスト用のチャンネルでのみ動作させる
    if interaction.channel_id != 1458677806388220006:
        await interaction.response.send_message("このコマンドは管理者のテスト用のチャンネルでのみ使用できます。", ephemeral=True)
        return

    """書き方は前バージョンに合わせてます  by yamatomato0105"""
    # EC -> TakasumiBOT コイン
    if type.value == "ec_to_tc":
        if amount <= 0:
            await interaction.response.send_message("金額は **0** より大きくしてください。", ephemeral=True)
            return

        # [1] 現在のレートを取得
        current_rate = await economy.get_current_rate()

        # [2] 制限チェック
        is_ok, remaining = economy.check_exchange_limit(interaction.user.id, amount, current_rate)
        if not is_ok:
            await interaction.response.send_message(f"❌ 上限オーバーです。\n本日の残り枠: {remaining:.0f} Money", ephemeral=True)
            return
        
        # [3] 所持金から回収
        success, collected = economy.collect_ec_for_exchange(interaction.user.id, amount)
        if not success:
            await interaction.response.send_message("❌ ECが不足しています（手数料10%が必要です）", ephemeral=True)
            return

        # [4] 申請チャンネルに送信
        config = economy.load_json("config.json", {})
        log_ch = None
        try:
            log_ch = interaction.client.fetch_channel(config.get("log_channel", 1457893837824331786))
        except discord.NotFound:
            await interaction.response.send_message("❌ 申請処理中にエラーが発生しました。管理者に連絡してください\n-# エラー： チャンネルの取得に失敗しました", ephemeral=True)
            logger.error(f"Failed to fetch log channel for exchange_dev by user {interaction.user.id}")
            return
        if not log_ch:
            await interaction.response.send_message("❌ 申請処理中に問題が発生しました。管理者に連絡してください\n-# エラー： チャンネルの取得に失敗しました", ephemeral=True)
            logger.error(f"Log channel not found for exchange_dev by user {interaction.user.id}")
            return
        log_embed = discord.Embed(title="交換申請 (EC -> TC)", color=0xffa500)
        log_embed.add_field(name="ユーザー", value=interaction.user.mention)
        log_embed.add_field(name="換金額", value=f"{amount} EC")
        log_embed.add_field(name="換算額", value=f"{amount * current_rate:,.0f} コイン")
        log_embed.add_field(name="状態", value="-# 保留中")
        await log_ch.send(embed=log_embed, view=EconomyApplicationViews.EC_to_TC())

        # [5] ユーザーに応答
        embed = discord.Embed(title="✅ 換金申請を受理しました", color=0x00ff00)
        embed.description = f"**{amount} EC**（約 {amount * current_rate:,.0f} コイン）の換金申請を受け付けました。\n管理者が承認するまでお待ちください。"
        embed.set_footer(text="手数料10%をあわせた金額を徴収しました")

    # TakasumiBOT コイン -> EC
    elif type.value == "tc_to_ec":
        if amount <= 0:
            await interaction.response.send_message("金額は **0** より大きくしてください。", ephemeral=True)
            return
        
        # [1] 現在のレートを取得
        current_rate = await economy.get_current_rate()

        # [2] 必要な情報を計算
        total_money_needed = amount * current_rate * 1.10  # 10% 手数料込み
        has_assets, current_assets = await economy.check_takasumi_assets(interaction.user.id, amount * current_rate)
        if not has_assets:
            embed_no_assets = discord.Embed(description=f"信頼性確保のため、換金相当額の1.5倍（{math.ceil(amount * current_rate * 1.5)} コイン）の資産が必要です。", color=0xff0000)
            embed_no_assets.set_author(name="TakasumiBOT コイン が不足しています", icon_url=Imgs.CROSS)
            await interaction.response.send_message(embed=embed_no_assets, ephemeral=True)
            return

        # [3] 申請チャンネルに送信
        config = economy.load_json("config.json", {})
        log_ch = None
        try:
            log_ch = interaction.client.fetch_channel(config.get("log_channel", 1457893837824331786))
        except discord.NotFound:
            await interaction.response.send_message("❌ 申請処理中にエラーが発生しました。管理者に連絡してください\n-# エラー： チャンネルの取得に失敗しました", ephemeral=True)
            logger.error(f"Failed to fetch log channel for exchange_dev by user {interaction.user.id}")
            return
        if not log_ch:
            await interaction.response.send_message("❌ 申請処理中に問題が発生しました。管理者に連絡してください\n-# エラー： チャンネルの取得に失敗しました", ephemeral=True)
            logger.error(f"Log channel not found for exchange_dev by user {interaction.user.id}")
            return
        log_embed = discord.Embed(title="交換申請 (TC -> EC)", color=0x00ffff)
        log_embed.add_field(name="ユーザー", value=interaction.user.mention)
        log_embed.add_field(name="発行額", value=f"{amount} EC")
        log_embed.add_field(name="合計請求額", value=f"{total_money_needed:,.0f} コイン")
        log_embed.add_field(name="状態", value="-# 保留中")
        await log_ch.send(embed=log_embed, view=EconomyApplicationViews.TC_to_EC())

@app_commands.command(name="exchange", description="ECを換金申請します（1日2万Moneyまで）")
async def exchange(interaction: discord.Interaction, amount: float):
    await interaction.response.defer() # タイムアウト対策
    
    # (1) 金額が0以下でないかチェック
    # (2) 現在のレートを取得
    rate = await economy.get_current_rate()

    # (3) 【追加】1日2万制限のチェックを呼び出す
    is_ok, remaining = economy.check_exchange_limit(interaction.user.id, amount, rate)
    if not is_ok:
        await interaction.followup.send(f"❌ 上限オーバーです。本日の残り枠: {remaining:.0f} Money")
        return

    # (4) ECの没収処理 (collect_ec_for_exchange)
    success, collected = economy.collect_ec_for_exchange(interaction.user.id, amount)
    
    if success:
        # (5) 【追加】没収できたら、その金額を本日の累計に加算する
        economy.add_exchange_record(interaction.user.id, amount, rate)
        
        # (6) ユーザーへ応答 & 管理者へログ送信
        config = economy.load_json("config.json", {})
        log_ch = interaction.client.get_channel(config.get("log_channel"))
        
        if log_ch:
            log_embed = discord.Embed(title="💰 換金申請", color=0xffa500)
            log_embed.add_field(name="ユーザー", value=interaction.user.mention)
            log_embed.add_field(name="換金額", value=f"{amount} EC")
            log_embed.add_field(name="換算額", value=f"{amount * rate:,.0f} Money")
            # 承認・拒否リアクションで core_system.handle_reaction_event が動く仕組み
            msg = await log_ch.send(embed=log_embed)
            await msg.add_reaction("✅")

        # (7) ユーザーへ完了報告
        embed = discord.Embed(title="✅ 換金申請を受理しました", color=0x00ff00)
        embed.description = f"**{amount} EC** (約 {amount * rate:,.0f} Money) の換金申請を受け付けました。\n管理者が承認するまでお待ちください。"
        embed.set_footer(text="※手数料10%が含まれた金額が既に差し引かれています")
        
        await interaction.followup.send(embed=embed) # deferしているので followup を使う
    else:
        await interaction.followup.send("❌ ECが不足しています（手数料10%が必要です）", ephemeral=True)



@app_commands.command(name="buy_ec", description="Takasumi moneyでECを購入申請します（手数料5%）")
async def buy_ec(interaction: discord.Interaction, amount: float):
    if amount <= 0:
        await interaction.response.send_message("金額は0より大きくしてください。", ephemeral=True)
        return

    rate = await economy.get_current_rate()
    base_cost = amount * rate
    fee = base_cost * 0.05
    total_money = base_cost + fee

    # 【重要】1.5倍の資産チェックを実行
    has_assets, current_assets = await economy.check_takasumi_assets(interaction.user.id, base_cost)

    if not has_assets:
        await interaction.response.send_message(
            f"❌ Takasumi moneyが不足しています。\n"
            f"（信頼性確保のため、換金相当額の1.5倍（{base_cost * 1.5:,.0f} Money）の資産が必要です）", 
            ephemeral=True
        )
        return

    # 管理者用ログ送信
    config = economy.load_json("config.json", {})
    log_ch = interaction.client.get_channel(config.get("log_channel"))
    if log_ch:
        log_embed = discord.Embed(title="💎 EC購入申請", color=0x00ffff)
        log_embed.add_field(name="ユーザー", value=interaction.user.mention)
        log_embed.add_field(name="発行額", value=f"{amount} EC")
        log_embed.add_field(name="合計請求額", value=f"{total_money:,.0f} Money")
        msg = await log_ch.send(embed=log_embed)
        await msg.add_reaction("✅")

    # ユーザーへの応答
    embed = discord.Embed(title="🛒 購入申請を受け付けました", color=0xffff00)
    embed.add_field(name="購入希望額", value=f"{amount} EC", inline=True)
    embed.add_field(name="レート", value=f"1 EC = {rate:.4f}", inline=True)
    embed.add_field(name="本家送金額", value=f"{base_cost:,.0f} Money", inline=True)
    embed.add_field(name="手数料(5%)", value=f"{fee:,.0f} Money", inline=True)
    embed.add_field(name="**合計振込額**", value=f"**{total_money:,.0f} Money**", inline=False)
    embed.description = "上記合計金額を管理人に送金してください。入金確認後、ECが発行されます。"

    await interaction.response.send_message(embed=embed)

def setup_economy_commands(bot):
    cmds = [money, rate, ec_work, economy_stats, exchange, buy_ec]
    for c in cmds:
        if c.name not in [cmd.name for cmd in bot.tree.get_commands()]:
            bot.tree.add_command(c)
#う
