import hashlib
import hmac
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "ryohi.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS casts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                名前      TEXT    NOT NULL,
                一泊単価  INTEGER NOT NULL DEFAULT 0,
                滞在種別  TEXT    NOT NULL DEFAULT '日額',
                メモ      TEXT,
                登録日時  DATETIME DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                建物名    TEXT    NOT NULL,
                部屋番号  TEXT    NOT NULL,
                メモ      TEXT
            );

            CREATE TABLE IF NOT EXISTS stays (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                cast_id          INTEGER NOT NULL REFERENCES casts(id),
                部屋id           INTEGER NOT NULL REFERENCES rooms(id),
                チェックイン日   DATE    NOT NULL,
                チェックアウト日  DATE,
                適用単価         INTEGER NOT NULL DEFAULT 0,
                ステータス       TEXT    NOT NULL DEFAULT '滞在中',
                メモ             TEXT,
                登録日時         DATETIME DEFAULT (datetime('now', 'localtime')),
                更新日時         DATETIME DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS payments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                cast_id    INTEGER NOT NULL REFERENCES casts(id),
                支払い日   DATE    NOT NULL,
                金額       INTEGER NOT NULL,
                メモ       TEXT,
                ステータス TEXT    NOT NULL DEFAULT '未確認',
                登録日時   DATETIME DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS auth (
                id    INTEGER PRIMARY KEY CHECK (id = 1),
                salt  TEXT NOT NULL,
                hash  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS 月額記録 (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cast_id     INTEGER NOT NULL REFERENCES casts(id),
                年月        TEXT    NOT NULL,
                条件クリア  INTEGER NOT NULL DEFAULT 0,
                月額        INTEGER NOT NULL DEFAULT 0,
                メモ        TEXT,
                登録日時    DATETIME DEFAULT (datetime('now', 'localtime')),
                更新日時    DATETIME DEFAULT (datetime('now', 'localtime')),
                UNIQUE(cast_id, 年月)
            );
        """)
    _migrate()
    if os.getenv("DEMO_MODE", "").lower() == "true":
        _seed_demo()


def _migrate():
    """既存DBに不足カラムを安全に追加する"""
    with get_conn() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(casts)")}
        if "滞在種別" not in existing:
            conn.execute("ALTER TABLE casts ADD COLUMN 滞在種別 TEXT NOT NULL DEFAULT '日額'")


# ── キャスト ──────────────────────────────────────────

def get_all_casts():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM casts ORDER BY 登録日時 DESC").fetchall()


def add_cast(名前, 単価, 種別, メモ=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO casts (名前, 一泊単価, 滞在種別, メモ) VALUES (?, ?, ?, ?)",
            (名前, 単価, 種別, メモ),
        )


def update_cast(cast_id, 名前, 単価, 種別, メモ=""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE casts SET 名前=?, 一泊単価=?, 滞在種別=?, メモ=? WHERE id=?",
            (名前, 単価, 種別, メモ, cast_id),
        )


# ── 部屋 ──────────────────────────────────────────────

def get_all_rooms():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM rooms ORDER BY 建物名, 部屋番号").fetchall()


def add_room(建物名, 部屋番号, メモ=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO rooms (建物名, 部屋番号, メモ) VALUES (?, ?, ?)",
            (建物名, 部屋番号, メモ),
        )


def update_room(room_id, 建物名, 部屋番号, メモ=""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE rooms SET 建物名=?, 部屋番号=?, メモ=? WHERE id=?",
            (建物名, 部屋番号, メモ, room_id),
        )


# ── 宿泊記録 ──────────────────────────────────────────

def get_active_stays():
    with get_conn() as conn:
        return conn.execute("""
            SELECT s.*, c.名前, c.一泊単価, c.滞在種別
            FROM stays s
            JOIN casts c ON s.cast_id = c.id
            WHERE s.ステータス = '滞在中'
            ORDER BY s.チェックイン日 DESC
        """).fetchall()


def get_checked_out_stays():
    with get_conn() as conn:
        return conn.execute("""
            SELECT s.*, c.名前, c.滞在種別
            FROM stays s
            JOIN casts c ON s.cast_id = c.id
            WHERE s.ステータス = 'チェックアウト済'
            ORDER BY s.チェックアウト日 DESC
        """).fetchall()


def add_stay(cast_id, room_id, checkin, 単価, メモ=""):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO stays (cast_id, 部屋id, チェックイン日, 適用単価, メモ)
               VALUES (?, ?, ?, ?, ?)""",
            (cast_id, room_id, checkin, 単価, メモ),
        )


def checkout_stay(stay_id, checkout, メモ=""):
    with get_conn() as conn:
        conn.execute(
            """UPDATE stays
               SET チェックアウト日=?, ステータス='チェックアウト済', メモ=?,
                   更新日時=datetime('now','localtime')
               WHERE id=?""",
            (checkout, メモ, stay_id),
        )


def update_stay(stay_id, checkout, メモ):
    with get_conn() as conn:
        if checkout:
            conn.execute(
                """UPDATE stays SET チェックアウト日=?, メモ=?,
                   更新日時=datetime('now','localtime') WHERE id=?""",
                (checkout, メモ, stay_id),
            )
        else:
            conn.execute(
                """UPDATE stays SET メモ=?,
                   更新日時=datetime('now','localtime') WHERE id=?""",
                (メモ, stay_id),
            )


# ── 月額記録 ──────────────────────────────────────────

def get_monthly_records(cast_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM 月額記録 WHERE cast_id=? ORDER BY 年月 DESC",
            (cast_id,),
        ).fetchall()


# ── 支払い記録 ──────────────────────────────────────────

def add_payment(cast_id, 支払い日, 金額, メモ=""):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO payments (cast_id, 支払い日, 金額, メモ, ステータス)
               VALUES (?, ?, ?, ?, '未確認')""",
            (cast_id, 支払い日, 金額, メモ),
        )


def get_pending_payments():
    with get_conn() as conn:
        return conn.execute("""
            SELECT p.*, c.名前
            FROM payments p
            JOIN casts c ON p.cast_id = c.id
            WHERE p.ステータス = '未確認'
            ORDER BY p.支払い日 DESC
        """).fetchall()


def get_confirmed_payments(cast_id):
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM payments
               WHERE cast_id=? AND ステータス='確認済み'
               ORDER BY 支払い日 DESC""",
            (cast_id,),
        ).fetchall()


