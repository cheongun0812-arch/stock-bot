import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="CHEONGUN AI Quant Master", layout="wide")

st.markdown("""
    <style>
    .pos-val { color: #d32f2f !important; font-weight: bold; } 
    .neg-val { color: #2e7d32 !important; font-weight: bold; } 
    .main-title { font-size: 2.2rem; font-weight: 900; text-align: center; margin-bottom: 5px; }
    .disclaimer { font-size: 0.8rem; color: #666666; text-align: center; margin-bottom: 20px; }
    .section-title { font-size: 1.5rem !important; font-weight: 700 !important; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #f0f2f6; }
    .result-summary { font-size: 1.1rem; font-weight: 700; margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 코어 엔진: 데이터 로드 ---
@st.cache_data(ttl=3600)
def get_symbol_data(raw_input):
    if not raw_input: return None, "KR", "None", 0.0
    raw_input = raw_input.strip().upper()
    
    ticker_out, market, name = None, "KR", raw_input
    
    # 한국 종목 (6자리 숫자)
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            hist = t_obj.history(period="1d")
            if not hist.empty:
                ticker_out = raw_input + suffix
                market = "KR"
                name = t_obj.info.get('longName') or t_obj.info.get('shortName') or raw_input
                break
    # 미국 및 기타
    else:
        t_obj = yf.Ticker(raw_input)
        hist = t_obj.history(period="1d")
        if not hist.empty:
            ticker_out = raw_input
            market = "US"
            name = t_obj.info.get('shortName', raw_input)
            
    # 가격 정보 추출
    price = 0.0
    if ticker_out:
        price = float(yf.Ticker(ticker_out).history(period="1d")['Close'].iloc[-1])
        
    return ticker_out, market, name, price

def get_advanced_chart(ticker_symbol):
    if not ticker_symbol: return None
    try:
        df = yf.download(ticker_symbol, period="2y", progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 이평선
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        df = df.iloc[-252:].copy().dropna(subset=['Close'])
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))
        for c, clr, lbl in [('MA5','#FFD700','5일'),('MA20','#FF1493','20일'),('MA60','#00BFFF','60일'),('MA120','#8B4513','120일')]:
            fig.add_trace(go.Scatter(x=df.index, y=df[c], line=dict(color=clr, width=1.3), name=lbl))
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
        return fig
    except: return None

# --- 3. 사이드바 및 상태 관리 ---
with st.sidebar:
    st.header("🔍 종목 조회")
    user_input = st.text_input("종목코드(6자리) 또는 티커 입력", value="005930")
    ticker, market_type, s_name, live_p = get_symbol_data(user_input)
    
    # 단위 설정
    unit = "원" if market_type == "KR" else "$"
    step_val = 100.0 if market_type == "KR" else 0.01
    
    if ticker:
        st.success(f"✅ {s_name} ({unit})")
    else:
        st.error("종목을 찾을 수 없습니다.")

# --- 4. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} 시뮬레이션 ({unit})</div>", unsafe_allow_html=True)
st.markdown("<div class='disclaimer'>모든 투자의 책임은 본인에게 있습니다.</div>", unsafe_allow_html=True)

# 1️⃣ 보유 현황
st.markdown("<div class='section-title'>👤 1️⃣ 현재 보유 현황</div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: cur_avg = st.number_input(f"현재 평단가 ({unit})", value=live_p, step=step_val)
with c2: cur_qty = st.number_input("현재 보유 수량 (주)", value=0, step=1)
with c3: mkt_p = st.number_input(f"현재 시장가 ({unit})", value=live_p, step=step_val)

# 2️⃣ 추가 매수 시나리오 (양방향 동기화)
st.markdown("<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오</div>", unsafe_allow_html=True)
cs1, cs2 = st.columns(2)

# 안전 범위 설정
p_min, p_max = float(mkt_p * 0.1), float(mkt_p * 2.0)
if p_min == p_max: p_max = p_min + 100.0

with cs1:
    buy_p_input = st.number_input(f"추가 매수 가격 ({unit})", min_value=p_min, max_value=p_max, value=mkt_p, step=step_val)
    # 안전 장치: 입력값이 범위를 벗어날 경우 대비
    safe_p = min(max(buy_p_input, p_min), p_max)
    buy_p = st.slider("가격 조정 (드래그)", p_min, p_max, value=safe_p, step=step_val, label_visibility="collapsed")

with cs2:
    buy_q_input = st.number_input("추가 구매 수량 (주)", min_value=0, max_value=10000, value=0, step=1)
    buy_q = st.slider("수량 조정 (드래그)", 0, 10000, value=buy_q_input, step=1, label_visibility="collapsed")

# --- 5. 분석 결과 ---
total_qty = cur_qty + buy_q
total_cost = (cur_avg * cur_qty) + (buy_p * buy_q)
final_avg = total_cost / total_qty if total_qty > 0 else 0
avg_diff = final_avg - cur_avg
profit_rate = ((mkt_p - final_avg) / final_avg * 100) if final_avg > 0 else 0

st.divider()
res_c1, res_c2, res_c3 = st.columns(3)
res_c1.metric("예상 평단가", f"{final_avg:,.2f} {unit}", f"{avg_diff:,.2f}", delta_color="inverse")
res_c2.metric("최종 보유수량", f"{total_qty:,} 주")
res_c3.metric("예상 수익률", f"{profit_rate:.2f}%")

# 차트 출력
chart = get_advanced_chart(ticker)
if chart:
    st.plotly_chart(chart, use_container_width=True)

if total_qty > 0:
    color = "#d32f2f" if avg_diff > 0 else "#2e7d32"
    updown = "상승" if avg_diff > 0 else "하락"
    st.markdown(f"<div class='result-summary'>☞ 분석: 추가 매수 후 평단가가 기존 대비 <span style='color:{color};'>{abs(avg_diff):,.2f} {unit} {updown}</span>합니다.</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b></div>", unsafe_allow_html=True)