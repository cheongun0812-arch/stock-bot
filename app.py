import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 페이지 설정 및 스타일 ---
st.set_page_config(page_title="CHEONGUN AI Quant", layout="wide")

st.markdown("""
    <style>
    .pos-val { color: #d32f2f !important; font-weight: bold; } 
    .neg-val { color: #2e7d32 !important; font-weight: bold; } 
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 10px; }
    .disclaimer { font-size: 0.9rem; color: #666666; text-align: center; margin-bottom: 30px; line-height: 1.6; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 25px; margin-bottom: 15px; }
    td { text-align: right !important; }
    th { text-align: center !important; }
    .result-summary { font-size: 1.1rem; font-weight: 700; margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #2e7d32; }
    /* 사이드바 메모 스타일 */
    .sidebar-memo { font-size: 0.85rem; color: #2e7d32; font-weight: 600; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 엔진: 데이터 및 차트 로직 ---
@st.cache_data(ttl=3600)
def get_symbol_data(raw_input):
    raw_input = raw_input.strip().upper()
    ticker_out, market, name = None, None, raw_input
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            hist = t_obj.history(period="1d")
            if not hist.empty:
                ticker_out, market = raw_input + suffix, "KR"
                name = t_obj.info.get('longName') or t_obj.info.get('shortName') or raw_input
                mapping = {"Samsung Electronics Co., Ltd.": "삼성전자", "SK hynix Inc.": "SK하이닉스"}
                name = mapping.get(name, name)
                break
    else:
        t_obj = yf.Ticker(raw_input)
        hist = t_obj.history(period="1d")
        if not hist.empty:
            ticker_out, market, name = raw_input, "US", t_obj.info.get('shortName', raw_input)
    return ticker_out, market, name

def get_advanced_chart(ticker_symbol):
    # 데이터 로드 (이평선 계산을 위해 2년치)
    df = yf.download(ticker_symbol, period="2y", progress=False)
    if df.empty: return None
    
    # 이동평균선 계산
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # 최근 1년(약 252 거래일) 데이터 슬라이싱 및 결측치 제거
    df = df.iloc[-252:].copy()
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

    fig = go.Figure()

    # 1. 캔들스틱 차트 (가시성 최적화)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='주가(캔들)',
        increasing_line_color='#d32f2f', # 상승 빨강
        decreasing_line_color='#1976d2'  # 하락 파랑
    ))

    # 2. 이동평균선 추가
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#FFD700', width=1.2), name='5일선'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#FF1493', width=1.5), name='20일선'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#00BFFF', width=1.8), name='60일선'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='#8B4513', width=2.2), name='120일선'))

    fig.update_layout(
        title=f"최근 1년 주가 흐름 분석 (이동평균선 포함)",
        yaxis_title="가격",
        xaxis_rangeslider_visible=False,
        height=600,
        template="plotly_white",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # 주말 공백 제거
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig

# --- 2. 사이드바: 종목 조회 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    # [요청 사항] 국장/미장 안내 메모 추가
    st.markdown("<div class='sidebar-memo'>💡 국장(종목번호) 및 미장(티커) 모든 종목 조회 가능</div>", unsafe_allow_html=True)
    
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_data(user_input)
    
    if ticker:
        st.success(f"✅ {s_name} 연동 성공")
        live_p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
    else:
        live_p = 0.0

# --- 3. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} AI 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown(f"<div class='disclaimer'>본 프로그램에서 제공하는 정보는 단순 참고용이며, 투자 권유를 목적으로 하지 않습니다.<br>모든 투자 판단의 책임은 투자자 본인에게 있으며, 결과에 대한 법적 책임을 지지 않습니다.</div>", unsafe_allow_html=True)

# 1️⃣ 내 현재 보유 현황
st.markdown("<div class='section-title'>👤 1️⃣ 내 현재 보유 현황</div>", unsafe_allow_html=True)
with st.expander("입력창 열기/닫기", expanded=True):
    c1, c2, c3 = st.columns(3)
    curr_unit = "원" if market == "KR" else "$"
    current_avg = st.number_input(f"현재 평단가 ({curr_unit})", value=float(live_p))
    current_qty = st.number_input("현재 보유 수량 (주)", value=0)
    now_p = st.number_input(f"현재 시장가 (자동연동)", value=float(live_p))

# 2️⃣ 추가 매수 시나리오
st.divider()
st.markdown("<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])
with cs1: buy_p = st.slider("추가 매수 가격", float(now_p*0.1), float(now_p*2.0), float(now_p))
with cs2: buy_q = st.slider("추가 매수 수량 (주)", 0, 5000, 0)
total_buy_amt = buy_p * buy_q
with cs3:
    st.markdown("**💰 예상 투입 금액**")
    val_str = f"${total_buy_amt:,.2f}" if market == "US" else f"{total_buy_amt:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)

# --- 4. 차트 표시 ---
st.divider()
chart_fig = get_advanced_chart(ticker)
if chart_fig:
    st.plotly_chart(chart_fig, use_container_width=True)

# --- 5. 분석 결과 ---
st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)
old_cost, new_cost = current_avg * current_qty, buy_p * buy_q
total_qty = current_qty + buy_q
final_avg = (old_cost + new_cost) / total_qty if total_qty > 0 else 0
avg_diff = final_avg - current_avg
aft_profit = (now_p - final_avg) * total_qty
aft_rtn = (aft_profit / (old_cost + new_cost) * 100) if (old_cost + new_cost) > 0 else 0

r1, r2, r3 = st.columns(3)
with r1: st.markdown(f"<p class='bold-text'>실시간 현재가</p><h2>{now_p:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r2: st.markdown(f"<p class='bold-text'>예상 평단가</p><h2>{final_avg:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r3:
    r_color = "#d32f2f" if aft_rtn >= 0 else "#2e7d32"
    st.markdown(f"<p class='bold-text'>예상 수익률</p><h2 style='color:{r_color};'>{aft_rtn:.2f}%</h2>", unsafe_allow_html=True)

if total_qty > 0:
    d_color, d_sign, d_word = ("#d32f2f", "▲", "상승") if avg_diff > 0 else ("#2e7d32", "▼", "하락")
    st.markdown(f"<div class='result-summary'>☞ 분석 결과: 평단가가 <span style='color:{d_color};'>{d_sign} {abs(avg_diff):,.2f} {d_word}</span>이 되었습니다.</div>", unsafe_allow_html=True)

# 데이터 표 및 푸터
st.info("📑 **AI 인텔리전트 가이드**")
st.write("차트의 이동평균선 흐름과 현재가의 위치를 비교하여 투자 비중을 조절하시기 바랍니다.")
st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b><br>© 2025 All Rights Reserved. Powered by AI Quant Intelligence.</div>", unsafe_allow_html=True)