import streamlit as st
from datetime import date
from db import get_all_casts, add_payment, get_confirmed_payments, get_pending_payments_for_cast, delete_payment

st.set_page_config(layout="centered", initial_sidebar_state="collapsed")

# サイドバーのナビゲーションを完全に非表示
st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.title("支払い入力")

# cast_idがURLになければエラー
params = st.query_params
if "cast_id" not in params:
    st.error("URLが正しくありません。お店からもらったURLを使ってください。")
    st.stop()

# cast_idに一致するキャストを取得
try:
    cast_id = int(params["cast_id"])
except ValueError:
    st.error("URLが正しくありません。")
    st.stop()

casts = get_all_casts()
cast = next((c for c in casts if c["id"] == cast_id), None)

if cast is None:
    st.error("キャスト情報が見つかりません。お店に確認してください。")
    st.stop()

st.subheader(f"👤 {cast['名前']} さんの支払いページ")
st.caption("支払いを申告してください。店側が確認後に残高に反映されます。")

st.divider()

# ── 支払い入力フォーム ────────────────────────────────
with st.form("payment_form"):
    支払い日 = st.date_input("支払い日", value=date.today())
    金額 = st.number_input("金額（円）", min_value=1, step=1000)
    メモ = st.text_input("メモ（任意）")
    submitted = st.form_submit_button("申告する", use_container_width=True)

if submitted:
    add_payment(cast_id, 支払い日, int(金額), メモ)
    st.success("申告しました。店側の確認をお待ちください。")
    st.rerun()

st.divider()

# ── 未確認（確認待ち）一覧 ────────────────────────────
st.subheader("確認待ちの申告")
pending = get_pending_payments_for_cast(cast_id)

if not pending:
    st.info("確認待ちの申告はありません。")
else:
    for p in pending:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{p['支払い日']}**　{p['金額']:,}円　{p['メモ'] or ''}")
        if col2.button("取消", key=f"cancel_{p['id']}"):
            delete_payment(p["id"])
            st.success("取り消しました。")
            st.rerun()

st.divider()

# ── 確認済み支払い履歴 ────────────────────────────────
st.subheader("確認済みの支払い履歴")
records = get_confirmed_payments(cast_id)

if not records:
    st.info("確認済みの支払いはまだありません。")
else:
    合計 = 0
    for r in records:
        st.write(f"**{r['支払い日']}**　{r['金額']:,}円　{r['メモ'] or ''}")
        合計 += r["金額"]
    st.divider()
    st.metric("確認済み合計", f"¥{合計:,}")
