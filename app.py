import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 系統初始化與頁面設定
# ==========================================
st.set_page_config(
    page_title="T100 智力夥伴選股系統 V3.0",
    page_icon="🧠",
    layout="wide"
)

# ==========================================
# 2. 資料來源 (台灣50 - 完整中文主檔)
# ==========================================
tw50_dict = {
    '2330.TW': '台積電', '2317.TW': '鴻海', '2454.TW': '聯發科', '2308.TW': '台達電', 
    '2303.TW': '聯電', '2881.TW': '富邦金', '2882.TW': '國泰金', '2382.TW': '廣達', 
    '2891.TW': '中信金', '2886.TW': '兆豐金', '2884.TW': '玉山金', '2885.TW': '元大金', 
    '2412.TW': '中華電', '2892.TW': '第一金', '1216.TW': '統一', '2880.TW': '華南金', 
    '5880.TW': '合庫金', '2883.TW': '開發金', '2887.TW': '台新金', '2357.TW': '華碩', 
    '3711.TW': '日月光投控', '2327.TW': '國巨', '2395.TW': '研華', '2379.TW': '瑞昱', 
    '2890.TW': '永豐金', '3008.TW': '大立光', '3231.TW': '緯創', '1101.TW': '台泥', 
    '3034.TW': '聯詠', '2002.TW': '中鋼', '2345.TW': '智邦', '3045.TW': '台灣大', 
    '4938.TW': '和碩', '5871.TW': '中租-KY', '2603.TW': '長榮', '2888.TW': '新光金', 
    '2408.TW': '南亞科', '3037.TW': '欣興', '6669.TW': '緯穎', '1303.TW': '南亞', 
    '1301.TW': '台塑', '5876.TW': '上海商銀', '3017.TW': '奇鋐', '1326.TW': '台化', 
    '2912.TW': '統一超', '4904.TW': '遠傳', '2301.TW': '光寶科', '1605.TW': '華新', 
    '1102.TW': '亞泥', '2207.TW': '和泰車', '0050.TW': '元大台灣50'
}

# ==========================================
# 3. 側邊欄：策略控制台
# ==========================================
with st.sidebar:
    st.title("🎛️ 戰術控制台")
    st.info("請選擇本週的操作風格：")
    
    # 策略選擇器
    strategy_mode = st.radio(
        "選擇策略模組：",
        ("🚀 動能爆發 (PE+黃金交叉)", "🛡️ 拉回防守 (牙醫策略)")
    )
    
    st.divider()
    
    if strategy_mode == "🚀 動能爆發 (PE+黃金交叉)":
        st.caption("參數設定 (PE估值)：")
        pe_tech_bull = st.slider("科技股-多頭 PE", 15, 30, 22)
        pe_tech_bear = st.slider("科技股-空頭 PE", 10, 20, 14)
        pe_fin_bull  = st.slider("金融/傳產-多頭 PE", 10, 20, 15)
    else:
        st.caption("參數設定 (支撐判定)：")
        pullback_tolerance = st.slider("容許誤差範圍 (%)", 1, 5, 3)
        st.markdown(f"> 尋找股價回到均線 `{pullback_tolerance}%` 範圍內的股票。")

    run_btn = st.button("🔄 執行全自動掃描", type="primary")

# ==========================================
# 4. 顯示：策略邏輯說明 (SOP)
# ==========================================
st.title(f"📊 T100 顧問級選股系統 V3.0")

if strategy_mode == "🚀 動能爆發 (PE+黃金交叉)":
    st.success("""
    **【當前策略邏輯：進攻型】** 1. **價值濾網：** 股價 < (EPS × 合理PE)，具備 >15% 潛在漲幅。
    2. **趨勢濾網：** 5日均線(MA5) > 20日均線(MA20)，呈現短多排列。
    3. **目標：** 抓出「便宜」且「剛發動」的股票。
    """)
else:
    st.info("""
    **【當前策略邏輯：防守型 (股市牙醫版)】**
    1. **大趨勢確立：** 股價必須在 60日均線(季線) 之上，確保長多格局。
    2. **等待好球帶：** 股價回檔至 20日均線(月線) 附近 (誤差範圍內)。
    3. **風險報酬比：** 進場點離支撐點(MA20)很近，停損空間小，風報比極佳。
    4. **目標：** 不追高，買在「回檔止穩」的安全點。
    """)

# ==========================================
# 5. 核心運算引擎
# ==========================================
def get_pe_params(sector):
    # 根據 UI 設定回傳 PE 參數
    if sector == 'Technology':
        return {'pe_bull': pe_tech_bull, 'pe_bear': pe_tech_bear}
    elif sector == 'Financial Services':
        return {'pe_bull': pe_fin_bull, 'pe_bear': 10}
    else:
        return {'pe_bull': pe_fin_bull, 'pe_bear': 9}

