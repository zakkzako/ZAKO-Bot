import discord
from discord import app_commands
import datetime
import pytz
import importlib
import os
import json
import notification
import updater
import jikoku
import economy
import general_commands
import admin_commands
import economy_commands
import gambling_commands
import jst
import logging
from _notification_types_ import NOTIFICATION_TYPES

JST = jst.get_jst()
admin_id_env = os.getenv('ADMIN_ID')
"""ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []"""
ADMIN_IDS = [ 1158268839721717781, 1160453651660288041 ]  # 管理者チェックがうまくいかないため、一時的にハードコーディングしています。ゆるして  by yamatomato0105

logger = logging.getLogger(__name__)

# ZAKO-Bot Community の 失業保険失効通知専用チャンネル のキャッシュ
UNEMPLOYMENT_NOTIFY_CHANNEL: discord.TextChannel | None = None

# Notification type constants
WORK_COOLDOWN_MINUTES = 20

async def init_system(bot):
    global UNEMPLOYMENT_NOTIFY_CHANNEL
    UNEMPLOYMENT_NOTIFY_CHANNEL = bot.get_channel(1473864813506465903) or await bot.fetch_channel(1473864813506465903)
    try:
        await bot.tree.sync()
    except Exception as e:
        logger.error(f"Sync Error: {e}")

async def check_reminders(bot):
    await updater.perform_full_update()
    try:
        await jikoku.announce_time(bot)
    except Exception as e:
        logger.error(f"Jihou Error: {e}")

    now = datetime.datetime.now(JST)
    if not os.path.exists("reminders.json"):
        return
    queue: list[dict] = []
    with open("reminders.json", "r") as f:
        try: queue = json.load(f)
        except json.JSONDecodeError:
            logger.warning("JSON Decode Error in reminders.json")

    updated_queue: list[dict] = []
    for r in queue:
        target_time = datetime.datetime.fromisoformat(r['target_time'])
        if now >= target_time:
            channel = bot.get_channel(r.get('channel_id')) or bot.fetch_channel(r.get('channel_id'))
            user = r['user_id']
            if channel and user:
                try:
                    notification_type = r.get('notification_type', NOTIFICATION_TYPES.EXTERNAL_WORK)

                    # --- ここから通知メッセージの分岐 ---
                    if notification_type == NOTIFICATION_TYPES.UNEMPLOYMENT_INSURANCE:
                        if channel.guild.id == 1455450215313309763:
                            channel = UNEMPLOYMENT_NOTIFY_CHANNEL
                        # 失業保険（TakasumiBOT）の通知
                        await channel.send(f"<@{user}> 失業保険が間もなく失効します\n</pay:1132518157119135775> で失業保険を購入しましょう。")

                    elif notification_type == NOTIFICATION_TYPES.WORK:
                        # 内部workコマンドの通知
                        await channel.send(f"<@{user}> `/work` から{r.get('cooldown_min', WORK_COOLDOWN_MINUTES)}分が経過しました。\n再度 </work:1471034168853925942> を実行できます！")

                    elif notification_type == NOTIFICATION_TYPES.EXTERNAL_WORK:
                        # 外部bot（TakasumiBOT）のwork検知による通知
                        await channel.send(f"<@{user}> workから{r.get('cooldown_min', WORK_COOLDOWN_MINUTES)}分が経過しました。\n</work:1132868147519692871> が再度実行できます")
                    elif notification_type == NOTIFICATION_TYPES.STEAL:
                        # 外部bot（TakasumiBOT）のsteal検知による通知
                        await channel.send(f"<@{user}> stealから2時間が経過しました。\n</steal:1436546809894932584> が再度実行できます")
                    else:
                        raise ValueError(f"Unknown notification type: {notification_type}")
                except Exception as e:
                    logger.error(f"Notification send error: {e}")
            continue
        updated_queue.append(r)
    with open("reminders.json", "w") as f:
        json.dump(updated_queue, f, indent=4)

