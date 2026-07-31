import os
import streamlit as st
from auth import require_auth
from db import init_db

init_db()

st.set_page_config(page_title="寮費管理システム", layout="wide")
require_auth()
st.title("寮費管理システム")

if os.getenv("DEMO_MODE", "").lower() == "true":
    st.warning("これはデモ環境です。入力したデータはサーバー再起動時にリセットされます。")
st.markdown("""
| ページ | 用途 |
|---|---|
| スタッフ管理 | スタッフの登録・編集・支払いURL発行 |
| 部屋管理 | 建物・部屋の登録・編集 |
| 宿泊記録 | チェックイン・アウトの管理 |
| 月額管理 | 月額スタッフの請求額を月ごとに管理 |
| 支払い確認 | 未確認支払いの承認・修正 |
| 支払い入力 | スタッフが支払いを自己申告（認証不要） |
| 残高確認 | スタッフごとの請求額・支払い・残高 |
| 台帳出力 | 全スタッフの宿泊費・支払いをCSVでエクスポート |
""")
