import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# ----------------------------
# Optional: KR holidays
# ----------------------------
HAS_HOLIDAYS_LIB = True
try:
    import holidays  # pip install holidays
except Exception:
    HAS_HOLIDAYS_LIB = False


# ----------------------------
# UI / Theme (기존 분위기 유지)
# ----------------------------
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0A0A0B; color: #E0E0E0; }
.main-title { font-size: 50px; font-weight: 900; color: #FFD700; }
.violation-card {
    background: #2D0A0A; border: 2px solid #FF4B4B; padding: 22px;
    border-radius: 15px; margin-bottom: 18px;
}
.panel {
    background: #131316; border: 1px solid #2A2A2A; padding: 18px;
    border-radius: 14px; margin-bottom: 16px;
}
.red-text { color: #FF4B4B; font-weight: 900; font-size: 22px; }
.gold-text { color: #FFD700; font-weight: 800; }
.muted { color: #9E9E9E; }
thead tr th { background-color: #FF4B4B !important; color: white !important; font-size: 15px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
st.write("### ⚠️ 법인카드 규정 위반(심야/휴일/공휴일) 자동 탐지 + 월별집계 + 기준금액 초과 모니터링")


# ----------------------------
# Helpers
# ----------------------------
def normalize_money(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(r"[^0-9\-]", "", regex=True),
        errors="coerce"
    ).fillna(0)

def parse_date_only(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.split().str[0]
    return pd.to_datetime(x, errors="coerce")

def parse_hour_from_datetime(s: pd.Series) -> pd.Series:
    t = pd.to_datetime(s.astype(str).str.strip(), errors="coerce")
    return t.dt.hour

def in_night_hours(hour, start, end) -> bool:
    if pd.isna(hour):
        return False
    h = int(hour)
    if start <= end:
        return (h >= start) and (h <= end)
    return (h >= start) or (h <= end)

def auto_detect_header_row(raw_df: pd.DataFrame) -> int:
    header_row = 0
    for i, row in raw_df.head(20).iterrows():
        txt = " ".join([str(x) for x in row.values])
        if any(k in txt for k in ["승인일자", "승인일시", "거래처명", "가맹점", "금액", "사용자",
                                  "Approval date", "Customer name", "Amount", "User"]):
            header_row = i
            break
    return header_row

def find_first_matching_col(cols: list[str], keywords: list[str]):
    for c in cols:
        c_str = str(c)
        for k in keywords:
            if k.lower() in c_str.lower():
                return c
    return None

def build_kr_holiday_set(years: list[int]) -> set:
    if not HAS_HOLIDAYS_LIB:
        return set()
    try:
        kr = holidays.KR(years=years)
        return set(pd.to_datetime(list(kr.keys())))
    except Exception:
        return set()

def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=name[:31])
    return out.getvalue()

def to_tsv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep="\t").encode("utf-8-sig")


# ----------------------------
# Sidebar (요구사항 반영)
# ----------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.markdown("### ⚙️ 감사 기준 설정")

    st.markdown("**① 위반 기준**")
    night_start = st.slider("심야 시작(시)", 0, 23, 23)
    night_end = st.slider("심야 종료(시)", 0, 23, 6)

    restrict_weekend = st.checkbox("주말 사용 제한(휴일=토/일)", value=True)
    restrict_public_holiday = st.checkbox("공휴일 사용 제한(대한민국)", value=True)

    if restrict_public_holiday and not HAS_HOLIDAYS_LIB:
        st.warning("공휴일 탐지: `pip install holidays` 필요(현재는 공휴일 탐지 비활성).")

    st.divider()
    st.markdown("**② 기준금액 초과 표시(위반 아니어도 표시)**")
    monthly_limit_total = st.number_input("월 기준금액(전체합계) 원", min_value=0, value=0, step=100000)
    monthly_limit_per_user = st.number_input("월 기준금액(사용자별) 원", min_value=0, value=0, step=100000)
    single_tx_limit = st.number_input("단건 고액 결제 기준(원)", min_value=0, value=500000, step=50000)

    st.divider()
    st.markdown("**③ 예외(소명/허용 건)**")
    st.caption("예외는 '따로 찾아 설명'하신다고 하셔서, 기본은 위반으로 남기고 표시/다운로드만 합니다.")


# ----------------------------
# Upload & Load
# ----------------------------
uploaded_file = st.file_uploader("📤 카드 사용내역 업로드 (CSV / XLSX)", type=["csv", "xlsx"])

if not uploaded_file:
    st.info("파일 업로드 후 심야/휴일/공휴일 위반과 월별 집계, 기준금액 초과 표시를 자동 생성합니다.")
    st.stop()

try:
    if uploaded_file.name.lower().endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file, header=None, dtype=str, encoding_errors="ignore")
    else:
        raw_df = pd.read_excel(uploaded_file, header=None, dtype=str)
except Exception as e:
    st.error(f"파일 로드 실패: {e}")
    st.stop()

header_row = auto_detect_header_row(raw_df)
df = raw_df.iloc[header_row + 1:].copy()
df.columns = [str(c).strip() for c in raw_df.iloc[header_row].values]
cols = list(df.columns)

# ----------------------------
# Column Mapping (한글+영문 동시 지원)
# ----------------------------
col_date = find_first_matching_col(cols, ["승인일자", "거래일자", "사용일자", "Approval date"])
col_time = find_first_matching_col(cols, ["승인일시", "승인시간", "Approval date"])  # Approval date에 시간 포함되는 경우
col_amt = find_first_matching_col(cols, ["금액", "이용금액", "합계", "Amount"])
col_merchant = find_first_matching_col(cols, ["거래처명", "가맹점명", "가맹점", "Customer name"])
col_user = find_first_matching_col(cols, ["사용자", "이용자명", "User"])
col_cardno = find_first_matching_col(cols, ["카드번호", "Card number"])
col_approveno = find_first_matching_col(cols, ["승인번호", "Approval number"])
col_docno = find_first_matching_col(cols, ["문서번호", "Document number"])
col_slipno = find_first_matching_col(cols, ["전표번호", "Slip number"])
col_title = find_first_matching_col(cols, ["문서 내용", "문서내용", "Document content", "title"])

missing = [name for name, c in [("승인일자/Approval date", col_date), ("금액/Amount", col_amt)] if c is None]
if missing:
    st.error(f"필수 컬럼을 찾지 못했습니다: {', '.join(missing)}\n\n현재 컬럼: {', '.join(cols)}")
    st.stop()

# If time column is missing, reuse date column if it contains timestamp
if col_time is None:
    col_time = col_date

# ----------------------------
# Normalize
# ----------------------------
df[col_amt] = normalize_money(df[col_amt])
df["__date"] = parse_date_only(df[col_date])
df["__hour"] = parse_hour_from_datetime(df[col_time])

df = df[~df["__date"].isna()].copy()
df["month"] = df["__date"].dt.to_period("M").astype(str)

df["is_weekend"] = df["__date"].dt.weekday >= 5
df["is_night"] = df["__hour"].apply(lambda h: in_night_hours(h, night_start, night_end))

# KR public holidays
df["is_public_holiday"] = False
if restrict_public_holiday and HAS_HOLIDAYS_LIB:
    years = sorted({int(y) for y in df["__date"].dt.year.dropna().unique().tolist()})
    kr_holidays = build_kr_holiday_set(years)
    if len(kr_holidays) > 0:
        d_only = pd.to_datetime(df["__date"].dt.date)
        df["is_public_holiday"] = d_only.isin(kr_holidays)

# ----------------------------
# Violation Reason
# (요구사항: 심야/휴일/공휴일을 위반으로 분류)
# ----------------------------
def build_reason(row) -> str:
    reasons = []
    if row["is_night"]:
        reasons.append("심야사용")
    if restrict_weekend and row["is_weekend"]:
        reasons.append("주말사용")
    if restrict_public_holiday and row["is_public_holiday"]:
        reasons.append("공휴일사용")
    return " / ".join(reasons)

df["violation_reason"] = df.apply(build_reason, axis=1)
df["is_violation"] = df["violation_reason"].str.len() > 0

# High amount (단건 고액)
df["is_high_amount"] = (df[col_amt] >= float(single_tx_limit)) if single_tx_limit and single_tx_limit > 0 else False

# ----------------------------
# Monthly totals + threshold exceed
# ----------------------------
monthly_total = df.groupby("month", as_index=False)[col_amt].sum().rename(columns={col_amt: "월합계(전체)"})
monthly_total["기준초과(전체)"] = False
if monthly_limit_total and monthly_limit_total > 0:
    monthly_total["기준초과(전체)"] = monthly_total["월합계(전체)"] >= float(monthly_limit_total)

if col_user is None:
    df["__user"] = "미분류"
    user_col = "__user"
else:
    user_col = col_user

monthly_user = df.groupby(["month", user_col], as_index=False)[col_amt].sum().rename(columns={col_amt: "월합계(사용자)"})
monthly_user["기준초과(사용자)"] = False
if monthly_limit_per_user and monthly_limit_per_user > 0:
    monthly_user["기준초과(사용자)"] = monthly_user["월합계(사용자)"] >= float(monthly_limit_per_user)

df = df.merge(monthly_total[["month", "기준초과(전체)"]], on="month", how="left")
df = df.merge(monthly_user[["month", user_col, "기준초과(사용자)"]], on=["month", user_col], how="left")
df["is_exceed_any"] = df["기준초과(전체)"].fillna(False) | df["기준초과(사용자)"].fillna(False)

# ----------------------------
# UI Filters
# ----------------------------
with st.container():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1.6])
    with c1:
        month_options = ["전체"] + sorted(df["month"].unique().tolist())
        pick_month = st.selectbox("조회 월", options=month_options, index=0)
    with c2:
        only_viol = st.checkbox("위반만 보기", value=True)
    with c3:
        only_exceed = st.checkbox("기준초과만 보기", value=False)
    with c4:
        keyword = st.text_input("검색(거래처/사용자/문서번호 등)", value="")
    st.markdown('</div>', unsafe_allow_html=True)

view = df.copy()
if pick_month != "전체":
    view = view[view["month"] == pick_month].copy()
if only_viol:
    view = view[view["is_violation"]].copy()
if only_exceed:
    view = view[view["is_exceed_any"]].copy()

if keyword.strip():
    k = keyword.strip()
    search_cols = [c for c in [col_merchant, col_user, col_docno, col_cardno, col_approveno, col_title] if c is not None and c in view.columns]
    if not search_cols:
        search_cols = [col_date]
    mask = False
    for c in search_cols:
        mask = mask | view[c].astype(str).str.contains(k, na=False)
    view = view[mask].copy()

# ----------------------------
# Metrics
# ----------------------------
total_amt = float(df[col_amt].sum())
total_cnt = len(df)
viol_cnt = int(df["is_violation"].sum())
viol_amt = float(df.loc[df["is_violation"], col_amt].sum())
exceed_cnt = int(df["is_exceed_any"].sum())
high_cnt = int(df["is_high_amount"].sum())

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("총 집행(전체)", f"{total_amt:,.0f}원")
m2.metric("전체 건수", f"{total_cnt:,}건")
m3.metric("위반 건수", f"{viol_cnt:,}건")
m4.metric("위반 금액", f"{viol_amt:,.0f}원")
m5.metric("기준초과(월) 건수", f"{exceed_cnt:,}건")
m6.metric("단건 고액", f"{high_cnt:,}건")

# ----------------------------
# Violation Summary Card
# ----------------------------
night_df = df[df["is_night"]].copy()
weekend_df = df[df["is_weekend"]].copy()
holiday_df = df[df["is_public_holiday"]].copy()

st.markdown('<div class="violation-card">', unsafe_allow_html=True)
st.markdown(
    f'<p class="red-text">🚨 위반 리스크 탐지 보고</p>'
    f'<div class="muted">'
    f'심야 {len(night_df):,}건 / 주말 {len(weekend_df):,}건 / 공휴일 {len(holiday_df):,}건'
    f'</div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------
# Display table (중요 정보 중심)
# ----------------------------
def build_display(df_in: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["승인일자"] = pd.to_datetime(df_in["__date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["승인일시"] = df_in[col_time].astype(str) if col_time in df_in.columns else ""
    if col_merchant is not None:
        out["거래처명"] = df_in[col_merchant].astype(str)
    if col_user is not None:
        out["사용자"] = df_in[col_user].astype(str)
    out["금액"] = pd.to_numeric(df_in[col_amt], errors="coerce").fillna(0).astype(float)

    if col_cardno is not None:
        out["카드번호"] = df_in[col_cardno].astype(str)
    if col_approveno is not None:
        out["승인번호"] = df_in[col_approveno].astype(str)
    if col_docno is not None:
        out["문서번호"] = df_in[col_docno].astype(str)
    if col_slipno is not None:
        out["전표번호"] = df_in[col_slipno].astype(str)
    if col_title is not None:
        out["문서제목"] = df_in[col_title].astype(str)

    out["월"] = df_in["month"].astype(str)
    out["위반여부"] = df_in["is_violation"].fillna(False)
    out["위반사유"] = df_in["violation_reason"].astype(str)
    out["초과여부"] = df_in["is_exceed_any"].fillna(False)
    out["고액여부"] = df_in["is_high_amount"].fillna(False)
    out["주말"] = df_in["is_weekend"].fillna(False)
    out["공휴일"] = df_in["is_public_holiday"].fillna(False)
    out["심야"] = df_in["is_night"].fillna(False)

    return out

st.markdown("### 📌 위반/초과 상태 목록")
display_df = build_display(view)
st.dataframe(
    display_df,
    use_container_width=True,
    height=420,
    column_config={
        "금액": st.column_config.NumberColumn(format="%,.0f 원"),
        "위반여부": st.column_config.CheckboxColumn(),
        "초과여부": st.column_config.CheckboxColumn(),
        "고액여부": st.column_config.CheckboxColumn(),
        "주말": st.column_config.CheckboxColumn(),
        "공휴일": st.column_config.CheckboxColumn(),
        "심야": st.column_config.CheckboxColumn(),
    },
)

# ----------------------------
# Downloads
# ----------------------------
violations = df[df["is_violation"]].copy()
exceeds = df[df["is_exceed_any"]].copy()

viol_x = build_display(violations)
exceed_x = build_display(exceeds) if len(exceeds) > 0 else pd.DataFrame()

st.markdown("### ⬇️ 다운로드")
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button(
        "🚨 위반내역 Excel 다운로드",
        data=to_excel_bytes({"위반내역": viol_x}),
        file_name="violations.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    st.download_button(
        "🚨 위반내역 텍스트(TSV) 다운로드",
        data=to_tsv_bytes(viol_x),
        file_name="violations.tsv",
        mime="text/tab-separated-values",
        use_container_width=True
    )

with d2:
    st.download_button(
        "📈 기준초과내역 Excel 다운로드",
        data=to_excel_bytes({"기준초과내역": exceed_x}) if not exceed_x.empty else b"",
        file_name="exceeds.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=exceed_x.empty,
        use_container_width=True
    )
    st.download_button(
        "📈 기준초과내역 텍스트(TSV) 다운로드",
        data=to_tsv_bytes(exceed_x) if not exceed_x.empty else b"",
        file_name="exceeds.tsv",
        mime="text/tab-separated-values",
        disabled=exceed_x.empty,
        use_container_width=True
    )

with d3:
    monthly_total_x = monthly_total.copy()
    monthly_user_x = monthly_user.copy()
    st.download_button(
        "🧾 월별집계 Excel 다운로드",
        data=to_excel_bytes({"월집계_전체": monthly_total_x, "월집계_사용자": monthly_user_x}),
        file_name="monthly_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ----------------------------
# Chart: Monthly trend
# ----------------------------
st.markdown("### 📊 월별 사용 추이(전체)")
trend = monthly_total.sort_values("month").copy()
fig = go.Figure()
fig.add_trace(go.Scatter(x=trend["month"], y=trend["월합계(전체)"], mode="lines+markers"))
fig.update_layout(
    title="월별 집행 합계(전체)",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color="white"),
    xaxis_title="월",
    yaxis_title="원"
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("ℹ️ 운영 메모", expanded=False):
    st.write("""
- 위반 분류: 심야 + (옵션) 주말 + (옵션) 공휴일  
- 예외는 별도 소명/설명 대상으로 남겨두는 구조(요구사항 반영)  
- 기준금액 초과는 위반과 무관하게 표시/다운로드 가능  
- 공휴일 탐지는 `holidays` 설치 시 활성
""")
