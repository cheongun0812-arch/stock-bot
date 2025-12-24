import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# --- 페이지 설정 및 스타일 ---
st.set_page_config(page_title="CHEONGUN AI Quant", layout="wide")

st.markdown("""
    <style>
    .pos-val { color: #d32f2f !important; font-weight: bold; } 
    .neg-val { color: #2e7d32 !important; font-weight: bold; } 
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 30px; }
    .section-title { font-size: 1.5rem !important; font-weight: 700 !important; margin-top: 20px; }
    td { text-align: right !important; }
    th { text-align: center !important; }
    .result-summary { font-size: 1.1rem; font-weight: 700; margin-top: 10px; padding: 15px; background-color: #f0f2f6; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 엔진: 데이터 및 로컬 저장소 로직 ---
@st.cache_data(ttl=3600)
def get_symbol_data(raw_input):
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

def get_history_chart(ticker):
    data = yf.download(ticker, period="1y")
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
    fig.update_layout(title="최근 1년 주가 흐름", xaxis_rangeslider_visible=False, height=400)
    return fig

# --- 2. 사이드바: 종목 조회 및 포트폴리오 저장 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    # 배포용 초기화 값: 삼성전자(005930)
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_data(user_input)
    
    if ticker:
        st.success(f"✅ {s_name} 연동")
        live_p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
    else:
        live_p = 0.0

    st.divider()
    st.subheader("💾 내 포트폴리오 (로컬)")
    st.info("입력하신 데이터는 사용자의 브라우저 세션에만 임시 보관됩니다.")

# --- 3. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} AI 시뮬레이션</div>", unsafe_allow_html=True)

# 1️⃣ 현재 보유 현황 (배포용 초기화)
st.markdown("<div class='section-title'>👤 1️⃣ 내 현재 보유 현황</div>", unsafe_allow_html=True)
with st.expander("데이터 입력 (초기 상태)", expanded=True):
    c1, c2, c3 = st.columns(3)
    curr_unit = "원" if market == "KR" else "$"
    # 실제 운용 값을 지우고 0 또는 기본 샘플값으로 초기화
    current_avg = st.number_input(f"현재 평단가 ({curr_unit})", value=float(live_p))
    current_qty = st.number_input("현재 보유 수량 (주)", value=0)
    now_p = st.number_input(f"현재 시장가 ({curr_unit})", value=float(live_p))

# 2️⃣ 추가 매수 시나리오
st.divider()
st.markdown("<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])
with cs1: buy_p = st.slider("추가 매수 가격", float(now_p*0.5), float(now_p*1.5), float(now_p))
with cs2: buy_q = st.slider("추가 매수 수량 (주)", 0, 5000, 0)
total_buy_amt = buy_p * buy_q
with cs3:
    st.markdown("**💰 예상 투입 금액**")
    val_str = f"${total_buy_amt:,.2f}" if market == "US" else f"{total_buy_amt:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)

# --- 계산 엔진 ---
old_cost = current_avg * current_qty
new_cost = buy_p * buy_q
total_qty = current_qty + buy_q
final_avg = (old_cost + new_cost) / total_qty if total_qty > 0 else 0

curr_profit_amt = (now_p - current_avg) * current_qty
curr_rtn = (curr_profit_amt / old_cost * 100) if old_cost > 0 else 0

aft_profit_amt = (now_p - final_avg) * total_qty
aft_rtn = (aft_profit_amt / (old_cost + new_cost) * 100) if (old_cost + new_cost) > 0 else 0

# --- 4. 시각화: 차트 추가 ---
st.divider()
st.plotly_chart(get_history_chart(ticker), use_container_width=True)

# --- 5. 분석 결과 ---
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)
r1, r2, r3 = st.columns(3)
with r1:
    st.markdown(f"<p class='bold-text'>실시간 현재가</p><h2>{now_p:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r2:
    diff = final_avg - current_avg
    color, sign, word = ("#d32f2f", "▲", "상승") if diff > 0 else ("#2e7d32", "▼", "하락")
    st.markdown(f"<p class='bold-text'>예상 평단가</p><h2>{final_avg:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r3:
    rtn_color = "#d32f2f" if aft_rtn >= 0 else "#2e7d32"
    st.markdown(f"<p class='bold-text'>예상 수익률</p><h2 style='color:{rtn_color};'>{aft_rtn:.2f}%</h2>", unsafe_allow_html=True)

if total_qty > 0:
    st.markdown(f"<div class='result-summary'>☞ 분석 결과: 평단가가 <span style='color:{color};'>{sign} {abs(diff):,.2f} {word}</span> 되어 {aft_rtn:.2f}% 수익률이 예상됩니다.</div>", unsafe_allow_html=True)

# 데이터 표
df_res = pd.DataFrame({
    "항목": ["보유 수량", "평균 단가", "수익 금액", "수익률(%)"],
    "현재 상태": [f"{current_qty:,}주", f"{current_avg:,.2f}", f"{curr_profit_amt:+,.0f}", f"{curr_rtn:.2f}%"],
    "매수 후 예상": [f"{total_qty:,}주", f"{final_avg:,.2f}", f"{aft_profit_amt:+,.0f}", f"{aft_rtn:.2f}%"]
}).set_index("항목")

def apply_color(val):
    if "+" in str(val): return 'color: #d32f2f; font-weight: bold;'
    if "-" in str(val): return 'color: #2e7d32; font-weight: bold;'
    return ''
st.table(df_res.style.applymap(apply_color))

# --- 6. AI 가이드 ---
st.info("📑 **AI 인텔리전트 가이드**")
if total_qty == 0:
    st.write("상단의 보유 현황과 시나리오 수량을 입력하시면 AI 분석이 시작됩니다.")
elif aft_rtn < 0:
    st.write(f"💡 **AI 분석:** 현재 평단가 회복(ZERO)을 위해 주가가 {abs(aft_rtn):.2f}% 반등해야 합니다. 이번 물타기로 탈출 확률이 높아졌습니다.")
else:
    st.write(f"🎉 **AI 분석:** 수익 구간입니다! 추가 매수는 수익금 극대화를 위한 전략적 선택입니다.")

# --- 제작자 표시 ---
st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b><br>© 2025 All Rights Reserved. Powered by AI Quant Intelligence.</div>", unsafe_allow_html=True)