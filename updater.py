import subprocess
import datetime
import jst
import logging

JST = jst.get_jst()
logger = logging.getLogger(__name__)

def perform_full_update():
    """引数なしの定義"""
    try:
        subprocess.run(["git", "fetch"], check=True, capture_output=True)
        status = subprocess.check_output(["git", "status", "-uno"]).decode("utf-8")

        if "Your branch is behind" in status:
            log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
            logger.info(f"[{log_time}] [Updater] 更新を検知。git pullを実行します...")
            subprocess.run(["git", "pull"], check=True)
            logger.info(f"[{log_time}] [Updater] ダウンロード完了。/admin_reload で反映してください。")
            return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[Updater] サブプロセスエラー: {e}")
    except Exception as e:
        logger.error(f"[Updater] エラー: {e}")
    return False
