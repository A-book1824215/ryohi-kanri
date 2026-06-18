import streamlit as st
from auth import require_auth
from db import get_all_rooms, add_room, update_room

require_auth()
st.title("部屋管理")

# ── 新規登録 ──────────────────────────────────────────
with st.expander("新規部屋を登録", icon="➕"):
    with st.form("add_room_form"):
        建物名 = st.text_input("建物名（例：Aビル、第2寮）")
        部屋番号 = st.text_input("部屋番号（例：101号室）")
        メモ = st.text_input("メモ（任意）")
        submitted = st.form_submit_button("登録")

    if submitted:
        if not 建物名 or not 部屋番号:
            st.error("建物名と部屋番号を入力してください。")
        else:
            add_room(建物名, 部屋番号, メモ)
            st.success(f"「{建物名}ー{部屋番号}」を登録しました。")
            st.rerun()

st.divider()

# ── 部屋一覧 ──────────────────────────────────────────
rooms = get_all_rooms()

if not rooms:
    st.info("部屋が登録されていません。")
else:
    st.subheader(f"登録部屋一覧（{len(rooms)}室）")

    for room in rooms:
        label = f"{room['建物名']}ー{room['部屋番号']}"
        with st.expander(label):
            with st.form(f"edit_room_{room['id']}"):
                新建物名 = st.text_input("建物名", value=room["建物名"])
                新部屋番号 = st.text_input("部屋番号", value=room["部屋番号"])
                新メモ = st.text_input("メモ", value=room["メモ"] or "")
                save = st.form_submit_button("保存")

            if save:
                update_room(room["id"], 新建物名, 新部屋番号, 新メモ)
                st.success("更新しました。")
                st.rerun()
