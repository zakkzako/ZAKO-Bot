import subprocess
import datetime
import jst
import logging

JST = jst.get_jst()
logger = logging.getLogger(__name__)

def perform_full_update():
    """引数なしの定義 - 安全に git の更新をチェックして pull を行う"""
    try:
        # fetch は短めのタイムアウトを指定
        subprocess.run(["git", "fetch"], check=True, capture_output=True, timeout=30)
        # upstream が設定されていれば behind/ahead を判定する（ロケールに依存しない）
        try:
            # @{u} (upstream) を使う方法。upstream が未設定の場合は CalledProcessError になる。
            status = subprocess.check_output(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], timeout=10).decode("utf-8").strip()
            behind_count = int(status.split()[0]) if status else 0
        except subprocess.CalledProcessError:
            # フォールバック: git status -sb を使って 'behind' を含むかで判定（ロケールの影響あり得るが fallback）
            status2 = subprocess.check_output(["git", "status", "-sb"], timeout=10).decode("utf-8")
            behind_count = 1 if "behind" in status2.lower() else 0

        if behind_count > 0:
            log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')
            logger.info(f"[{log_time}] [Updater] 更新を検知。git pull を実行します...")
            # pull の実行にもタイムアウト
            subprocess.run(["git", "pull"], check=True, timeout=60)
            logger.info(f"[{log_time}] [Updater] ダウンロード完了。/admin_reload で反映してください。")
            return True
    except subprocess.TimeoutExpired as e:
        logger.error(f"[Updater] サブプロセスがタイムアウトしました: {e}")
    except subprocess.CalledProcessError as e:
        logger.error(f"[Updater] サブプロセスエラー: {e}")
    except Exception as e:
        logger.error(f"[Updater] エラー: {e}")
    return False
