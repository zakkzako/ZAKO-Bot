import discord
from discord import app_commands
import datetime
import pytz
import importlib
import os
import notification
import updater
import jikoku
import economy
from commands import general
from commands import admin
from commands import economy_cmds
from commands import gambling
import jst
import logging
import notification_settings
import database
from _notification_types_ import NOTIFICATION_TYPES

JST = jst.get_jst()
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [ 1158268839721717781, 1160453651660288041 ]

logger = logging.getLogger(__name__)

UNEMPLOYMENT_NOTIFY_CHANNEL: discord.TextChannel | None = None
WORK_COOLDOWN_MINUTES = 20

async def init_system(bot):
    try:
        global UNEMPLOYMENT_NOTIFY_CHANNEL
        UNEMPLOYMENT_NOTIFY_CHANNEL = bot.get_channel(1473864813506465903) or await bot.fetch_channel(1473864813506465903)
        register_to_tree(bot)
        logger.info("System initialized")
    except Exception as e:
        logger.error(f"Initialization Error: {e}")

async def should_send_notification(bot, user_id: int, notification_type: str) -> bool:
    """ユーザーの設定に基づいて、通知を送るべきかを判定"""
    global UNEMPLOYMENT_NOTIFY_CHANNEL
    UNEMPLOYMENT_NOTIFY_CHANNEL = bot.get_channel(1473864813506465903) or await bot.fetch_channel(1473864813506465903)
    try:
        # load_settingsがasyncになったためawaitを追加
        settings = await notification_settings.NotificationSettingsView.load_settings(user_id)

        type_to_setting = {
            NOTIFICATION_TYPES.WORK: 'work',
            NOTIFICATION_TYPES.EXTERNAL_WORK: 'external_work',
            NOTIFICATION_TYPES.UNEMPLOYMENT_INSURANCE: 'unemployment_insurance',
            NOTIFICATION_TYPES.STEAL: 'steal'
        }

        setting_key = type_to_setting.get(notification_type, 'external_work')
        return settings.get(setting_key, True)
    except Exception as e:
        logger.error(f"Error loading notification settings for user {user_id}: {e}")
        return True

async def check_reminders(bot):
    await updater.perform_full_update()
    try:
        await jikoku.announce_time(bot)
    except Exception as e:
        logger.error(f"Jihou Error: {e}")

    now = datetime.datetime.now(JST)
    now_iso = now.isoformat()

    # DBから時間が来ている（または過ぎている）リマインダーだけを取得
    rows = await database.fetch_all("SELECT * FROM reminders WHERE target_time <= ?", (now_iso,))
    
    if not rows:
        return

    processed_ids = []

    for r in rows:
        rem_id = r['id']
        user_id = r['user_id']
        channel_id = r['channel_id']
        notification_type = r['notification_type']
        cooldown_min = r['cooldown_min']

        # 処理対象としてIDを記録
        processed_ids.append(rem_id)

        try:
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        except Exception as e:
            if hasattr(e, 'status') and e.status == 403:
                logger.warning(f"Channel access forbidden for channel ID {channel_id}")
            elif hasattr(e, 'status') and e.status == 404:
                logger.warning(f"Channel not found for channel ID {channel_id}")
            else:
                logger.error(f"Error fetching channel ID {channel_id}: {e}")
            continue

        if channel and user_id:
            if not await should_send_notification(bot, user_id, notification_type):
                continue
                
            try:
                if notification_type == NOTIFICATION_TYPES.UNEMPLOYMENT_INSURANCE:
                    if channel.guild.id == 1455450215313309763:
                        await channel.send(f"<@{user_id}> 失業保険が間もなく失効します\n<#1455515562255056948> で </pay:1132518157119135775> を実行して失業保険を購入しましょう。")
                    else:
                        await channel.send(f"<@{user_id}> 失業保険が間もなく失効します\n</pay:1132518157119135775> を実行して失業保険を購入しましょう。")

                elif notification_type == NOTIFICATION_TYPES.WORK:
                    await channel.send(f"<@{user_id}> `/ec_work` から{cooldown_min}分が経過しました。\n再度 </ec_work:1485251320268066896> を実行できます！")

                elif notification_type == NOTIFICATION_TYPES.EXTERNAL_WORK:
                    await channel.send(f"<@{user_id}> workから{cooldown_min}分が経過しました。\n</work:1132868147519692871> が再度実行できます")
                
                elif notification_type == NOTIFICATION_TYPES.STEAL:
                    await channel.send(f"<@{user_id}> stealから2時間が経過しました。\n</steal:1436546809894932584> が再度実行できます")
                else:
                    logger.warning(f"Unknown notification type: {notification_type}")
            except Exception as e:
                logger.error(f"Notification send error: {e}")
                continue

    # 処理が終わったリマインダーを一括でDBから削除
    if processed_ids:
        placeholders = ','.join('?' * len(processed_ids))
        await database.execute_query(f"DELETE FROM reminders WHERE id IN ({placeholders})", tuple(processed_ids))

