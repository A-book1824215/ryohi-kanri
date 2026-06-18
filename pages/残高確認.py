import streamlit as st
from auth import require_auth
from db import get_balance_summary

require_auth()
st.title("残高確認")
st.caption("確認済み支払いのみ反映されます。")

summary = get_balance_summary()

if not summary:
    st.info("キャストが登録されていません。")
    st.stop()

# 未払いのあるキャストを上に表示
summary.sort(key=lambda x: x["残高"], reverse=True)

未払いあり = [s for s in summary if s["残高"] > 0]
完済      = [s for s in summary if s["残高"] <= 0]

# ── 未払いあり ────────────────────────────────────────
if 未払いあり:
    st.subheader(f"⚠️ 未払いあり（{len(未払いあり)}名）")
    for s in 未払いあり:
        種別 = "月額" if s["滞在種別"] == "月額" else "日額"
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            col1.markdown(f"**{s['名前']}**　`{種別}`")
            col2.metric("累計請求", f"¥{s['請求額']:,}")
            col3.metric("支払い済み", f"¥{s['支払い済み']:,}")
            col4.metric("残高（未払い）", f"¥{s['残高']:,}", delta=f"-¥{s['残高']:,}", delta_color="inverse")

st.divider()

# ── 完済 ──────────────────────────────────────────────
if 完済:
    with st.expander(f"完済・過払い（{len(完済)}名）"):
        for s in 完済:
            種別 = "月額" if s["滞在種別"] == "月額" else "日額"
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            col1.write(f"**{s['名前']}**　`{種別}`")
            col2.write(f"請求: ¥{s['請求額']:,}")
            col3.write(f"支払い: ¥{s['支払い済み']:,}")
            label = "過払い" if s["残高"] < 0 else "完済"
            col4.write(f"**{label}**: ¥{abs(s['残高']):,}")

st.divider()

# ── 合計 ──────────────────────────────────────────────
総未払い = sum(s["残高"] for s in summary if s["残高"] > 0)
st.metric("全体の未払い合計", f"¥{総未払い:,}")
