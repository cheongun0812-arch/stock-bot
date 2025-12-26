import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- [스타일 설정] ---
st.set_page_config(page_title="CHEONGUN Quant Simulator", layout="wide")

st.markdown("""
    <style>
    .pos-val { color: #d32f2f; font-weight: bold; } 
    .neg-val { color: #2e7d32; font-weight: bold; } 
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 20px; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 20px; margin-bottom: 15px; }
    td { text-align: right !important; }
    th { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 데이터 엔진 ---
@st.cache_data(ttl=3600)
def get_symbol_info(raw_input):
    if not raw_input: return None, "KR", "입력대기"
    raw_input = raw_input.strip().upper()
    ticker_out, market, name = None, "KR", raw_input
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            if not t_obj.history(period="5d").empty:
                ticker_out, market = raw_input + suffix, "KR"
                name = t_obj.info.get('shortName') or t_obj.info.get('longName') or raw_input
                break
    else:
        t_obj = yf.Ticker(raw_input)
        if not t_obj.history(period="5d").empty:
            ticker_out, market = raw_input, "US"
            name = t_obj.info.get('shortName', raw_input)
    return ticker_out, market, name

def get_technical_chart(ticker_symbol):
    if not ticker_symbol: return None
    df = yf.download(ticker_symbol, period="1y", progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 이동평균선 계산 (2, 6, 20, 60, 180일)
    for ma in [2, 6, 20, 60, 180]:
        df[f'MA{ma}'] = df['Close'].rolling(window=ma).mean()
    
    fig = go.Figure()
    # 캔들스틱
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))
    # 이평선 추가
    colors = ['#FFD700', '#FF8C00', '#FF1493', '#00BFFF', '#8B4513']
    for i, ma in enumerate([2, 6, 20, 60, 180]):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{ma}'], line=dict(width=1.2, color=colors[i]), name=f'{ma}일선'))
    
    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white", 
                      margin=dict(t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- 2. 사이드바 및 초기 가격 세팅 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    user_input = st.text_input("종목 번호 또는 티커", value="005930")
    ticker, market, s_name = get_symbol_info(user_input)
    
    live_p = 0.0
    if ticker:
        live_p = float(yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1])
        st.success(f"✅ {s_name} 승인")
    unit = "원" if market == "KR" else "$"

# --- 3. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} 투자 시뮬레이션</div>", unsafe_allow_html=True)

# [정정] 현재 보유 현황 섹션 (수동 입력값 보존을 위해 기본값 설정을 유동적으로 변경)
st.markdown(f"<div class='section-title'>👤 1️⃣ 내 현재 보유 현황 ({unit})</div>", unsafe_allow_html=True)
with st.expander("데이터 입력", expanded=True):
    c1, c2, c3 = st.columns(3)
    # value에 live_p를 직접 넣지 않고, 초기값으로만 사용되게 하거나 사용자가 직접 제어하게 함
    current_avg = st.number_input(f"현재 내 평단가", value=float(live_p) if live_p > 0 else 0.0, step=10.0 if market=="KR" else 0.01)
    current_qty = st.number_input("현재 보유 수량 (주)", value=0, step=1)
    now_p = st.number_input(f"현재 시장가 (실시간)", value=float(live_p), step=10.0 if market=="KR" else 0.01)

# --- 4. 추가 매수 시나리오 (양방향 동기화) ---
st.divider()
st.markdown(f"<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오 ({unit})</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])

p_min, p_max = float(now_p * 0.1), float(now_p * 3.0)
with cs1:
    buy_p_in = st.number_input(f"추가 매수 가격", min_value=p_min, max_value=p_max, value=float(now_p))
    buy_p = st.slider("가격 미세 조정", p_min, p_max, value=min(max(buy_p_in, p_min), p_max), label_visibility="collapsed")
with cs2:
    buy_q_in = st.number_input("추가 구매 수량", min_value=0, max_value=100000, value=0)
    buy_q = st.slider("수량 미세 조정", 0, 100000, value=int(buy_q_in), label_visibility="collapsed")

total_buy = buy_p * buy_q
with cs3:
    st.markdown(f"**💰 추가 매수 총액**")
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{total_buy:,.0f}{unit}</h3>", unsafe_allow_html=True)

# --- 5. 분석 결과 ---
st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)

total_qty = current_qty + buy_q
final_avg = ((current_avg * current_qty) + total_buy) / total_qty if total_qty > 0 else 0
avg_diff = final_avg - current_avg
aft_rtn = ((now_p - final_avg) / final_avg * 100) if final_avg > 0 else 0

res_c1, res_c2, res_c3 = st.columns(3)
with res_c1: st.metric("현재 시장가", f"{now_p:,.0f} {unit}")
with res_c2: st.metric("예상 평단가", f"{final_avg:,.2f} {unit}", f"{avg_diff:,.2f} ({'상승' if avg_diff > 0 else '하락'})", delta_color="inverse")
with res_c3: st.metric("예상 수익률", f"{aft_rtn:.2f}%")

# --- 6. [복구] 1년 주가 캔들 차트 및 이평선 ---
st.markdown("<div class='section-title'>📊 최근 1년 주가 흐름 및 기술적 지표</div>", unsafe_allow_html=True)
chart_fig = get_technical_chart(ticker)
if chart_fig:
    st.plotly_chart(chart_fig, use_container_width=True)
else:
    st.info("종목을 조회하면 차트가 표시됩니다.")

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b></div>", unsafe_allow_html=True)