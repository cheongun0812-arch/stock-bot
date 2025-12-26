import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- [1. 어제 만족하셨던 그 스타일 그대로 복구] ---
st.set_page_config(page_title="CHEONGUN Quant Simulator", layout="wide")

# 아빠의 입력값을 고정하는 메모리 설정
if 'my_avg' not in st.session_state: st.session_state.my_avg = 0.0
if 'my_qty' not in st.session_state: st.session_state.my_qty = 0
if 'buy_p_fix' not in st.session_state: st.session_state.buy_p_fix = 0.0

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 5px; }
    .disclaimer { font-size: 0.85rem; color: #666666; text-align: center; margin-bottom: 25px; line-height: 1.6; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 20px; margin-bottom: 10px; }
    .result-summary { 
        font-size: 1.15rem; font-weight: 700; margin-top: -5px; margin-bottom: 15px;
        padding: 15px; background-color: #f8f9fa; border-radius: 10px; border-left: 8px solid #2e7d32; 
    }
    td { text-align: right !important; }
    th { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- [2. 엔진: 데이터 로드 및 차트 복구] ---
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
                raw_name = t_obj.info.get('longName') or t_obj.info.get('shortName') or raw_input
                mapping = {"Samsung Electronics Co., Ltd.": "삼성전자", "SK hynix Inc.": "SK하이닉스"}
                name = mapping.get(raw_name, raw_name)
                break
    else:
        t_obj = yf.Ticker(raw_input)
        if not t_obj.history(period="5d").empty:
            ticker_out, market = raw_input, "US"
            name = t_obj.info.get('shortName', raw_input)
    return ticker_out, market, name

def get_advanced_chart(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="1y", progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        # 아빠가 요청하신 이평선: 2, 6, 20, 60, 180일
        for ma in [2, 6, 20, 60, 180]:
            df[f'MA{ma}'] = df['Close'].rolling(window=ma).mean()
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))
        clrs = ['#FFD700', '#FF8C00', '#FF1493', '#00BFFF', '#8B4513']
        for i, ma in enumerate([2, 6, 20, 60, 180]):
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{ma}'], line=dict(width=1.2, color=clrs[i]), name=f'{ma}일선'))
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, template="plotly_white", margin=dict(t=30, b=10))
        return fig
    except: return None

# --- [3. 사이드바 조회] ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    u_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_info(u_input)
    live_p = 0.0
    if ticker:
        live_p = float(yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1])
        st.success(f"✅ {s_name} 승인 완료")
    unit = "원" if market == "KR" else "$"

# --- [4. 메인 화면: 한글 제목 및 법적 문구] ---
st.markdown(f"<div class='main-title'>📈 {s_name} 투자 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown("<div class='disclaimer'>본 프로그램은 참고용이며 모든 투자 결과에 대한 법적 책임은 사용자 본인에게 있습니다.</div>", unsafe_allow_html=True)

# 1️⃣ 현재 보유 현황 (입력값 고정)
st.markdown(f"<div class='section-title'>👤 1️⃣ 내 현재 보유 현황 ({unit})</div>", unsafe_allow_html=True)
with st.expander("데이터 입력 (수정 시 고정됩니다)", expanded=True):
    c1, c2, c3 = st.columns(3)
    current_avg = c1.number_input(f"현재 내 평단가", value=st.session_state.my_avg if st.session_state.my_avg > 0 else float(live_p))
    current_qty = c2.number_input("현재 보유 수량 (주)", value=st.session_state.my_qty)
    now_p = c3.number_input(f"현재 시장가 (실시간)", value=float(live_p))
    st.session_state.my_avg, st.session_state.my_qty = current_avg, current_qty

# 2️⃣ 추가 매수 시나리오 (타이핑 기능 반영)
st.divider()
st.markdown(f"<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오 ({unit})</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])
p_min, p_max = float(now_p * 0.1), float(now_p * 3.0)

with cs1:
    buy_p_in = st.number_input(f"추가 매수 가격", min_value=p_min, max_value=p_max, value=st.session_state.buy_p_fix if st.session_state.buy_p_fix > 0 else float(now_p))
    buy_p = st.slider("가격 조정", p_min, p_max, value=min(max(buy_p_in, p_min), p_max), label_visibility="collapsed")
    st.session_state.buy_p_fix = buy_p 
with cs2:
    buy_q_in = st.number_input("추가 구매 수량 (주)", min_value=0, max_value=100000, value=0)
    buy_q = st.slider("수량 조정", 0, 100000, value=int(buy_q_in), label_visibility="collapsed")
total_buy = buy_p * buy_q
with cs3:
    st.markdown(f"**💰 추가 구매 총액**")
    val_str = f"${total_buy:,.2f}" if market == "US" else f"{total_buy:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)

# 3️⃣ 분석 결과 (안내 문구 및 요약 표)
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

# [복구] 하단 안내 문구 (색상 적용)
if total_qty > 0:
    color, sign, status = ("#d32f2f", "▲", "상승") if avg_diff > 0 else ("#1976d2", "▼", "하락")
    st.markdown(f"""
    <div class='result-summary'>
        ☞ <b>시뮬레이션 분석 결과:</b><br>
        추가 매수 시 예상 평단가는 기존 대비 <span style='color:{color};'>{sign} {abs(avg_diff):,.2f} {unit} {status}</span> 되었습니다.<br>
        최종 주당 평균 가액은 <b>{final_avg:,.2f} {unit}</b>입니다.
    </div>
    """, unsafe_allow_html=True)

# [복구] 상세 SUMMARY 표
st.markdown("### 📋 상세 시뮬레이션 요약 (SUMMARY)")
df_res = pd.DataFrame({
    "항목": ["보유 수량", "평균 단가", "수익 금액", "수익률(%)"],
    "현재 상태": [f"{current_qty:,}주", f"{current_avg:,.2f}", f"{(now_p-current_avg)*current_qty:+,.0f}{unit}", f"{(now_p-current_avg)/current_avg*100 if current_avg>0 else 0:.2f}%"],
    "매수 후 예상": [f"{total_qty:,}주", f"{final_avg:,.2f}", f"{(now_p-final_avg)*total_qty:+,.0f}{unit}", f"{aft_rtn:.2f}%"]
}).set_index("항목")
st.table(df_res.style.applymap(lambda x: 'color: #d32f2f; font-weight: bold;' if '+' in str(x) else ('color: #1976d2; font-weight: bold;' if '-' in str(x) else ''), subset=pd.IndexSlice[['수익 금액', '수익률(%)'], :]))

# 4️⃣ [복구] 입양 보냈던 차트 제자리로!
st.markdown("<div class='section-title'>📊 최근 1년 주가 흐름 및 기술적 지표</div>", unsafe_allow_html=True)
chart = get_advanced_chart(ticker)
if chart: st.plotly_chart(chart, use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b></div>", unsafe_allow_html=True)