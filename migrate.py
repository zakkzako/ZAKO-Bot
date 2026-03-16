import asyncio
import json
import os
import aiosqlite
import database

async def migrate_data():
    # テーブルが存在しない場合は作成
    await database.init_db()
    
    async with aiosqlite.connect(database.DB_FILE) as db:
        print("--- 移行開始 ---")

        # 1. users.json の移行
        if os.path.exists("users.json"):
            with open("users.json", "r", encoding="utf-8") as f:
                try:
                    users_data = json.load(f)
                    for uid_str, data in users_data.items():
                        uid = int(uid_str)
                        balance = data.get("balance", 0.0)
                        daily_exchange = data.get("daily_exchange_total", 0.0)
                        last_exchange = data.get("last_exchange_date", "")
                        last_work = data.get("last_work", "")
                        
                        await db.execute("""
                            INSERT OR REPLACE INTO users (user_id, balance, daily_exchange_total, last_exchange_date, last_work)
                            VALUES (?, ?, ?, ?, ?)
                        """, (uid, balance, daily_exchange, last_exchange, last_work))
                    print(f"users.json から {len(users_data)} 件のデータを移行しました。")
                except Exception as e:
                    print(f"users.json の移行エラー: {e}")

        # 2. blackjack_data.json の移行
        if os.path.exists("blackjack_data.json"):
            with open("blackjack_data.json", "r", encoding="utf-8") as f:
                try:
                    bj_data = json.load(f)
                    for uid_str, data in bj_data.items():
                        uid = int(uid_str)
                        await db.execute("""
                            INSERT OR REPLACE INTO blackjack_stats (user_id, win, loss, draw, total_profit)
                            VALUES (?, ?, ?, ?, ?)
                        """, (uid, data.get("win", 0), data.get("loss", 0), data.get("draw", 0), data.get("total_profit", 0.0)))
                    print(f"blackjack_data.json から {len(bj_data)} 件のデータを移行しました。")
                except Exception as e:
                    print(f"blackjack_data.json の移行エラー: {e}")

        # 3. notification_settings.json の移行
        if os.path.exists("notification_settings.json"):
            with open("notification_settings.json", "r", encoding="utf-8") as f:
                try:
                    ns_data = json.load(f)
                    for uid_str, data in ns_data.items():
                        uid = int(uid_str)
                        await db.execute("""
                            INSERT OR REPLACE INTO notification_settings (user_id, work, external_work, unemployment_insurance, steal)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            uid, 
                            int(data.get("work", True)), 
                            int(data.get("external_work", True)), 
                            int(data.get("unemployment_insurance", True)), 
                            int(data.get("steal", True))
                        ))
                    print(f"notification_settings.json から {len(ns_data)} 件のデータを移行しました。")
                except Exception as e:
                    print(f"notification_settings.json の移行エラー: {e}")

        # 4. reminders.json の移行
        if os.path.exists("reminders.json"):
            with open("reminders.json", "r", encoding="utf-8") as f:
                try:
                    reminders = json.load(f)
                    for r in reminders:
                        await db.execute("""
                            INSERT INTO reminders (user_id, channel_id, target_time, cooldown_min, notification_type)
                            VALUES (?, ?, ?, ?, ?)
                        """, (r.get("user_id"), r.get("channel_id"), r.get("target_time"), r.get("cooldown_min", 0), r.get("notification_type")))
                    print(f"reminders.json から {len(reminders)} 件のデータを移行しました。")
                except Exception as e:
                    print(f"reminders.json の移行エラー: {e}")

        # 5. economy_data.json と config.json の移行 (system_config)
        sys_configs = {}
        if os.path.exists("economy_data.json"):
            with open("economy_data.json", "r", encoding="utf-8") as f:
                try:
                    econ = json.load(f)
                    if "total_supply" in econ:
                        sys_configs["total_supply"] = str(econ["total_supply"])
                except Exception as e:
                    print(f"economy_data.json の移行エラー: {e}")
        
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                try:
                    cfg = json.load(f)
                    for k, v in cfg.items():
                        sys_configs[k] = str(v)
                except Exception as e:
                    print(f"config.json の移行エラー: {e}")
        
        for k, v in sys_configs.items():
            await db.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (k, v))
        print(f"設定ファイルから {len(sys_configs)} 件のシステムデータを移行しました。")

        await db.commit()
        print("--- 移行完了 ---")

if __name__ == "__main__":
    asyncio.run(migrate_data())