async def process_message_event(bot, message):
    if message.author.bot and message.embeds:
        for embed in message.embeds:
            desc = embed.description or ""
            fields_text = "".join([f.value for f in embed.fields])
            if "給料:" in desc or "給料:" in fields_text:
                importlib.reload(notification)
                await notification.handle_work_detection(bot, message, embed)
            elif "失業保険" in desc and "購入しました" in desc:
                # ユーザー特定ロジックは既存のものを流用（適宜変数名を合わせてください）
                user = None
                if message.interaction_metadata: user = message.interaction_metadata.user
                elif message.mentions: user = message.mentions[0]
                if user:
                    importlib.reload(notification)
                    await notification.handle_unemployment_detection(bot, message, user, desc)
            elif "から盗めませんでした" in desc or "から盗みました" in desc:
                importlib.reload(notification)
                await notification.handle_steal_detection(bot, message)

# EC -> TC 承認処理
async def handle_economy_application_exchange_ec(bot, interaction, approved):
    if interaction.user.id not in ADMIN_IDS:
        return

    """承認チェック"""
    if approved == True:
        # 承認
        try:
            importlib.reload(economy)
            embed = interaction.message.embeds[0]
            uid = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            user = bot.get_user(uid)
            amount = float((embed.fields[1].value).split(" ")[0])
            new_rate = await economy.confirm_exchange(amount, "ec", user)
            embed.fields[3].value = f"✅ 承認済み（レート: {new_rate:.4f}）"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Confirmed: Exchange to EC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to EC Error: {e}")

    elif approved == False:
        # 却下
        try:
            embed = interaction.message.embeds[0]
            user = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            amount = float((embed.fields[1].value).split(" ")[0])
            embed.fields[3].value = "❌ 却下済み"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Denied: Exchange to EC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to EC Denial Error: {e}")

# TC -> EC 承認処理
async def handle_economy_application_exchange_tc(bot, interaction, approved):
    if interaction.user.id not in ADMIN_IDS:
        return

    """承認チェック"""
    if approved == True:
        # 承認
        try:
            importlib.reload(economy)
            embed = interaction.message.embeds[0]
            uid = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            user = bot.get_user(uid)
            amount = float((embed.fields[1].value).split(" ")[0])
            new_rate = await economy.confirm_exchange(amount, "tc", user)
            embed.fields[3].value = f"✅ 承認済み（レート: {new_rate:.4f}）"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Confirmed: Exchange to TC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to TC Error: {e}")
    elif approved == False:
        # 却下
        try:
            embed = interaction.message.embeds[0]
            user = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            amount = float((embed.fields[1].value).split(" ")[0])
            embed.fields[3].value = "❌ 却下済み"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Denied: Exchange to TC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to TC Denial Error: {e}")

async def handle_reaction_event(bot, payload):
    if payload.user_id not in ADMIN_IDS or str(payload.emoji) != "✅":
        return

    channel = bot.get_channel(payload.channel_id)
    try: message = await channel.fetch_message(payload.message_id)
    except: return

    if not (message.author.id == bot.user.id and message.embeds): return
    embed = message.embeds[0]

    try:
        # 最新の経済ロジックを読み込み
        importlib.reload(economy)
        user_mention = embed.fields[0].value
        user_id = int(user_mention.replace("<@", "").replace(">", "").replace("!", ""))
        amount = float(embed.fields[1].value.split(" ")[0])

        if embed.title == "💰 換金申請":
            new_rate = await economy.confirm_exchange_burn(amount)
            await message.edit(content=f"✅ **換金完了** (レート: {new_rate:.4f})", embed=None)
        elif embed.title == "💎 EC購入申請":
            new_rate = await economy.confirm_buy_issue(user_id, amount)
            await message.edit(content=f"✅ **購入完了** (レート: {new_rate:.4f})", embed=None)

        logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Confirmed: {embed.title} for {user_id}")
    except Exception as e:
        logger.error(f"Reaction Process Error: {e}")

def register_to_tree(bot):
    try:
        importlib.reload(general_commands)
        importlib.reload(admin_commands)
        importlib.reload(economy_commands) 
        importlib.reload(gambling_commands)
        general_commands.setup_general_commands(bot)
        admin_commands.setup_admin_commands(bot)
        economy_commands.setup_economy_commands(bot)
        gambling_commands.setup_gambling_commands(bot)
        # 必要に応じて同期も行う
        bot.loop.create_task(bot.tree.sync())
        logger.info("Modules reloaded and tree synced.")
    except Exception as e:
        logger.error(f"Registration Error: {e}")
