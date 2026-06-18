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
| キャスト管理 | キャストの登録・編集・支払いURL発行 |
| 部屋管理 | 建物・部屋の登録・編集 |
| 宿泊記録 | チェックイン・アウトの管理 |
| 月額管理 | 月額キャストの請求額を月ごとに管理 |
| 支払い確認 | 未確認支払いの承認・修正 |
| 支払い入力 | キャストが支払いを自己申告（認証不要） |
| 残高確認 | キャストごとの請求額・支払い・残高 |
| 台帳出力 | 全キャストの宿泊費・支払いをCSVでエクスポート |
""")
