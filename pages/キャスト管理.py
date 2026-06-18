import streamlit as st
from auth import require_auth, show_change_password
from db import get_all_casts, add_cast, update_cast

require_auth()
st.title("キャスト管理")

try:
    BASE_URL = st.secrets["base_url"]
except Exception:
    BASE_URL = "http://localhost:8501"

KINDS = ["日額", "月額"]

# ── 新規登録 ──────────────────────────────────────────
with st.expander("新規キャストを登録", icon="➕"):
    with st.form("add_cast_form"):
        名前 = st.text_input("名前")
        種別 = st.radio("滞在種別", KINDS, horizontal=True)
        単価 = st.number_input("一泊単価（円）※月額の場合は0でOK", min_value=0, step=500)
        メモ = st.text_input("メモ（任意）")
        submitted = st.form_submit_button("登録")

    if submitted:
        if not 名前:
            st.error("名前を入力してください。")
        else:
            add_cast(名前, int(単価), 種別, メモ)
            st.success(f"「{名前}」を登録しました。")
            st.rerun()

st.divider()

# ── キャスト一覧 ──────────────────────────────────────
casts = get_all_casts()

if not casts:
    st.info("キャストが登録されていません。")
else:
    st.subheader(f"登録キャスト一覧（{len(casts)}名）")

    for cast in casts:
        種別ラベル = "📅 月額" if cast["滞在種別"] == "月額" else "🌙 日額"
        with st.expander(f"{cast['名前']}　{種別ラベル}"):
            # 専用URL
            url = f"{BASE_URL}/%E6%94%AF%E6%89%95%E3%81%84%E5%85%A5%E5%8A%9B?cast_id={cast['id']}"
            st.text_input("支払い入力URL（コピーしてキャストに渡す）", value=url, key=f"url_{cast['id']}")

            with st.form(f"edit_cast_{cast['id']}"):
                新名前 = st.text_input("名前", value=cast["名前"])
                新種別 = st.radio("滞在種別", KINDS, index=KINDS.index(cast["滞在種別"]), horizontal=True)
                新単価 = st.number_input("一泊単価（円）", min_value=0, step=500, value=cast["一泊単価"])
                新メモ = st.text_input("メモ", value=cast["メモ"] or "")
                save = st.form_submit_button("保存")

            if save:
                update_cast(cast["id"], 新名前, int(新単価), 新種別, 新メモ)
                st.success("更新しました。")
                st.rerun()

st.divider()
show_change_password()
