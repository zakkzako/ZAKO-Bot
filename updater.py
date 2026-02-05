import asyncio
import datetime
import logging
import jst

JST = jst.get_jst()
logger = logging.getLogger(__name__)

async def perform_full_update():
    """非ブロッキングで git fetch/status/pull を実行し、更新検知時に pull する"""
    try:
        # git fetch
        fetch_proc = await asyncio.create_subprocess_exec(
            "git", "fetch",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await fetch_proc.communicate()

        # git status -uno
        status_proc = await asyncio.create_subprocess_exec(
            "git", "status", "-uno",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        status_out, status_err = await status_proc.communicate()
        status = status_out.decode("utf-8", errors="ignore")

        if "Your branch is behind" in status:
            log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
            logger.info(f"[{log_time}] [Updater] 更新を検知。git pull を実行します...")

            pull_proc = await asyncio.create_subprocess_exec(
                "git", "pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            pull_out, pull_err = await pull_proc.communicate()

            if pull_proc.returncode != 0:
                stderr_text = pull_err.decode("utf-8", errors="ignore")
                logger.error(f"[{log_time}] [Updater] git pull failed: {stderr_text}")
                return False

            logger.info(f"[{log_time}] [Updater] ダウンロード完了。/admin_reload で反映してください。")
            return True
    except Exception:
        logger.exception("[Updater] エラーが発生しました")
    return False
