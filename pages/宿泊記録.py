import streamlit as st
from datetime import date
from auth import require_auth
from db import get_all_casts, get_all_rooms, get_active_stays, get_checked_out_stays, add_stay, checkout_stay, update_stay

require_auth()
st.title("宿泊記録")

casts = get_all_casts()
rooms = get_all_rooms()

if not casts:
    st.warning("先にキャストを登録してください。")
    st.stop()
if not rooms:
    st.warning("先に部屋を登録してください。")
    st.stop()

cast_options = {c["id"]: c["名前"] for c in casts}
room_options = {r["id"]: f"{r['建物名']}ー{r['部屋番号']}" for r in rooms}

# ── チェックイン登録 ──────────────────────────────────
with st.expander("チェックイン登録", icon="🛎️"):
    with st.form("checkin_form"):
        cast_id = st.selectbox("キャスト", options=list(cast_options.keys()), format_func=lambda x: cast_options[x])
        room_id = st.selectbox("部屋", options=list(room_options.keys()), format_func=lambda x: room_options[x])
        checkin = st.date_input("チェックイン日", value=date.today())

        selected_cast = next(c for c in casts if c["id"] == cast_id)
        単価 = st.number_input("適用単価（円／泊）", min_value=0, step=500, value=selected_cast["一泊単価"])
        メモ = st.text_input("メモ（任意）")
        submitted = st.form_submit_button("チェックイン登録")

    if submitted:
        add_stay(cast_id, room_id, checkin, int(単価), メモ)
        st.success(f"「{cast_options[cast_id]}」のチェックインを登録しました。")
        st.rerun()

st.divider()

# ── 滞在中一覧 ────────────────────────────────────────
st.subheader("滞在中")
active = get_active_stays()

if not active:
    st.info("現在の滞在者はいません。")
else:
    for s in active:
        泊数 = (date.today() - date.fromisoformat(s["チェックイン日"])).days
        label = f"{s['名前']}　{room_options[s['部屋id']]}　{s['チェックイン日']} チェックイン（{泊数}泊目）"
        with st.expander(label):
            with st.form(f"checkout_{s['id']}"):
                checkout = st.date_input("チェックアウト日", value=date.today())
                新メモ = st.text_input("メモ", value=s["メモ"] or "")
                col1, col2 = st.columns(2)
                do_checkout = col1.form_submit_button("チェックアウト")
                do_update = col2.form_submit_button("メモだけ更新")

            if do_checkout:
                checkout_stay(s["id"], checkout, 新メモ)
                st.success("チェックアウトしました。")
                st.rerun()
            if do_update:
                update_stay(s["id"], None, 新メモ)
                st.success("更新しました。")
                st.rerun()

st.divider()

# ── チェックアウト済み一覧 ────────────────────────────
with st.expander("チェックアウト済み履歴"):
    past = get_checked_out_stays()
    if not past:
        st.info("履歴はありません。")
    else:
        for s in past:
            泊数 = (date.fromisoformat(s["チェックアウト日"]) - date.fromisoformat(s["チェックイン日"])).days
            合計 = 泊数 * s["適用単価"]
            st.write(f"**{s['名前']}**　{room_options[s['部屋id']]}　{s['チェックイン日']}〜{s['チェックアウト日']}　{泊数}泊　{合計:,}円")
