import discord
from discord import app_commands
import economy
import aiohttp
import datetime
import pytz
import json
import os
import jst

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

        # 3. 重複チェック (読み込んだ後に判定する)
        if any(r.get('user_id') == user_id and r.get('notification_type') == NOTIFICATION_TYPE_WORK for r in queue):
            print(f"【{datetime.datetime.now(JST)}】[Work] 通知予約をスキップ: User {user_id} は既に予約済みです。")
            return 
        # 既存の予約があるか確認
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
@app_commands.command(name="money", description="所持ECとTakasumiBot money換算額を確認します")
async def money(interaction: discord.Interaction):
    users = economy.load_json("users.json", {})
    balance = users.get(str(interaction.user.id), {}).get("balance", 0.0)
    rate = await economy.get_current_rate()
    embed = discord.Embed(title="あなたの所持金", color=0x00ff00)
    embed.add_field(name="所持EC", value=f"{balance:.2f} EC", inline=True)
    embed.add_field(name="本家換算額", value=f"約 {balance * rate:.0f} Money", inline=True)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="rate", description="現在の1ECあたりの価値を確認します")
async def rate(interaction: discord.Interaction):
        r = await economy.get_current_rate()
        await interaction.response.send_message(f"📈 現在の換金レート: **1 EC = {r:.4f} TakasumiBOT Money**")

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