def get_pending_payments_for_cast(cast_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM payments WHERE cast_id=? AND ステータス='未確認' ORDER BY 支払い日 DESC",
            (cast_id,),
        ).fetchall()


def confirm_payment(payment_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE payments SET ステータス='確認済み' WHERE id=?",
            (payment_id,),
        )


def revert_payment(payment_id):
    """確認済みを未確認に戻す"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE payments SET ステータス='未確認' WHERE id=?",
            (payment_id,),
        )


def delete_payment(payment_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM payments WHERE id=?", (payment_id,))


# ── 残高計算 ──────────────────────────────────────────

def get_balance_summary():
    """全キャストの請求額・支払い額・残高を返す"""
    with get_conn() as conn:
        casts = conn.execute("SELECT * FROM casts ORDER BY 登録日時 DESC").fetchall()
        result = []
        for c in casts:
            cid = c["id"]

            if c["滞在種別"] == "日額":
                row = conn.execute("""
                    SELECT COALESCE(SUM(
                        (julianday(COALESCE(チェックアウト日, date('now','localtime')))
                         - julianday(チェックイン日)) * 適用単価
                    ), 0) AS 請求額
                    FROM stays WHERE cast_id=?
                """, (cid,)).fetchone()
                請求額 = int(row["請求額"])
            else:
                row = conn.execute(
                    "SELECT COALESCE(SUM(月額), 0) AS 請求額 FROM 月額記録 WHERE cast_id=?",
                    (cid,),
                ).fetchone()
                請求額 = int(row["請求額"])

            pay = conn.execute(
                "SELECT COALESCE(SUM(金額), 0) AS 合計 FROM payments WHERE cast_id=? AND ステータス='確認済み'",
                (cid,),
            ).fetchone()
            支払い済み = int(pay["合計"])

            result.append({
                "id": cid,
                "名前": c["名前"],
                "滞在種別": c["滞在種別"],
                "請求額": 請求額,
                "支払い済み": 支払い済み,
                "残高": 請求額 - 支払い済み,
            })
        return result


# ── 月額記録 ──────────────────────────────────────────

def upsert_monthly_record(cast_id, 年月, 条件クリア, 月額, メモ=""):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO 月額記録 (cast_id, 年月, 条件クリア, 月額, メモ)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(cast_id, 年月)
               DO UPDATE SET 条件クリア=excluded.条件クリア,
                             月額=excluded.月額,
                             メモ=excluded.メモ,
                             更新日時=datetime('now','localtime')""",
            (cast_id, 年月, int(条件クリア), 月額, メモ),
        )


# ── 認証 ──────────────────────────────────────────────

_PBKDF2_ITERATIONS = 260_000  # OWASP 2024推奨値


def is_password_configured():
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM auth").fetchone()
        return row["cnt"] > 0


def set_password(plain: str):
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, _PBKDF2_ITERATIONS)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auth (id, salt, hash) VALUES (1, ?, ?)",
            (salt.hex(), key.hex()),
        )


