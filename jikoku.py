import discord
import datetime
import json
import os
import jst
import logging

JST = jst.get_jst()
JIKOKU_STATE_FILE = "jikoku_state.json"

logger = logging.getLogger(__name__)

def _load_last_sent_hour():
    """最後に送信した時刻を読み込む"""
    if not os.path.exists(JIKOKU_STATE_FILE):
        return None
    try:
        with open(JIKOKU_STATE_FILE, "r") as f:
            data = json.load(f)
            hour_data = data.get("last_sent_hour")
            if isinstance(hour_data, (list, tuple)) and len(hour_data) == 4:
                try:
                    year, month, day, hour = (int(hour_data[0]), int(hour_data[1]), int(hour_data[2]), int(hour_data[3]))
                except (TypeError, ValueError):
                    logger.warning(f"Invalid jikoku state format (non-integer values): {hour_data}")
                    return None
                try:
                    # Validate that the loaded values form a valid datetime
                    datetime.datetime(year, month, day, hour)
                except ValueError:
                    logger.warning(f"Invalid jikoku state datetime values: {hour_data}")
                    return None
                return (year, month, day, hour)
            return None
    except Exception as e:
        logger.error(f"Failed to load jikoku state: {e}")
        return None

def _save_last_sent_hour(hour_key):
    """最後に送信した時刻を保存する"""
    try:
        # Write to temporary file first for atomic operation
        temp_file = JIKOKU_STATE_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump({"last_sent_hour": list(hour_key)}, f)
        # Atomically replace the old file
        os.replace(temp_file, JIKOKU_STATE_FILE)
    except Exception as e:
        logger.error(f"Failed to save jikoku state: {e}")

async def announce_time(bot):
    """毎正時に実行される時報処理"""
    if not os.path.exists("config.json"):
        return

    with open("config.json", "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON Decode Error: {e}")
            return

    channel_id = config.get("announcement_channel")
    if not channel_id:
        return

    now = datetime.datetime.now(JST)
    # 00分であることを確認（30秒間隔のループで呼ばれる想定）
    if now.minute == 0:
        # 通知済みチェック: 既にこの時刻に送信済みであれば送信しない
        last_sent_hour = _load_last_sent_hour()
        current_hour_key = (now.year, now.month, now.day, now.hour)
        if last_sent_hour == current_hour_key:
            return
        
        channel = bot.get_channel(channel_id)
        if channel:
            # 24時間制で表示
            msg = f"{now.hour}時をお知らせします"
            try:
                await channel.send(msg)
                # Save state after successful send to prevent duplicate announcements
                _save_last_sent_hour(current_hour_key)
                logger.info(f"【{now.strftime('%Y/%m/%d %H:%M:%S')}】時報を送信しました: {msg}")
            except discord.DiscordException as e:
                logger.error(f"Discord API Error: {e}")
                # Don't update state on failure - allows retry on next iteration