def run_analysis():
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_stocks = len(tw50_dict)
    
    for i, (ticker_id, ch_name) in enumerate(tw50_dict.items()):
        progress = (i + 1) / total_stocks
        progress_bar.progress(progress)
        status_text.text(f"Scanning: {ch_name}...")

        try:
            stock = yf.Ticker(ticker_id)
            info = stock.info
            
            # --- 基礎資料 ---
            sector = info.get('sector', 'Unknown')
            eps_ttm = info.get('trailingEps', 0)
            current_price = info.get('currentPrice', 0)
            
            if current_price == 0: # 防呆
                hist_fast = stock.history(period='1d')
                if not hist_fast.empty:
                    current_price = hist_fast['Close'].iloc[-1]

            # --- 技術指標運算 ---
            hist = stock.history(period="6mo") 
            if len(hist) < 60: continue

            ma_5  = hist['Close'].rolling(window=5).mean().iloc[-1]
            ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] # 月線 (支撐線)
            ma_60 = hist['Close'].rolling(window=60).mean().iloc[-1] # 季線 (生命線)
            
            # --- 策略分流 ---
            action = "觀望"
            detail_msg = ""
            risk_rate = 0.0
            
            # [策略 A] 動能爆發 (原本邏輯)
            if strategy_mode == "🚀 動能爆發 (PE+黃金交叉)":
                is_bull_trend = current_price > ma_60
                is_golden_cross = ma_5 > ma_20
                
                # PE 估值
                if eps_ttm > 0 and '0050' not in ticker_id:
                    pe_params = get_pe_params(sector)
                    target_pe = pe_params['pe_bull'] if is_bull_trend else pe_params['pe_bear']
                    predicted_price = eps_ttm * target_pe
                    gap_rate = (predicted_price - current_price) / current_price
                    
                    if gap_rate > 0.15 and is_golden_cross:
                        action = "★ 強力買進"
                        detail_msg = f"低估 {gap_rate:.1%} + 黃金交叉"
                    elif gap_rate > 0.15:
                        action = "觀察 (趨勢弱)"
                        detail_msg = "便宜但無動能"
                else:
                    detail_msg = "ETF/無EPS" # 0050 不適用 PE 策略

            # [策略 B] 拉回防守 (牙醫策略)
            else:
                # 條件1: 長多趨勢 (股價 > 季線)
                if current_price > ma_60:
                    # 條件2: 計算與月線(MA20)的乖離率
                    # 若為正值，代表股價在月線之上；若負值代表跌破
                    bias_20 = (current_price - ma_20) / ma_20
                    
                    # 邏輯：股價在月線上方，但距離很近 (例如 0% ~ 3%)，視為拉回支撐
                    tolerance = pullback_tolerance / 100
                    
                    if 0 < bias_20 < tolerance:
                        action = "🛡️ 拉回買點"
                        risk_rate = bias_20
                        detail_msg = f"回測月線 (距支撐 {bias_20:.1%})"
                    elif bias_20 < 0:
                        action = "⚠️ 跌破支撐"
                        detail_msg = "已破月線，觀望"
                    else:
                        detail_msg = f"乖離過大 ({bias_20:.1%})"
                else:
                    detail_msg = "空頭趨勢 (股價<季線)"

            # --- 寫入結果 ---
            if "買" in action or "拉回" in action: # 只收集有機會的
                results.append({
                    '代號': ticker_id.replace('.TW', ''),
                    '名稱': ch_name,
                    '現價': round(current_price, 1),
                    '系統建議': action,
                    '判斷理由': detail_msg,
                    '月線(支撐)': round(ma_20, 1),
                    '季線(趨勢)': round(ma_60, 1)
                })

        except Exception as e:
            pass
            
    status_text.text("掃描完成！")
    return pd.DataFrame(results)

# ==========================================
# 6. 主程式執行與報表呈現
# ==========================================

if run_btn:
    df = run_analysis()
    
    if df.empty:
        st.warning("🔍 目前沒有符合此策略標準的股票。 (這也是一種保護，代表現在不適合進場)")
    else:
        # 排序邏輯：
        # 動能策略 -> 依照潛在漲幅 (這裡沒顯示，簡化排序)
        # 拉回策略 -> 依照「判斷理由」中的距離排序 (字串排序勉強可用，或不排)
        
        st.subheader(f"📋 掃描結果：{strategy_mode}")
        
        # 針對「拉回策略」特別顯示重點指標
        if "牙醫" in strategy_mode:
            st.caption("💡 牙醫心法：買在支撐附近，停損設在跌破月線(MA20)時。")
        
        # 樣式設定
        def highlight_row(row):
            return ['background-color: #e6fffa; color: black']*len(row) if "買" in row['系統建議'] else ['']*len(row)

        st.dataframe(
            df.style.apply(highlight_row, axis=1),
            use_container_width=True,
            hide_index=True
        )
else:
    st.write("👈 請點擊側邊欄按鈕開始掃描")
