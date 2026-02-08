import subprocess
import json
import os
import logging
import re
import jst

logger = logging.getLogger(__name__)

async def update_device_status(bot):
    BATTERY_CH_ID = int(os.getenv('BATTERY_CH_ID', 0))
    CPU_CH_ID     = int(os.getenv('CPU_CH_ID', 0))
    RAM_CH_ID     = int(os.getenv('RAM_CH_ID', 0))

    # カッコ付きの時刻文字列を作成
    now = jst.now()
    time_suffix = f"（{now.strftime('%H時%M分時点')}）"

    try:
        # 1. 電池情報の更新
        try:
            res = subprocess.check_output(["termux-battery-status"], timeout=5).decode("utf-8")
            data = json.loads(res)
            persentage = data.get("percentage", 0)
            statusmsg = "【不明】"
            battery_status = data.get("status", "").lower()
            if battery_status == "charging":
                statusmsg = "【充電中】"
            elif battery_status == "discharging":
                statusmsg = "【放電中】"
            elif battery_status == "full":
                statusmsg = "【満充電】"
            elif battery_status == "not-charging":
                statusmsg = "【充電停止中】"

            msg = f"bat-{statusmsg}{persentage}"
            full_msg = f"{msg}{time_suffix}"
            ch = bot.get_channel(BATTERY_CH_ID) or await bot.fetch_channel(BATTERY_CH_ID)
            if ch and ch.name != full_msg: await ch.edit(name=full_msg)
        except Exception as e:
            logger.error(f"Battery Error: {e}")

        # 2. CPU使用率の更新
        try:
            cpu_res = subprocess.check_output("top -n 1 -b", shell=True).decode("utf-8")
            # "0%user" のような形式から数字を抽出
            user_match = re.search(r'(\d+)%user', cpu_res)
            sys_match = re.search(r'(\d+)%sys', cpu_res)

            if user_match and sys_match:
                # UserとSystemの合計を計算
                usage = int(user_match.group(1)) + int(sys_match.group(1))
                cpu_text = f"{usage}/100"
            else:
                cpu_text = "取得中"

            full_msg = f"cpu-{cpu_text}{time_suffix}"
            ch = bot.get_channel(CPU_CH_ID) or await bot.fetch_channel(CPU_CH_ID)
            if ch and ch.name != full_msg: await ch.edit(name=full_msg)
        except Exception as e:
            logger.error(f"CPU Error: {e}")

        # 3. RAM残り容量の更新
        try:
            ram_res = subprocess.check_output("free -m | grep Mem", shell=True).decode("utf-8")
            parts = ram_res.split()
            total_mb = parts[1]
            available_mb = parts[6]

            full_msg = f"ram-{available_mb}mb/{total_mb}mb{time_suffix}"
            ch = bot.get_channel(RAM_CH_ID) or await bot.fetch_channel(RAM_CH_ID)
            if ch and ch.name != full_msg: await ch.edit(name=full_msg)
        except Exception as e:
            logger.error(f"RAM Error: {e}")

    except Exception as e:
        logger.error(f"Device Monitor Global Error: {e}")
