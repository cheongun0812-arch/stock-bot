import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="CHEONGUN AI Quant Master", layout="wide")

# CSS 스타일 정의: 단위와 결과값 가독성 최적화
st.markdown("""
    <style>
    .pos-val { color: #d32f2f !important; font-weight: bold; } 
    .neg-val { color: #2e7d32 !important; font-weight: bold; } 
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 10px; }
    .disclaimer { font-size: 0.85rem; color: #666666; text-align: center; margin-bottom: 30px; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 25px; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; }
    .result-summary { font-size: 1.15rem; font-weight: 700; margin-top: 15px; padding: 15px; background-color: #f8f9fa; border-radius: 10px; border-left: 8px solid #2e7d32; }
    /* 표 데이터 우측 정렬 */
    td { text-align: right !important; }
    th { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 코어 엔진: 데이터 로드 및 차트 ---
@st.cache_data(ttl=3600)
def get_symbol_info(raw_input):
    if not raw_input: return None, "KR", "None", 0.0
    raw_input = raw_input.strip().upper()
    ticker_out, market, name, price = None, "KR", raw_input, 0.0
    
    # 한국 종목 처리
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            hist = t_obj.history(period="1d")
            if not hist.empty:
                ticker_out, market = raw_input + suffix, "KR"
                name = t_obj.info.get('longName', raw_input)
                price = float(hist['Close'].iloc[-1])
                break
    # 미국 및 해외 종목 처리
    else:
        t_obj = yf.Ticker(raw_input)
        hist = t_obj.history(period="1d")
        if not hist.empty:
            ticker_out, market = raw_input, "US"
            name = t_obj.info.get('shortName', raw_input)
            price = float(hist['Close'].iloc[-1])
            
    return ticker_out, market, name, price

def get_candle_chart(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="2y", progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 이동평균선 계산
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA120'] = df['Close'].rolling(120).mean()
        df = df.iloc[-252:].copy()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#FF1493', width=1.5), name='20일선'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='#8B4513', width=2), name='120일선'))
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white", margin=dict(t=30, b=10))
        return fig
    except: return None

# --- 3. 사이드바 및 단위 설정 ---
with st.sidebar:
    st.header("🔍 종목 설정")
    u_input = st.text_input("종목번호 또는 티커", value="005930")
    ticker, mkt_type, s_name, live_p = get_symbol_info(u_input)
    
    # [핵심] 단위 및 입력 간격 자동 설정
    unit = "원" if mkt_type == "KR" else "$"
    step_val = 100.0 if mkt_type == "KR" else 0.01
    
    if ticker: st.success(f"✅ {s_name} ({unit}) 연동")

# --- 4. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} AI 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown("<div class='disclaimer'>제공되는 데이터는 참고용이며, 투자 결정의 책임은 본인에게 있습니다.</div>", unsafe_allow_html=True)

# 1️⃣ 현재 보유 현황
st.markdown(f"<div class='section-title'>👤 1️⃣ 현재 보유 현황 ({unit})</div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: cur_avg = st.number_input(f"현재 평단가", value=live_p, step=step_val)
with c2: cur_qty = st.number_input("현재 수량 (주)", value=0, step=1)
with c3: now_p = st.number_input(f"현재 시장가", value=live_p, step=step_val)

# 2️⃣ 추가 매수 시나리오 (양방향 동기화)
st.markdown(f"<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오 ({unit})</div>", unsafe_allow_html=True)
cs1, cs2 = st.columns(2)
p_min, p_max = float(now_p * 0.1), float(now_p * 2.0)
if p_min == p_max: p_max += 100.0

with cs1:
    buy_p_in = st.number_input(f"추가 매수 가격", min_value=p_min, max_value=p_max, value=now_p, step=step_val)
    buy_p = st.slider("가격 조정 (드래그)", p_min, p_max, value=min(max(buy_p_in, p_min), p_max), step=step_val, label_visibility="collapsed")

with cs2:
    buy_q_in = st.number_input("추가 매수 수량", min_value=0, max_value=10000, value=0, step=1)
    buy_q = st.slider("수량 조정 (드래그)", 0, 10000, value=buy_q_in, step=1, label_visibility="collapsed")

# --- 5. 분석 결과 섹션 ---
total_qty = cur_qty + buy_q
total_invest = (cur_avg * cur_qty) + (buy_p * buy_q)
final_avg = total_invest / total_qty if total_qty > 0 else 0
avg_diff = final_avg - cur_avg
profit_rtn = ((now_p - final_avg) / final_avg * 100) if final_avg > 0 else 0

st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
m1.metric("예상 평단가", f"{final_avg:,.2f} {unit}", f"{avg_diff:,.2f} {unit}", delta_color="inverse")
m2.metric("최종 보유 수량", f"{total_qty:,} 주")
m3.metric("예상 수익률", f"{profit_rtn:.2f}%")

# [요청사항] 하단 상세 텍스트 결과
if total_qty > 0:
    color = "#d32f2f" if avg_diff > 0 else "#2e7d32"
    status = "상승(불타기)" if avg_diff > 0 else "하락(물타기)"
    st.markdown(f"<div class='result-summary'>☞ 분석 결과: 평단가가 기존 대비 <span style='color:{color};'>{abs(avg_diff):,.2f} {unit} {status}</span>하여 최종 <span style='color:{color};'>{final_avg:,.2f} {unit}</span>이 되었습니다.</div>", unsafe_allow_html=True)

# 차트 출력
chart = get_candle_chart(ticker)
if chart: st.plotly_chart(chart, use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b> | © 2025 AI Quant Master</div>", unsafe_allow_html=True)