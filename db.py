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
