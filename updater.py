import asyncio
import datetime
import logging
import os
import io
import tempfile
import zipfile
import shutil
import aiohttp
import jst

JST = jst.get_jst()
logger = logging.getLogger(__name__)

# ==========================================
# 【設定項目】
# ==========================================
GITHUB_OWNER = "zakkzako"
GITHUB_REPO = "ZAKO-Bot"
GITHUB_BRANCH = "main" # もしデフォルトブランチがmasterの場合は "master" に変更してください

# パブリックリポジトリなのでトークンは不要です
GITHUB_TOKEN = None
# トークン設定した方がレートリミット緩くなるから設定してちょ by Yamatomato

# 上書き・削除されたくないファイルやディレクトリのリスト
# （環境変数ファイルや、動的に書き換わるDBファイルなどは必ず入れてください）
EXCLUDE_LIST = [
    ".git",
    "__pycache__",
    "venv",
    ".env",
    ".local_version",
    "bot_data.db",
    ".gitignore",
    "requirements.txt"
    # もしjsonファイル等でユーザーデータを保存している場合は、ここに追記してください
]
# ==========================================

async def perform_full_update():
    """GitHubからZIPをダウンロードし、差分ファイルのみ更新する（擬似pull）"""
    log_time = datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')

    # 1. 更新の必要があるかチェック
    versions = await get_current_version()
    if versions["remote"] == "unknown":
        logger.warning(f"[{log_time}] [Updater] リモートバージョンの取得に失敗しました。更新をスキップします。")
        return False
    if versions["local"] == versions["remote"]:
        # 既に最新の場合は何もしない
        return False

    logger.info(f"[{log_time}] [Updater] 更新を検知。擬似pullを開始します...")

    zip_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        async with aiohttp.ClientSession() as session:
            # 2. ZIPファイルのダウンロード
            async with session.get(zip_url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"[{log_time}] [Updater] ZIPのダウンロードに失敗しました: HTTP {resp.status}")
                    return False
                zip_data = await resp.read()

        # 3. メモリ上でZIPを展開し、一時ディレクトリに解凍
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            with tempfile.TemporaryDirectory() as temp_dir:
                z.extractall(temp_dir)

                # GitHubのZIPはルートに「リポジトリ名-ブランチ名」のフォルダができるため、その中身を起点とする
                extracted_root = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                updated_files_count = 0

                # 4. ファイルの差分チェックと上書きコピー
                for root, dirs, files in os.walk(extracted_root):
                    # 除外対象のディレクトリを探索から外す
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_LIST]

                    for file in files:
                        if file in EXCLUDE_LIST:
                            continue

                        ext_file_path = os.path.join(root, file)
                        # カレントディレクトリからの相対パスを計算
                        rel_path = os.path.relpath(ext_file_path, extracted_root)
                        local_file_path = os.path.abspath(rel_path)

                        # ローカルにディレクトリが存在しない場合は作成
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                        needs_update = False
                        if not os.path.exists(local_file_path):
                            # ローカルにファイルがない場合は新規作成
                            needs_update = True
                        else:
                            # 中身をバイナリで比較して差分があれば更新
                            with open(ext_file_path, "rb") as ef, open(local_file_path, "rb") as lf:
                                if ef.read() != lf.read():
                                    needs_update = True

                        if needs_update:
                            shutil.copy2(ext_file_path, local_file_path)
                            logger.info(f"[Updater] Updated: {rel_path}")
                            updated_files_count += 1

        # 5. 最新のコミットハッシュを保存（次回以降の比較用）
        if versions["remote"] != "unknown":
            with open(".local_version", "w", encoding="utf-8") as f:
                f.write(versions["remote"])

        logger.info(f"[{log_time}] [Updater] ダウンロード完了。{updated_files_count}件のファイルを更新しました。/admin_reload で反映してください。")
        return True

    except Exception:
        logger.exception("[Updater] 擬似pull中にエラーが発生しました")
        return False

async def get_current_version():
    """GitHub APIを使用してローカルとリモートのコミットハッシュを取得して辞書で返す"""
    versions = {"local": "unknown", "remote": "unknown"}

    # ローカルのバージョンは Git の代わりにファイル (.local_version) から読み取る
    if os.path.exists(".local_version"):
        with open(".local_version", "r", encoding="utf-8") as f:
            versions["local"] = f.read().strip()

    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    versions["remote"] = data["sha"]
                else:
                    logger.error(f"[Updater] APIリクエスト失敗: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"[Updater] API経由でのバージョン取得エラー: {e}")

    return versions
