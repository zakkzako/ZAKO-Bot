import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_FILE = "bot_data.db"

async def init_db():
    """データベースとテーブルの初期化を行います"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. ユーザーの経済データ (users.jsonの代わり)
            # user_id はJSONでは文字列でしたが、SQLではINTEGER（整数）として扱います
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0.0,
                    daily_exchange_total REAL DEFAULT 0.0,
                    last_exchange_date TEXT DEFAULT ''
                )
            """)

            # 2. ブラックジャックの戦績データ (blackjack_data.jsonの代わり)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blackjack_stats (
                    user_id INTEGER PRIMARY KEY,
                    win INTEGER DEFAULT 0,
                    loss INTEGER DEFAULT 0,
                    draw INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0.0
                )
            """)

            # 3. リマインダー（通知キュー）データ (reminders.jsonの代わり)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    target_time TEXT NOT NULL,
                    cooldown_min INTEGER,
                    notification_type TEXT NOT NULL
                )
            """)

            # 4. システム設定や全体データ (economy_data.json, config.jsonの代わり)
            # 柔軟に保存できるよう Key-Value 型にしています
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 初期データが必要なもの（総発行ECの初期値など）のセットアップ
            await db.execute("""
                INSERT OR IGNORE INTO system_config (key, value)
                VALUES ('total_supply', '10000000.0')
            """)

            await db.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

# --- 共通で使える便利なDB操作関数（今後の実装を楽にするため） ---

async def execute_query(query: str, parameters: tuple = ()):
    """データの更新・挿入・削除を行う汎用関数"""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(query, parameters)
        await db.commit()

async def fetch_one(query: str, parameters: tuple = ()):
    """データを1件だけ取得する汎用関数"""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row # カラム名でアクセスできるようにする
        async with db.execute(query, parameters) as cursor:
            return await cursor.fetchone()

async def fetch_all(query: str, parameters: tuple = ()):
    """データを複数件取得する汎用関数"""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, parameters) as cursor:
            return await cursor.fetchall()