async def process_message_event(bot, message):
    if message.author.bot and message.embeds:
        if not message.guild:
            return

        bot_member = message.guild.get_member(bot.user.id) or await message.guild.fetch_member(bot.user.id)
        if not bot_member.guild_permissions.view_channel or not bot_member.guild_permissions.send_messages:
            logger.warning(f"Missing permissions in guild {message.guild.id} for notify. Skipping message processing.")
            await message.reply(embed=discord.Embed(description="通知を送信するのに必要な権限が不足しています。サーバー管理者にお問い合わせください。", color=discord.Color.red()))
            return

        for embed in message.embeds:
            desc = embed.description or ""
            fields_text = "".join([f.value for f in embed.fields])
            if "給料:" in desc or "給料:" in fields_text:
                importlib.reload(notification)
                await notification.handle_work_detection(bot, message, embed)
            elif "失業保険" in desc and "購入しました" in desc:
                user = None
                if message.interaction_metadata: user = message.interaction_metadata.user
                elif message.mentions: user = message.mentions[0]
                if user:
                    importlib.reload(notification)
                    await notification.handle_unemployment_detection(bot, message, user, desc)
            elif "から盗めませんでした" in desc or "から盗みました" in desc:
                importlib.reload(notification)
                await notification.handle_steal_detection(bot, message)

async def handle_economy_application_exchange_ec(bot, interaction, approved):
    if interaction.user.id not in ADMIN_IDS:
        return

    if approved == True:
        try:
            importlib.reload(economy)
            embed = interaction.message.embeds[0]
            uid = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            user = bot.get_user(uid)
            amount = float((embed.fields[1].value).split(" ")[0])
            new_rate = await economy.confirm_exchange(amount, "ec", user.id) # user_idを渡すよう修正
            embed.fields[3].value = f"✅ 承認済み（レート: {new_rate:.4f}）"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Confirmed: Exchange to EC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to EC Error: {e}")

    elif approved == False:
        try:
            embed = interaction.message.embeds[0]
            uid = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            user = bot.get_user(uid)
            embed.fields[3].value = "❌ 却下済み"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Denied: Exchange to EC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to EC Denial Error: {e}")

async def handle_economy_application_exchange_tc(bot, interaction, approved):
    if interaction.user.id not in ADMIN_IDS:
        return

    if approved == True:
        try:
            importlib.reload(economy)
            embed = interaction.message.embeds[0]
            uid = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            user = bot.get_user(uid)
            amount = float((embed.fields[1].value).split(" ")[0])
            new_rate = await economy.confirm_exchange(amount, "tc", user.id) # user_idを渡すよう修正
            embed.fields[3].value = f"✅ 承認済み（レート: {new_rate:.4f}）"
            await interaction.message.edit(embed=embed, view=None)
            logger.info(f"【{datetime.datetime.now(JST)}】[Economy] Confirmed: Exchange to TC for {user.name} ({user.id})")
        except Exception as e:
            logger.error(f"Economy Exchange to TC Error: {e}")
    elif approved == False:
        try:
            embed = interaction.message.embeds[0]
            uid = int((embed.fields[0].value).replace("<@", "").replace(">", "").replace("!", ""))
            user = bot.get_user(uid)
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
        importlib.reload(general)
        importlib.reload(admin)
        importlib.reload(economy_cmds) 
        importlib.reload(gambling)
        importlib.reload(notification_settings) 
        general.setup_general_commands(bot)
        admin.setup_admin_commands(bot)
        economy_cmds.setup_economy_commands(bot)
        gambling.setup_gambling_commands(bot)
        notification_settings.setup_notification_commands(bot)
        logger.info("Modules reloaded")
    except Exception as e:
        logger.error(f"Registration Error: {e}")
