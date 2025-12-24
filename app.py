import streamlit as st
import yfinance as yf
import pandas as pd

# --- 페이지 설정 및 스타일 정의 ---
st.set_page_config(page_title="CHEONGUN Quant Simulator", layout="wide")

# UI 커스텀 스타일 정의
st.markdown("""
    <style>
    /* 수익 색상 정의: 상승/수익(Red), 하락/손실(Green) */
    .pos-val { color: #d32f2f !important; font-weight: bold; } 
    .neg-val { color: #2e7d32 !important; font-weight: bold; } 
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 30px; }
    /* 섹션 타이틀 크기 통일 */
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 30px; margin-bottom: 15px; }
    /* 표 내부 텍스트 우측 정렬 */
    td { text-align: right !important; }
    th { text-align: center !important; }
    /* 하단 결과 메시지 스타일 */
    .result-summary { font-size: 1.1rem; font-weight: 700; margin-top: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 엔진: 데이터 로드 및 종목 처리 ---
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try: return yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    except: return 1380.0

@st.cache_data(ttl=3600)
def get_symbol_info(raw_input):
    raw_input = raw_input.strip().upper()
    ticker_out, market, name = None, None, raw_input
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            if not t_obj.history(period="1d").empty:
                ticker_out, market = raw_input + suffix, "KR"
                name = t_obj.info.get('longName') or t_obj.info.get('shortName') or raw_input
                mapping = {"Samsung Electronics Co., Ltd.": "삼성전자", "SK hynix Inc.": "SK하이닉스"}
                name = mapping.get(name, name)
                break
    else:
        t_obj = yf.Ticker(raw_input)
        if not t_obj.history(period="1d").empty:
            ticker_out, market, name = raw_input, "US", t_obj.info.get('shortName', raw_input)
    return ticker_out, market, name

# --- 2. 사이드바: 관심 종목 조회 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_info(user_input)
    ex_rate = get_exchange_rate()
    live_p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1] if ticker else 0.0
    if ticker: st.success(f"✅ {s_name} 연동 성공")

# --- 3. 메인 화면: 현재 보유 현황 ---
st.markdown(f"<div class='main-title'>📈 {s_name} 투자 시뮬레이션</div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'> 1️⃣ 내 현재 보유 현황</div>", unsafe_allow_html=True)
with st.expander("내 자산 데이터 입력", expanded=True):
    c1, c2, c3 = st.columns(3)
    curr_unit = "원" if market == "KR" else "$"
    with c1: current_avg = st.number_input(f"현재 내 평단가 ({curr_unit})", value=76397.0)
    with c2: current_qty = st.number_input("현재 보유 수량 (주)", value=1200)
    with c3: now_p = st.number_input(f"현재 주식 단가 (자동연동/수정)", value=float(live_p))

# --- 4. 추가 매수 시나리오 (드래그 조절) ---
st.divider()
st.markdown("<div class='section-title'> 2️⃣ 추가 매수 시나리오</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])
with cs1: buy_p = st.slider("추가 매수 가격", float(now_p*0.1), float(now_p*2.0), float(now_p))
with cs2: buy_q = st.slider("추가 구매 수량 (주)", 1, 5000, 100)
total_buy_amt = buy_p * buy_q
with cs3:
    st.markdown("**💰 추가 구매 총액**")
    val_str = f"${total_buy_amt:,.2f}" if market == "US" else f"{total_buy_amt:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)
    if market == "US": st.caption(f"(약 {total_buy_amt*ex_rate:,.0f}원)")

# --- 5. 계산 엔진 ---
old_cost = current_avg * current_qty
new_cost = buy_p * buy_q
total_qty = current_qty + buy_q
final_avg = (old_cost + new_cost) / total_qty

curr_profit_amt = (now_p - current_avg) * current_qty
curr_rtn = (curr_profit_amt / old_cost) * 100 if old_cost != 0 else 0

after_profit_amt = (now_p - final_avg) * total_qty
aft_rtn = (after_profit_amt / (old_cost + new_cost)) * 100 if (old_cost + new_cost) != 0 else 0

# --- 6. 시뮬레이션 분석 결과 ---
st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
with r1:
    val = f"${now_p:,.2f}" if market == "US" else f"{int(now_p):,}원"
    st.markdown(f"<p class='bold-text'>실시간 현재가</p><h2 class='bold-text'>{val}</h2>", unsafe_allow_html=True)

with r2:
    val = f"${final_avg:,.2f}" if market == "US" else f"{int(final_avg):,}원"
    diff = final_avg - current_avg
    if diff > 0: color, sign, word = "#d32f2f", "▲", "상승"
    elif diff < 0: color, sign, word = "#2e7d32", "▼", "하락"
    else: color, sign, word = "gray", "-", "유지"
    
    st.markdown(f"<p class='bold-text'>예상 평단가</p><h2 class='bold-text'>{val}</h2>", unsafe_allow_html=True)

with r3:
    rtn_color = "#d32f2f" if aft_rtn >= 0 else "#2e7d32"
    st.markdown(f"<p class='bold-text'>예상 수익률 변화</p><h2 style='color:{rtn_color}; font-weight:800;'>{aft_rtn:.2f}%</h2>", unsafe_allow_html=True)

# [요청하신 기능] 메트릭 하단 통합 안내 문구
st.markdown(f"<div class='result-summary'>☞ 본 물타기 시뮬레이션 분석 결과 주당 평단가 <span style='color:{color};'>{sign} {abs(diff):,.2f} {word}</span>이 되었습니다.</div>", unsafe_allow_html=True)

# 상세 데이터 표 (제목 삭제 및 동적 색상 적용)
data_conv = ex_rate if market == 'US' else 1
df_res = pd.DataFrame({
    "항목": ["보유 수량", "평균 단가", "총 투자금(원화환산)", "수익 금액", "수익률(%)"],
    "현재 상태": [
        f"{current_qty:,}주", f"{current_avg:,.2f}", f"{old_cost * data_conv:,.0f}원", 
        f"{curr_profit_amt * data_conv:+,.0f}원", f"{curr_rtn:.2f}%"
    ],
    "추가 매수 후 예상": [
        f"{total_qty:,}주", f"{final_avg:,.2f}", f"{(old_cost + new_cost) * data_conv:,.0f}원", 
        f"{after_profit_amt * data_conv:+,.0f}원", f"{aft_rtn:.2f}%"
    ]
}).set_index("항목")

# 스타일 함수 정의 (수익금액/수익률 행에 색상 적용)
def style_financials(styler):
    def get_color(val):
        if "+" in str(val) or (isinstance(val, (int, float)) and val > 0): return 'color: #d32f2f; font-weight: bold;'
        if "-" in str(val) or (isinstance(val, (int, float)) and val < 0): return 'color: #2e7d32; font-weight: bold;'
        return ''
    styler.applymap(get_color, subset=pd.IndexSlice[['수익 금액', '수익률(%)'], :])
    return styler

st.table(style_financials(df_res.style))

# --- 7. AI 인텔리전트 가이드 ---
st.info("📑 **AI 인텔리전트 가이드**")
if aft_rtn < 0:
    st.write(f"현재 {s_name} 평단가 회복(ZERO)까지 주가가 약 **{abs(aft_rtn):.2f}%** 더 상승해야 합니다.")
    st.write(f"💡 **AI 분석:** 추가 매수를 통해 평단가를 {abs(final_avg-current_avg):,.2f}원 조절했습니다. 이는 반등 시 본전 회복 시점을 앞당기는 최적의 전략입니다.")
else:
    st.write(f"🎉 **현재 수익 구간입니다!**")
    if buy_p > current_avg:
        st.write(f"💡 **AI 분석(불타기):** 현재 수익을 누리면서 비중을 공격적으로 늘리는 시나리오입니다. 추세 상승 시 수익금을 극대화할 수 있습니다.")
    else:
        st.write(f"💡 **AI 분석(비중 확대):** 저점 매수 기회를 활용하여 안정적으로 자산 규모를 키우는 전략입니다.")

# --- 제작자 표시 ---
st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b><br>© 2025 All Rights Reserved. Powered by Quant Intelligence.</div>", unsafe_allow_html=True)