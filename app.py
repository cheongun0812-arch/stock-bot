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
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 10px; }
    .disclaimer { font-size: 0.85rem; color: #666666; text-align: center; margin-bottom: 30px; line-height: 1.6; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 25px; margin-bottom: 15px; }
    td { text-align: right !important; }
    th { text-align: center !important; }
    .result-summary { font-size: 1.1rem; font-weight: 700; margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #2e7d32; }
    .sidebar-memo { font-size: 0.85rem; color: #2e7d32; font-weight: 600; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 코어 엔진: 데이터 로드 및 차트 로직 ---
@st.cache_data(ttl=3600)
def get_symbol_data(raw_input):
    if not raw_input: return None, None, "None"
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

def get_advanced_chart(ticker_symbol):
    # [에러 방지] ticker_symbol이 유효한 문자열인지 확인
    if not ticker_symbol or not isinstance(ticker_symbol, str):
        return None

    df = yf.download(ticker_symbol, period="2y", progress=False, auto_adjust=True)
    if df.empty: return None
    
    # 다중 인덱스 평탄화
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 이평선 계산
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    df = df.iloc[-252:].copy()
    available_cols = [c for c in ['Open', 'High', 'Low', 'Close'] if c in df.columns]
    df = df.dropna(subset=available_cols)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='주가(캔들)', increasing_line_color='#d32f2f', decreasing_line_color='#1976d2'
    ))

    lines = [('MA5', '#FFD700', '5일선'), ('MA20', '#FF1493', '20일선'), 
             ('MA60', '#00BFFF', '60일선'), ('MA120', '#8B4513', '120일선')]
    for col, color, lbl in lines:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], line=dict(color=color, width=1.3), name=lbl))

    fig.update_layout(
        yaxis_title="가격", xaxis_rangeslider_visible=False, height=550, 
        template="plotly_white", hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig

# --- 3. 사이드바 및 실시간 가격 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    st.markdown("<div class='sidebar-memo'>💡 국장(종목번호) 및 미장(티커) 모든 종목 조회 가능</div>", unsafe_allow_html=True)
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_data(user_input)
    
    ex_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1] if market == "US" else 1.0
    
    live_p = 0.0
    if ticker:
        st.success(f"✅ {s_name} 연동 성공")
        live_p = float(yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1])

# --- 4. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} AI 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown(f"<div class='disclaimer'>본 프로그램의 수치는 참고용이며 투자 결정의 책임은 본인에게 있습니다.</div>", unsafe_allow_html=True)

# 1️⃣ 내 현재 보유 현황
st.markdown("<div class='section-title'>👤 1️⃣ 내 현재 보유 현황</div>", unsafe_allow_html=True)
with st.expander("데이터 입력", expanded=True):
    c1, c2, c3 = st.columns(3)
    curr_unit = "원" if market == "KR" else "$"
    current_avg = st.number_input(f"현재 평단가 ({curr_unit})", value=live_p if live_p > 0 else 0.0)
    current_qty = st.number_input("현재 보유 수량 (주)", value=0)
    now_p = st.number_input(f"현재 시장가 (자동연동/수정)", value=live_p if live_p > 0 else 0.0)

# 2️⃣ 추가 매수 시나리오 (동기화 & 안전 장치 적용)
st.divider()
st.markdown("<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오</div>", unsafe_allow_html=True)

safe_now_p = now_p if now_p > 0 else 1.0
p_min, p_max = float(safe_now_p * 0.1), float(safe_now_p * 3.0)
q_min, q_max = 0.0, 10000.0

cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])

with cs1:
    buy_p_input = st.number_input(f"추가 매수 가격 ({curr_unit})", min_value=p_min, max_value=p_max, value=float(safe_now_p))
    # 클리핑 로직으로 에러 원천 차단
    safe_p_val = min(max(buy_p_input, p_min), p_max)
    buy_p = st.slider("가격 미세 조정", p_min, p_max, value=safe_p_val, label_visibility="collapsed")

with cs2:
    buy_q_input = st.number_input("추가 구매 수량 (주)", min_value=q_min, max_value=q_max, value=0.0)
    safe_q_val = min(max(buy_q_input, q_min), q_max)
    buy_q = st.slider("수량 미세 조정", q_min, q_max, value=safe_q_val, label_visibility="collapsed")

total_buy_amt = buy_p * buy_q
with cs3:
    st.markdown("**💰 예상 투입 금액**")
    val_str = f"${total_buy_amt:,.2f}" if market == "US" else f"{total_buy_amt:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)

# --- 5. 차트 및 분석 결과 ---
st.divider()
if ticker:
    chart_fig = get_advanced_chart(ticker)
    if chart_fig: st.plotly_chart(chart_fig, use_container_width=True)

# 시뮬레이션 계산
old_cost, new_cost = current_avg * current_qty, total_buy_amt
total_qty_res = current_qty + buy_q
final_avg = (old_cost + new_cost) / total_qty_res if total_qty_res > 0 else 0
avg_diff = final_avg - current_avg
aft_profit = (now_p - final_avg) * total_qty_res
aft_rtn = (aft_profit / (old_cost + new_cost) * 100) if (old_cost + new_cost) > 0 else 0

st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)
r1, r2, r3 = st.columns(3)
with r1: st.markdown(f"<p class='bold-text'>실시간 현재가</p><h2>{now_p:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r2: 
    cp, sp, wp = ("#d32f2f", "▲", "상승") if avg_diff > 0 else ("#2e7d32", "▼", "하락")
    st.markdown(f"<p class='bold-text'>예상 평단가</p><h2>{final_avg:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r3:
    cr = "#d32f2f" if aft_rtn >= 0 else "#2e7d32"
    st.markdown(f"<p class='bold-text'>예상 수익률</p><h2 style='color:{cr};'>{aft_rtn:.2f}%</h2>", unsafe_allow_html=True)

if total_qty_res > 0:
    st.markdown(f"<div class='result-summary'>☞ 분석 결과: 평단가가 <span style='color:{cp};'>{sp} {abs(avg_diff):,.2f} {wp}</span>이 되었습니다.</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b><br>© 2025 All Rights Reserved.</div>", unsafe_allow_html=True)
