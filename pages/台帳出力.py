import io
import csv
from datetime import date
import streamlit as st
from auth import require_auth
from db import get_ledger_rows

require_auth()
st.title("台帳出力")
st.caption("全キャストの宿泊費・確認済み支払いをCSVで出力します（会計ソフト取り込み対応）。")

# ── 期間フィルター ────────────────────────────────────
with st.expander("期間を絞り込む（省略で全期間）"):
    col1, col2 = st.columns(2)
    use_filter = st.checkbox("期間を指定する")
    if use_filter:
        start = col1.date_input("開始日", value=date.today().replace(day=1))
        end   = col2.date_input("終了日", value=date.today())
        start_str = start.isoformat()
        end_str   = end.isoformat()
    else:
        start_str = end_str = None

rows = get_ledger_rows(start_str, end_str)

if not rows:
    st.info("出力対象のデータがありません。")
    st.stop()

st.divider()

# ── プレビュー ────────────────────────────────────────
st.subheader(f"プレビュー（{len(rows)}件）")

for r in rows:
    if r["金額"] < 0:
        r["金額表示"] = f"▲{abs(r['金額']):,}円"
    else:
        r["金額表示"] = f"{r['金額']:,}円"

st.dataframe(
    [{"日付": r["日付"], "キャスト名": r["キャスト名"], "種別": r["種別"],
      "摘要": r["摘要"], "金額": r["金額表示"], "備考": r["備考"]} for r in rows],
    use_container_width=True,
    hide_index=True,
)

# 合計
請求合計 = sum(r["金額"] for r in rows if r["金額"] > 0)
支払合計  = sum(abs(r["金額"]) for r in rows if r["金額"] < 0)
差引残高  = 請求合計 - 支払合計

col1, col2, col3 = st.columns(3)
col1.metric("累計請求", f"¥{請求合計:,}")
col2.metric("確認済み支払い", f"¥{支払合計:,}")
col3.metric("差引残高", f"¥{差引残高:,}")

st.divider()

# ── CSVダウンロード ───────────────────────────────────
output = io.StringIO()
writer = csv.DictWriter(
    output,
    fieldnames=["日付", "キャスト名", "種別", "摘要", "金額", "備考"],
    extrasaction="ignore",
)
writer.writeheader()
writer.writerows(rows)
csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM付きUTF-8（Excel・弥生・freee対応）

filename = f"ryohi_{start_str or 'all'}_{end_str or 'all'}.csv"

st.download_button(
    label="CSVをダウンロード",
    data=csv_bytes,
    file_name=filename,
    mime="text/csv",
    use_container_width=True,
)
