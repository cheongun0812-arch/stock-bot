import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- [1. 페이지 설정 및 초기화] ---
st.set_page_config(page_title="CHEONGUN Quant Simulator", layout="wide")

# 세션 상태 초기화 (입력값 고정용)
if 'my_avg' not in st.session_state: st.session_state.my_avg = 0.0
if 'my_qty' not in st.session_state: st.session_state.my_qty = 0

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 20px; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 20px; margin-bottom: 15px; }
    td { text-align: right !important; }
    th { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- [2. 데이터 엔진] ---
@st.cache_data(ttl=3600)
def get_symbol_info(raw_input):
    if not raw_input: return None, "KR", "입력대기"
    raw_input = raw_input.strip().upper()
    ticker_out, market, name = None, "KR", raw_input
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            if not t_obj.history(period="1d").empty:
                ticker_out, market = raw_input + suffix, "KR"
                name = t_obj.info.get('shortName') or t_obj.info.get('longName') or raw_input
                break
    else:
        t_obj = yf.Ticker(raw_input)
        if not t_obj.history(period="1d").empty:
            ticker_out, market = raw_input, "US"
            name = t_obj.info.get('shortName', raw_input)
    return ticker_out, market, name

def get_technical_chart(ticker_symbol):
    if not ticker_symbol: return None
    df = yf.download(ticker_symbol, period="1y", progress=False, auto_adjust=True)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    for ma in [2, 6, 20, 60, 180]:
        df[f'MA{ma}'] = df['Close'].rolling(window=ma).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))
    colors = ['#FFD700', '#FF8C00', '#FF1493', '#00BFFF', '#8B4513']
    for i, ma in enumerate([2, 6, 20, 60, 180]):
        fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{ma}'], line=dict(width=1.2, color=colors[i]), name=f'{ma}일선'))
    fig.update_layout(xaxis_rangeslider_visible=False, height=450, template="plotly_white", margin=dict(t=30, b=10))
    return fig

# --- [3. 사이드바 및 종목 승인] ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_info(user_input)
    live_p = 0.0
    if ticker:
        live_p = float(yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1])
        st.success(f"✅ {s_name} 승인 완료")
    unit = "원" if market == "KR" else "$"

# --- [4. 메인 화면: 입력값 FIX 로직 적용] ---
st.markdown(f"<div class='main-title'>📈 {s_name} 투자 시뮬레이션</div>", unsafe_allow_html=True)

st.markdown(f"<div class='section-title'>👤 1️⃣ 내 현재 보유 현황 ({unit})</div>", unsafe_allow_html=True)
with st.expander("데이터 입력 (입력값 유지)", expanded=True):
    c1, c2, c3 = st.columns(3)
    # [FIX 핵심] session_state를 사용하여 사용자가 수정한 값을 기억함
    current_avg = c1.number_input(f"현재 내 평단가", value=st.session_state.my_avg if st.session_state.my_avg > 0 else float(live_p), key="avg_input")
    current_qty = c2.number_input("현재 보유 수량 (주)", value=st.session_state.my_qty, key="qty_input")
    now_p = c3.number_input(f"현재 시장가 (실시간)", value=float(live_p))
    
    # 입력된 값을 세션에 저장
    st.session_state.my_avg = current_avg
    st.session_state.my_qty = current_qty

# --- [5. 추가 매수 시나리오] ---
st.divider()
st.markdown(f"<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오 ({unit})</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])
p_min, p_max = float(now_p * 0.1), float(now_p * 3.0)
with cs1:
    buy_p_in = st.number_input(f"추가 매수 가격", min_value=p_min, max_value=p_max, value=float(now_p))
    buy_p = st.slider("가격 미세 조정", p_min, p_max, value=min(max(buy_p_in, p_min), p_max), label_visibility="collapsed")
with cs2:
    buy_q_in = st.number_input("추가 구매 수량 (주)", min_value=0, max_value=100000, value=0)
    buy_q = st.slider("수량 미세 조정", 0, 100000, value=int(buy_q_in), label_visibility="collapsed")
total_buy = buy_p * buy_q
with cs3:
    st.markdown(f"**💰 추가 구매 총액**")
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{total_buy:,.0f}{unit}</h3>", unsafe_allow_html=True)

# --- [6. 분석 결과 및 SUMMARY 표] ---
st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)
total_qty = current_qty + buy_q
total_cost = (current_avg * current_qty) + (buy_p * buy_q)
final_avg = total_cost / total_qty if total_qty > 0 else 0
avg_diff = final_avg - current_avg
aft_rtn = ((now_p - final_avg) / final_avg * 100) if final_avg > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("현재 시장가", f"{now_p:,.2f} {unit}")
m2.metric("예상 평단가", f"{final_avg:,.2f} {unit}", f"{avg_diff:,.2f}", delta_color="inverse")
m3.metric("예상 수익률", f"{aft_rtn:.2f}%")

st.markdown("### 📋 상세 시뮬레이션 요약 (SUMMARY)")
df_res = pd.DataFrame({
    "항목": ["보유 수량", "평균 단가", "총 투자금", "수익 금액", "수익률(%)"],
    "현재 상태": [f"{current_qty:,}주", f"{current_avg:,.2f}", f"{(current_avg*current_qty):,.0f}{unit}", f"{(now_p-current_avg)*current_qty:+,.0f}{unit}", f"{(now_p-current_avg)/current_avg*100 if current_avg>0 else 0:.2f}%"],
    "매수 후 예상": [f"{total_qty:,}주", f"{final_avg:,.2f}", f"{total_cost:,.0f}{unit}", f"{(now_p-final_avg)*total_qty:+,.0f}{unit}", f"{aft_rtn:.2f}%"]
}).set_index("항목")
st.table(df_res.style.applymap(lambda x: 'color: #d32f2f; font-weight: bold;' if '+' in str(x) else ('color: #2e7d32; font-weight: bold;' if '-' in str(x) else ''), subset=pd.IndexSlice[['수익 금액', '수익률(%)'], :]))

# --- [7. 차트 복구] ---
st.markdown("<div class='section-title'>📊 최근 1년 주가 흐름 및 기술적 지표</div>", unsafe_allow_html=True)
chart_fig = get_technical_chart(ticker)
if chart_fig: st.plotly_chart(chart_fig, use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b></div>", unsafe_allow_html=True)