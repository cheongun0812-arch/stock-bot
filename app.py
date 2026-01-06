import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. UI 및 테마 설정
st.set_page_config(page_title="QuantMaster v3.0", layout="wide")

st.markdown("""
    <style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #2E7D32; border-bottom: 3px solid #2E7D32; padding-bottom: 10px; }
    .metric-container { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 로드 및 전처리 (한국/미국 시장 지원)
@st.cache_data(ttl=3600)
def fetch_data(ticker):
    try:
        # 한국 종목 코드(6자리 숫자)인 경우 처리
        if ticker.isdigit() and len(ticker) == 6:
            # 유가증권(.KS) 우선 시도 후 코스닥(.KQ) 시도
            for suffix in [".KS", ".KQ"]:
                data = yf.download(ticker + suffix, period="2y")
                if not data.empty: return data, ticker + suffix
        else:
            data = yf.download(ticker, period="2y")
            if not data.empty: return data, ticker
        return None, None
    except Exception as e:
        return None, None

# 3. 백테스팅 핵심 로직 (물타기 시나리오)
def run_backtest(df, levels, multipliers, initial_invest):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 초기 설정 (첫 거래일에 진입했다고 가정)
    entry_price = df['Close'].iloc[0]
    qty = initial_invest / entry_price
    total_spent = initial_invest
    peak_price = entry_price
    
    buy_history = []
    is_escaped = False
    escape_date = None

    for date, row in df.iterrows():
        curr_price = row['Close']
        if curr_price > peak_price: peak_price = curr_price
        
        drawdown = (curr_price - peak_price) / peak_price
        avg_price = total_spent / qty

        # 탈출 체크 (현재가가 평단가보다 높으면 탈출)
        if curr_price >= avg_price and len(buy_history) > 0:
            is_escaped = True
            escape_date = date
            break

        # 물타기 체크 (설정된 하락 구간 도달 시)
        for i, (drop, mult) in enumerate(zip(levels, multipliers)):
            # 이미 해당 레벨에서 샀는지 확인하는 간단한 로직 (중복 매수 방지)
            if drawdown <= drop and len(buy_history) == i:
                add_cash = initial_invest * mult # 초기 투자금의 N배수 매수
                qty += add_cash / curr_price
                total_spent += add_cash
                buy_history.append({'date': date, 'price': curr_price, 'drop': f"{drop*100}%"})
                peak_price = curr_price # 매수 후 기준점 재설정 (전략적 판단)

    return {
        "is_escaped": is_escaped,
        "escape_date": escape_date,
        "final_avg": total_spent / qty,
        "buy_history": buy_history,
        "final_return": ((df['Close'].iloc[-1] / (total_spent / qty)) - 1) * 100
    }

# 4. Streamlit 메인 화면 구현
st.markdown("<div class='main-header'>📈 Ultimate Quant Averaging Simulator</div>", unsafe_allow_html=True)
st.write("세계 최고의 전략 엔진으로 당신의 탈출 시나리오를 검증하세요.")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 시뮬레이션 설정")
    ticker = st.text_input("종목 코드 (AAPL or 005930)", "005930")
    init_cash = st.number_input("초기 투자금 (단위: 원/$)", value=1000000, step=100000)
    
    st.divider()
    st.subheader("📍 물타기 구간 (%)")
    l1 = st.slider("1차 낙폭", -15, -1, -5) / 100
    l2 = st.slider("2차 낙폭", -30, -10, -15) / 100
    l3 = st.slider("3차 낙폭", -50, -20, -30) / 100
    
    st.subheader("💰 추가 매수 비중 (배수)")
    m1 = st.number_input("1차 매수 (배)", value=1.0)
    m2 = st.number_input("2차 매수 (배)", value=1.5)
    m3 = st.number_input("3차 매수 (배)", value=2.0)

# 실행 및 시각화
raw_df, final_ticker = fetch_data(ticker)

if raw_df is not None:
    res = run_backtest(raw_df, [l1, l2, l3], [m1, m2, m3], init_cash)
    
    # 상단 요약 지표
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("최종 평단가", f"{res['final_avg']:,.2f}")
    with c2:
        status = "✅ 탈출 성공" if res['is_escaped'] else "⏳ 진행 중"
        st.metric("상태", status)
    with c3:
        duration = (res['escape_date'] - raw_df.index[0]).days if res['is_escaped'] else "N/A"
        st.metric("탈출 소요 기간", f"{duration} 일")

    # 차트 시각화
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=raw_df.index, y=raw_df['Close'], name="주가", line=dict(color='#1f77b4')))
    fig.add_hline(y=res['final_avg'], line_dash="dash", line_color="red", annotation_text="목표 평단가")
    
    # 매수 지점 표시
    for b in res['buy_history']:
        fig.add_annotation(x=b['date'], y=b['price'], text=f"매수({b['drop']})", showarrow=True, arrowhead=1, bgcolor="orange")
    
    fig.update_layout(title=f"{final_ticker} 전략 백테스팅", height=500, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # 상세 내역
    with st.expander("📝 상세 매수 로그 확인"):
        st.table(pd.DataFrame(res['buy_history']))
else:
    st.error("종목을 찾을 수 없습니다. 티커를 정확히 입력해 주세요.")
