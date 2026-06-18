import streamlit as st
from auth import require_auth
from db import (
    get_pending_payments, confirm_payment, delete_payment,
    revert_payment, get_confirmed_payments, get_all_casts,
)

require_auth()
st.title("支払い確認")

tab1, tab2 = st.tabs(["未確認の申告", "確認済みの修正"])

# ── Tab1: 未確認の承認・削除 ──────────────────────────
with tab1:
    st.caption("キャストが申告した支払いを確認・承認します。")
    pending = get_pending_payments()

    if not pending:
        st.success("未確認の申告はありません。")
    else:
        st.subheader(f"未確認（{len(pending)}件）")
        for p in pending:
            with st.expander(f"{p['名前']}　{p['支払い日']}　{p['金額']:,}円"):
                st.write(f"メモ: {p['メモ'] or 'なし'}")
                st.write(f"申告日時: {p['登録日時']}")
                col1, col2 = st.columns(2)
                if col1.button("✅ 確認済みにする", key=f"confirm_{p['id']}"):
                    confirm_payment(p["id"])
                    st.success("確認済みにしました。")
                    st.rerun()
                if col2.button("🗑️ 削除（誤申告）", key=f"delete_{p['id']}"):
                    delete_payment(p["id"])
                    st.warning("削除しました。")
                    st.rerun()

# ── Tab2: 確認済みの取り消し ──────────────────────────
with tab2:
    st.caption("承認済みの支払いを未確認に戻すか削除できます。")

    casts = get_all_casts()
    if not casts:
        st.info("キャストが登録されていません。")
        st.stop()

    cast_options = {c["id"]: c["名前"] for c in casts}
    selected_id = st.selectbox(
        "キャストを選択",
        options=list(cast_options.keys()),
        format_func=lambda x: cast_options[x],
    )

    confirmed = get_confirmed_payments(selected_id)

    if not confirmed:
        st.info("確認済みの支払いはありません。")
    else:
        for p in confirmed:
            with st.expander(f"{p['支払い日']}　{p['金額']:,}円　{p['メモ'] or ''}"):
                col1, col2 = st.columns(2)
                if col1.button("↩️ 未確認に戻す", key=f"revert_{p['id']}"):
                    revert_payment(p["id"])
                    st.success("未確認に戻しました。")
                    st.rerun()
                if col2.button("🗑️ 削除", key=f"del_confirmed_{p['id']}"):
                    delete_payment(p["id"])
                    st.warning("削除しました。")
                    st.rerun()