def verify_password(plain: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT salt, hash FROM auth WHERE id=1").fetchone()
    if not row:
        return False
    salt = bytes.fromhex(row["salt"])
    key = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(key.hex(), row["hash"])


# ── 台帳出力 ──────────────────────────────────────────

def get_ledger_rows(start_date: str = None, end_date: str = None) -> list[dict]:
    """会計ソフト取り込み用: 宿泊費（日額・月額）＋確認済み支払いを日付順で返す"""
    with get_conn() as conn:
        date_filter_stays = ""
        date_filter_monthly = ""
        date_filter_payments = ""
        params_stays: list = []
        params_monthly: list = []
        params_payments: list = []

        if start_date:
            date_filter_stays    += " AND COALESCE(s.チェックアウト日, date('now','localtime')) >= ?"
            date_filter_monthly  += " AND m.年月 >= ?"
            date_filter_payments += " AND p.支払い日 >= ?"
            params_stays.append(start_date)
            params_monthly.append(start_date[:7])
            params_payments.append(start_date)
        if end_date:
            date_filter_stays    += " AND COALESCE(s.チェックアウト日, date('now','localtime')) <= ?"
            date_filter_monthly  += " AND m.年月 <= ?"
            date_filter_payments += " AND p.支払い日 <= ?"
            params_stays.append(end_date)
            params_monthly.append(end_date[:7])
            params_payments.append(end_date)

        # 日額キャストの宿泊費
        stays = conn.execute(f"""
            SELECT
                COALESCE(s.チェックアウト日, date('now','localtime')) AS 日付,
                c.名前   AS キャスト名,
                '宿泊費' AS 種別,
                r.建物名 || 'ー' || r.部屋番号
                    || '（' || s.チェックイン日 || '〜'
                    || COALESCE(s.チェックアウト日, '滞在中') || ' '
                    || CAST(ROUND(julianday(COALESCE(s.チェックアウト日, date('now','localtime')))
                                 - julianday(s.チェックイン日)) AS INTEGER)
                    || '泊 ' || s.適用単価 || '円/泊）'  AS 摘要,
                CAST(ROUND(
                    (julianday(COALESCE(s.チェックアウト日, date('now','localtime')))
                     - julianday(s.チェックイン日)) * s.適用単価
                ) AS INTEGER) AS 金額,
                CASE WHEN s.ステータス = '滞在中' THEN '暫定' ELSE '確定' END AS 備考
            FROM stays s
            JOIN casts c ON s.cast_id = c.id
            JOIN rooms r ON s.部屋id  = r.id
            WHERE c.滞在種別 = '日額'
            {date_filter_stays}
        """, params_stays).fetchall()

        # 月額キャストの宿泊費
        monthly = conn.execute(f"""
            SELECT
                m.年月 || '-01'  AS 日付,
                c.名前           AS キャスト名,
                '宿泊費（月額）' AS 種別,
                m.年月           AS 摘要,
                m.月額           AS 金額,
                CASE WHEN m.条件クリア THEN '条件クリア' ELSE '' END AS 備考
            FROM 月額記録 m
            JOIN casts c ON m.cast_id = c.id
            WHERE 1=1 {date_filter_monthly}
        """, params_monthly).fetchall()

        # 確認済み支払い
        payments = conn.execute(f"""
            SELECT
                p.支払い日   AS 日付,
                c.名前       AS キャスト名,
                '支払い'     AS 種別,
                COALESCE(p.メモ, '') AS 摘要,
                -p.金額      AS 金額,
                ''           AS 備考
            FROM payments p
            JOIN casts c ON p.cast_id = c.id
            WHERE p.ステータス = '確認済み' {date_filter_payments}
        """, params_payments).fetchall()

    all_rows = [dict(r) for r in stays] + [dict(r) for r in monthly] + [dict(r) for r in payments]
    all_rows.sort(key=lambda x: x["日付"])
    return all_rows


# ── デモデータ ────────────────────────────────────────

def _seed_demo():
    """DEMO_MODE=true のとき、DBが空なら初期ダミーデータを投入する"""
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM casts").fetchone()[0] > 0:
            return

        conn.executemany(
            "INSERT INTO casts (名前, 一泊単価, 滞在種別, メモ) VALUES (?, ?, ?, ?)",
            [
                ("さくら", 3000, "日額", ""),
                ("みく",   2500, "日額", ""),
                ("りな",      0, "月額", "長期滞在"),
            ],
        )
        conn.executemany(
            "INSERT INTO rooms (建物名, 部屋番号, メモ) VALUES (?, ?, ?)",
            [
                ("Aビル",      "101号室", ""),
                ("Aビル",      "102号室", ""),
                ("Bマンション", "201号室", ""),
            ],
        )
        conn.executemany(
            """INSERT INTO stays
               (cast_id, 部屋id, チェックイン日, チェックアウト日, 適用単価, ステータス)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (1, 1, "2026-06-10", None,         3000, "滞在中"),
                (2, 2, "2026-06-01", "2026-06-14", 2500, "チェックアウト済"),
            ],
        )
        conn.executemany(
            "INSERT INTO payments (cast_id, 支払い日, 金額, ステータス) VALUES (?, ?, ?, ?)",
            [
                (1, "2026-06-12", 10000, "確認済み"),
                (2, "2026-06-10", 20000, "確認済み"),
                (2, "2026-06-16", 10000, "未確認"),
            ],
        )
        conn.executemany(
            "INSERT INTO 月額記録 (cast_id, 年月, 条件クリア, 月額) VALUES (?, ?, ?, ?)",
            [
                (3, "2026-05", 1, 50000),
                (3, "2026-06", 0, 50000),
            ],
        )

    if not is_password_configured():
        set_password("demo1234")
