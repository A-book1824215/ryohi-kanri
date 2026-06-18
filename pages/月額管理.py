import streamlit as st
from datetime import date
from auth import require_auth
from db import get_all_casts, get_monthly_records, upsert_monthly_record

require_auth()
st.title("月額管理")
st.caption("長期（月額）キャストの月ごとの請求額を管理します。")

casts = get_all_casts()
月額キャスト = [c for c in casts if c["滞在種別"] == "月額"]

if not 月額キャスト:
    st.info("月額キャストが登録されていません。キャスト管理で滞在種別を「月額」に設定してください。")
    st.stop()

# キャスト選択
cast_options = {c["id"]: c["名前"] for c in 月額キャスト}
selected_id = st.selectbox("キャストを選択", options=list(cast_options.keys()), format_func=lambda x: cast_options[x])

st.divider()

# ── 月額登録・更新 ────────────────────────────────────
st.subheader("月額を登録・更新")

今月 = date.today().strftime("%Y-%m")
with st.form("monthly_form"):
    年月 = st.text_input("年月（YYYY-MM）", value=今月, placeholder="例: 2026-06")
    条件クリア = st.checkbox("条件クリア（出勤日数の条件を満たした）")
    月額 = st.number_input("月額（円）", min_value=0, step=1000)
    メモ = st.text_input("メモ（任意）")
    submitted = st.form_submit_button("保存")

if submitted:
    try:
        # 年月フォーマット簡易チェック
        if len(年月) != 7 or 年月[4] != "-":
            raise ValueError
        upsert_monthly_record(selected_id, 年月, 条件クリア, int(月額), メモ)
        st.success(f"「{cast_options[selected_id]}」{年月} の月額を保存しました。")
        st.rerun()
    except ValueError:
        st.error("年月は YYYY-MM 形式で入力してください（例: 2026-06）")

st.divider()

# ── 月額履歴 ──────────────────────────────────────────
st.subheader("月額履歴")
records = get_monthly_records(selected_id)

if not records:
    st.info("まだ記録がありません。")
else:
    合計 = 0
    for r in records:
        条件 = "✅ クリア" if r["条件クリア"] else "❌ 未クリア"
        st.write(f"**{r['年月']}**　{条件}　{r['月額']:,}円　{r['メモ'] or ''}")
        合計 += r["月額"]
    st.divider()
    st.metric("累計請求額", f"¥{合計:,}")
