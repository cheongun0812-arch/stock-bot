import streamlit as st
import yfinance as yf
import pandas as pd

# --- [원본 스타일 유지] ---
st.set_page_config(page_title="CHEONGUN Quant Simulator", layout="wide")

st.markdown("""
    <style>
    .pos-val { color: #d32f2f; font-weight: bold; } 
    .neg-val { color: #2e7d32; font-weight: bold; } 
    .bold-text { font-weight: 800 !important; font-size: 1.2rem; }
    .main-title { font-size: 2.5rem; font-weight: 900; text-align: center; margin-bottom: 30px; }
    .section-title { font-size: 1.75rem !important; font-weight: 700 !important; margin-top: 20px; margin-bottom: 15px; }
    td { text-align: right !important; }
    th { text-align: center !important; }
    .guide-msg { font-size: 1rem; font-weight: 600; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 데이터 엔진 ---
@st.cache_data(ttl=3600)
def get_symbol_info(raw_input):
    if not raw_input: return None, "KR", "None"
    raw_input = raw_input.strip().upper()
    ticker_out, market, name = None, "KR", raw_input
    
    try:
        if raw_input.isdigit() and len(raw_input) == 6:
            # 한국 주식은 .KS(코스피) 또는 .KQ(코스닥) 중 데이터가 있는 쪽을 찾음
            for suffix in [".KS", ".KQ"]:
                t_obj = yf.Ticker(raw_input + suffix)
                # 데이터 확인 로직 강화: history 대신 fast_info나 info 활용 가능
                if t_obj.history(period="5d").empty == False: 
                    ticker_out, market = raw_input + suffix, "KR"
                    name = t_obj.info.get('shortName') or t_obj.info.get('longName') or raw_input
                    break
        else:
            # 미국 주식
            t_obj = yf.Ticker(raw_input)
            if t_obj.history(period="5d").empty == False:
                ticker_out, market = raw_input, "US"
                name = t_obj.info.get('shortName', raw_input)
    except Exception as e:
        st.error(f"데이터 연동 중 오류 발생: {e}")
        return None, "KR", "None"
        
    return ticker_out, market, name

# --- 2. 사이드바 조회 ---
with st.sidebar:
    st.header("🔍 관심 종목 조회")
    user_input = st.text_input("종목 번호 또는 티커 입력", value="005930")
    ticker, market, s_name = get_symbol_info(user_input)
    live_p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1] if ticker else 0.0
    # 단위 결정
    unit = "원" if market == "KR" else "$"

# --- 3. 메인 화면 ---
st.markdown(f"<div class='main-title'>📈 {s_name} 투자 시뮬레이션</div>", unsafe_allow_html=True)

st.markdown(f"<div class='section-title'>👤 1️⃣ 내 현재 보유 현황 ({unit})</div>", unsafe_allow_html=True)
with st.expander("데이터 입력", expanded=True):
    c1, c2, c3 = st.columns(3)
    current_avg = st.number_input(f"현재 내 평단가 ({unit})", value=float(live_p))
    current_qty = st.number_input("현재 보유 수량 (주)", value=0)
    now_p = st.number_input(f"현재 시장가 ({unit})", value=float(live_p))

# --- 4. 추가 매수 시나리오 (양방향 동기화 반영) ---
st.divider()
st.markdown(f"<div class='section-title'>🟦 2️⃣ 추가 매수 시나리오 ({unit})</div>", unsafe_allow_html=True)
cs1, cs2, cs3 = st.columns([1.5, 1.5, 1.2])

# 안전 범위 설정
p_min, p_max = float(now_p * 0.1), float(now_p * 3.0)
if p_min == p_max: p_max += 100.0

with cs1:
    # 타이핑 박스
    buy_p_in = st.number_input(f"추가 매수 가격 ({unit})", min_value=p_min, max_value=p_max, value=float(now_p))
    # 슬라이더 (타이핑 값과 동기화)
    buy_p = st.slider("가격 미세 조정", p_min, p_max, value=min(max(buy_p_in, p_min), p_max), label_visibility="collapsed")

with cs2:
    # 타이핑 박스
    buy_q_in = st.number_input("추가 구매 수량 (주)", min_value=0, max_value=10000, value=0)
    # 슬라이더 (타이핑 값과 동기화)
    buy_q = st.slider("수량 미세 조정", 0, 10000, value=int(buy_q_in), label_visibility="collapsed")

total_buy_amt = buy_p * buy_q
with cs3:
    st.markdown(f"**💰 추가 구매 총액 ({unit})**")
    val_str = f"${total_buy_amt:,.2f}" if market == "US" else f"{total_buy_amt:,.0f}원"
    st.markdown(f"<h3 style='color: #2e7d32; text-align: right;'>{val_str}</h3>", unsafe_allow_html=True)

# --- 5. 분석 결과 ---
st.divider()
st.markdown("<div class='section-title'>🔍 시뮬레이션 분석 결과</div>", unsafe_allow_html=True)

total_qty = current_qty + buy_q
total_cost = (current_avg * current_qty) + (buy_p * buy_q)
final_avg = total_cost / total_qty if total_qty > 0 else 0
avg_diff = final_avg - current_avg
aft_rtn = ((now_p - final_avg) / final_avg * 100) if final_avg > 0 else 0

r1, r2, r3 = st.columns(3)
with r1:
    cur_val = f"${now_p:,.2f}" if market == "US" else f"{int(now_p):,}원"
    st.markdown(f"<p class='bold-text'>실시간 현재가</p><h2 class='bold-text'>{cur_val}</h2>", unsafe_allow_html=True)

with r2:
    avg_val = f"${final_avg:,.2f}" if market == "US" else f"{int(final_avg):,}원"
    color, sign, msg = ("#d32f2f", "▲", "🔺 평단가 상승") if avg_diff > 0 else ("#2e7d32", "▼", "🔹 평단가 하락")
    st.markdown(f"<p class='bold-text'>예상 평단가</p><h2 class='bold-text'>{avg_val}</h2>"
                f"<p style='color:{color}; text-align: right; margin:0;'>{sign} {abs(avg_diff):,.2f}</p>"
                f"<p class='guide-msg' style='color:{color}; text-align: right;'>{msg}</p>", unsafe_allow_html=True)

with r3:
    rtn_color = "#d32f2f" if aft_rtn >= 0 else "#2e7d32"
    st.markdown(f"<p class='bold-text'>예상 수익률</p><h2 style='color:{rtn_color}; font-weight:800;'>{aft_rtn:.2f}%</h2>", unsafe_allow_html=True)

# --- 6. 상세 데이터 표 ---
df_res = pd.DataFrame({
    "항목": ["보유 수량", "평균 단가", "수익 금액", "수익률(%)"],
    "현재 상태": [f"{current_qty:,}주", f"{current_avg:,.2f}", f"{(now_p-current_avg)*current_qty:+,.0f}", f"{(now_p-current_avg)/current_avg*100 if current_avg>0 else 0:.2f}%"],
    "추가 매수 후 예상": [f"{total_qty:,}주", f"{final_avg:,.2f}", f"{(now_p-final_avg)*total_qty:+,.0f}", f"{aft_rtn:.2f}%"]
}).set_index("항목")

st.table(df_res.style.applymap(lambda x: 'color: #d32f2f; font-weight: bold;' if '+' in str(x) else ('color: #2e7d32; font-weight: bold;' if '-' in str(x) else ''), subset=pd.IndexSlice[['수익 금액', '수익률(%)'], :]))

st.markdown("---")
st.markdown("<div style='text-align: right; color: gray; font-size: 0.8rem;'>Designed by <b>CHEONGUN</b></div>", unsafe_allow_html=True)