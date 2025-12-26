import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. 페이지 테마 및 스타일 ---
st.set_page_config(page_title="CHEONGUN AI Quant Master", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; color: #1E1E1E; margin-bottom: 10px; }
    .disclaimer { font-size: 0.85rem; color: #666666; text-align: center; margin-bottom: 30px; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 25px; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
    td { text-align: right !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 엔진 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker, period="2y"):
    df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- 3. 백테스팅 엔진 (물타기 전략 분석) ---
def run_backtest(df, drop_threshold, buy_amount_ratio=1.0):
    """
    drop_threshold: 매수 타점 (예: -0.1은 고점 대비 10% 하락 시 매수)
    buy_amount_ratio: 고점 대비 하락 시 기존 보유 수량만큼 추가 매수 (1:1 물타기)
    """
    initial_price = df['Close'].iloc[0]
    holdings = 100 # 초기 100주 가정
    avg_price = initial_price
    total_invested = initial_price * holdings
    
    peak_price = initial_price
    buy_count = 0
    escape_date = None
    
    for date, row in df.iterrows():
        curr_price = row['Close']
        if curr_price > peak_price:
            peak_price = curr_price
        
        # 물타기 조건 확인 (고점 대비 drop_threshold 이하로 떨어졌을 때)
        if curr_price <= peak_price * (1 + drop_threshold):
            # 추가 매수 실행
            add_qty = holdings * buy_amount_ratio
            total_invested += curr_price * add_qty
            holdings += add_qty
            avg_price = total_invested / holdings
            buy_count += 1
            peak_price = curr_price # 매수 후 기준점 갱신
            
        # 탈출 조건 확인 (수익률이 0% 이상으로 돌아왔을 때)
        if curr_price >= avg_price and buy_count > 0:
            escape_date = date
            break
            
    duration = (escape_date - df.index[0]).days if escape_date else "미탈출"
    final_return = ((df['Close'].iloc[-1] - avg_price) / avg_price * 100)
    
    return buy_count, duration, final_return, avg_price

# --- 4. 사이드바 및 UI ---
with st.sidebar:
    st.header("🔍 종목 및 전략 설정")
    ticker_input = st.text_input("종목 번호 또는 티커", value="005930")
    st.caption("💡 국장(005930), 미장(AAPL) 모두 지원")
    
    strategy_pct = st.selectbox("물타기 진입 구간 설정", [-0.05, -0.10, -0.20], format_func=lambda x: f"고점 대비 {int(x*100)}% 하락 시")
    
    ticker_final = ticker_input.strip().upper()
    if ticker_final.isdigit(): ticker_final += ".KS"
    
    df = get_stock_data(ticker_final)
    live_p = df['Close'].iloc[-1] if not df.empty else 0.0

# --- 5. 메인 레이아웃 ---
st.markdown(f"<div class='main-title'>📊 {ticker_input} AI 전략 백테스팅</div>", unsafe_allow_html=True)
st.markdown("<div class='disclaimer'>본 시뮬레이션은 과거 데이터를 기반으로 하며 미래 수익을 보장하지 않습니다.</div>", unsafe_allow_html=True)

if not df.empty:
    # 차트 시각화
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='종가', line=dict(color='#1f77b4')))
    fig.update_layout(title="최근 주가 추이", height=400, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # 백테스팅 실행
    b_count, b_duration, b_return, b_avg = run_backtest(df, strategy_pct)

    st.markdown("<div class='section-title'>🔍 전략 분석 결과 (Backtest)</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 물타기 횟수", f"{b_count}회")
    c2.metric("탈출 소요 기간", f"{b_duration}일")
    c3.metric("최종 예상 수익률", f"{b_return:.2f}%", delta=f"{b_return:.2f}%")
    c4.metric("최종 예상 평단가", f"{b_avg:,.0f}원")

    # 실시간 시뮬레이터 (사용자 입력)
    st.divider()
    st.markdown("<div class='section-title'>👤 실시간 물타기 시뮬레이터</div>", unsafe_allow_html=True)
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        my_avg = st.number_input("나의 현재 평단가", value=float(live_p * 1.1))
        my_qty = st.number_input("보유 수량", value=100)
    with col_in2:
        add_p = st.slider("추가 매수 가격", float(live_p*0.5), float(live_p*1.5), float(live_p))
        add_q = st.slider("추가 매수 수량", 0, 1000, 100)

    # 계산 결과 표
    new_avg = ((my_avg * my_qty) + (add_p * add_q)) / (my_qty + add_q)
    res_df = pd.DataFrame({
        "항목": ["보유 수량", "평균 단가", "수익률(%)"],
        "현재": [f"{my_qty:,}주", f"{my_avg:,.0f}원", f"{(live_p-my_avg)/my_avg*100:.2f}%"],
        "매수 후": [f"{my_qty+add_q:,}주", f"{new_avg:,.0f}원", f"{(live_p-new_avg)/new_avg*100:.2f}%"]
    }).set_index("항목")
    st.table(res_df)

    st.info(f"📑 **AI 인텔리전트 가이드**: 선택하신 {int(strategy_pct*100)}% 하락 전략은 과거 데이터 기준 탈출까지 평균 {b_duration}일이 소요되었습니다.")

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray;'>Designed by <b>CHEONGUN</b> | Powered by AI Quant</div>", unsafe_allow_html=True)