import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="CHEONGUN AI Quant", layout="wide")

st.markdown("""
    <style>
    /* 수익 색상: 상승(Red), 하락(Green) */
    .pos-val { color: #d32f2f !important; font-weight: bold; } 
    .neg-val { color: #2e7d32 !important; font-weight: bold; } 
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 10px; }
    .disclaimer { font-size: 0.85rem; color: #666666; text-align: center; margin-bottom: 30px; line-height: 1.6; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 25px; margin-bottom: 15px; }
    /* 표 데이터 우측 정렬 */
    td { text-align: right !important; }
    th { text-align: center !important; }
    .result-summary { font-size: 1.1rem; font-weight: 700; margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 10px; border-left: 5px solid #2e7d32; }
    .sidebar-memo { font-size: 0.85rem; color: #2e7d32; font-weight: 600; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 코어 엔진: 데이터 로드 및 차트 로직 ---
@st.cache_data(ttl=3600)
def get_symbol_data(raw_input):
    raw_input = raw_input.strip().upper()
    ticker_out, market, name = None, None, raw_input
    
    # 한국 종목 코드 (숫자 6자리) 처리
    if raw_input.isdigit() and len(raw_input) == 6:
        for suffix in [".KS", ".KQ"]:
            t_obj = yf.Ticker(raw_input + suffix)
            if not t_obj.history(period="1d").empty:
                ticker_out, market = raw_input + suffix, "KR"
                name = t_obj.info.get('longName') or t_obj.info.get('shortName') or raw_input
                # 주요 종목 한글 매핑
                mapping = {"Samsung Electronics Co., Ltd.": "삼성전자", "SK hynix Inc.": "SK하이닉스"}
                name = mapping.get(name, name)
                break
    # 미국 및 기타 해외 티커 처리
    else:
        t_obj = yf.Ticker(raw_input)
        if not t_obj.history(period="1d").empty:
            ticker_out, market = raw_input, "US"
            name = t_obj.info.get('shortName', raw_input)
            
    return ticker_out, market, name

def get_advanced_chart(ticker_symbol):
    # 데이터 로드 (이평선 계산을 위해 2년치)
    df = yf.download(ticker_symbol, period="2y", progress=False, auto_adjust=True)
    if df.empty: return None
    
    # [핵심 수정] 다중 인덱스 컬럼 평탄화 (KeyError 해결)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 이동평균선 계산
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # 최근 1년 데이터 슬라이싱 및 결측치 제거
    df = df.iloc[-252:].copy()
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

    fig = go.Figure()

    # 1. 캔들스틱 차트
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='주가(캔들)', increasing_line_color='#d32f2f', decreasing_line_color='#1976d2'
    ))

    # 2. 이동평균선 레이어 추가
    lines = [('MA5', '#FFD700', '5일선'), ('MA20', '#FF1493', '20일선'), 
             ('MA60', '#00BFFF', '60일선'), ('MA120', '#8B4513', '120일선')]
    for col, color, lbl in lines:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], line=dict(color=color, width=1.3), name=lbl))

    fig.update_layout(
        title=f"최근 1년 주가 흐름 및 이동평균선 분석",
        yaxis_title="가격", xaxis_rangeslider_visible=False,
        height=550, template="plotly_white", hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig

# --- 3. 사이드바: 관심 종목 조회 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    st.markdown("<div class='sidebar-memo'>💡 국장(종목번호) 및 미장(티커) 모든 종목 조회 가능</div>", unsafe_allow_html=True)
    
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_data(user_input)
    
    # 실시간 환율 정보 (미국 주식일 때만 활성화)
    ex_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1] if market == "US" else 1.0
    
    if ticker:
        st.success(f"✅ {s_name} 연동 성공")
        live_p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
    else:
        live_p = 0.0

# --- 4. 메인 화면 구성 ---
st.markdown(f"<div class='main-title'>📈 {s_name} AI 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown(f"<div class='disclaimer'>본 프로그램에서 제공하는 모든 수치는 단순 참고용이며 투자 권유를 목적으로 하지 않습니다.<br>모든 투자 판단의 책임은 투자자 본인에게 있으며, 결과에 대한 법적 책임을 지지 않습니다.</div>", unsafe_allow_html=True)

# 1️⃣ 내 현재 보유 현황
st.markdown("<div class='section-title'>👤 1️⃣ 내 현재 보유 현황</div>", unsafe_allow_html=True)
with st.expander("데이터 입력 (초기 상태)", expanded=True):
    c1, c2, c3 = st.columns(3)
    curr_unit = "원" if market == "KR" else "$"
    current_avg = st.number_input(f"현재 평단가 ({curr_unit})", value=float(live_p))
    current_qty = st.number_input("현재 보유 수량 (주)", value=0)
    now_p = st.number_input(f"현재 시장가 (자동연동/수정가능)", value=float(live_p))

# 2️⃣ 추가 매수 시나리오
st.divider()
st.markdown("<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])
with cs1: buy_p = st.slider("추가 매수 가격", float(now_p*0.1), float(now_p*2.0), float(now_p))
with cs2: buy_q = st.slider("추가 구매 수량 (주)", 0, 5000, 0)
total_buy_amt = buy_p * buy_q
with cs3:
    st.markdown("**💰 예상 투입 금액**")
    val_str = f"${total_buy_amt:,.2f}" if market == "US" else f"{total_buy_amt:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)
    if market == "US": st.caption(f"(약 {total_buy_amt*ex_rate:,.0f}원)")

# --- 5. 차트 시각화 ---
st.divider()
chart_fig = get_advanced_chart(ticker)
if chart_fig:
    st.plotly_chart(chart_fig, use_container_width=True)

# --- 6. 분석 결과 및 데이터 표 ---
st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)

old_cost = current_avg * current_qty
new_cost = total_buy_amt
total_qty_res = current_qty + buy_q
final_avg = (old_cost + new_cost) / total_qty_res if total_qty_res > 0 else 0
avg_diff = final_avg - current_avg

# 수익금 및 수익률 계산
curr_profit = (now_p - current_avg) * current_qty
curr_rtn = (curr_profit / old_cost * 100) if old_cost > 0 else 0
aft_profit = (now_p - final_avg) * total_qty_res
aft_rtn = (aft_profit / (old_cost + new_cost) * 100) if (old_cost + new_cost) > 0 else 0

r1, r2, r3 = st.columns(3)
with r1: st.markdown(f"<p class='bold-text'>실시간 현재가</p><h2>{now_p:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r2: 
    color_p, sign_p, word_p = ("#d32f2f", "▲", "상승") if avg_diff > 0 else ("#2e7d32", "▼", "하락")
    st.markdown(f"<p class='bold-text'>예상 평단가</p><h2>{final_avg:,.2f}{curr_unit}</h2>", unsafe_allow_html=True)
with r3:
    color_r = "#d32f2f" if aft_rtn >= 0 else "#2e7d32"
    st.markdown(f"<p class='bold-text'>예상 수익률</p><h2 style='color:{color_r};'>{aft_rtn:.2f}%</h2>", unsafe_allow_html=True)

# 메트릭 하단 안내 문구
if total_qty_res > 0:
    st.markdown(f"<div class='result-summary'>☞ 본 시뮬레이션 분석 결과 주당 평단가 <span style='color:{color_p};'>{sign_p} {abs(avg_diff):,.2f} {word_p}</span>이 되었습니다.</div>", unsafe_allow_html=True)

# 상세 데이터 표 (우측 정렬 및 조건부 색상)
data_conv = ex_rate if market == 'US' else 1
df_res = pd.DataFrame({
    "항목": ["보유 수량", "평균 단가", "총 투자금(원화환산)", "수익 금액", "수익률(%)"],
    "현재 상태": [
        f"{current_qty:,}주", f"{current_avg:,.2f}", f"{old_cost * data_conv:,.0f}원", 
        f"{curr_profit * data_conv:+,.0f}원", f"{curr_rtn:.2f}%"
    ],
    "매수 후 예상": [
        f"{total_qty_res:,}주", f"{final_avg:,.2f}", f"{(old_cost + new_cost) * data_conv:,.0f}원", 
        f"{aft_profit * data_conv:+,.0f}원", f"{aft_rtn:.2f}%"
    ]
}).set_index("항목")

def apply_color(val):
    if "+" in str(val): return 'color: #d32f2f; font-weight: bold;'
    if "-" in str(val): return 'color: #2e7d32; font-weight: bold;'
    return ''
st.table(df_res.style.applymap(apply_color, subset=pd.IndexSlice[['수익 금액', '수익률(%)'], :]))

# --- 7. AI 인텔리전트 가이드 ---
st.info("📑 **AI 인텔리전트 가이드**")
if total_qty_res == 0:
    st.write("상단의 종목을 조회하고 보유 수량을 입력하시면 AI 퀀트 분석이 시작됩니다.")
elif aft_rtn < 0:
    st.write(f"💡 **AI 분석:** 평단가 회복(ZERO)까지 주가가 {abs(aft_rtn):.2f}% 반등해야 합니다. 차트의 120일선(갈색) 지지 여부를 확인하세요.")
else:
    st.write("🎉 **AI 분석:** 현재 수익 구간입니다! 추가 매수는 수익금 극대화를 위한 '불타기' 전략으로 유효합니다.")

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b><br>© 2025 All Rights Reserved. Powered by AI Quant Intelligence.</div>", unsafe_allow_html=True)