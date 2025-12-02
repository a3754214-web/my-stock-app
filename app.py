import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 系統初始化 (System Init)
# ==========================================
st.set_page_config(
    page_title="T100 ERP 顧問級選股系統 V4.0",
    page_icon="💎",
    layout="wide"
)

# ==========================================
# 2. 資料來源 (Master Data - 台灣50)
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
# 3. 戰術控制台 (Control Panel)
# ==========================================
with st.sidebar:
    st.title("🎛️ 戰術控制台")
    st.info("請選擇本週的操作模組：")
    
    # 策略選擇器 (新增小豪策略)
    strategy_mode = st.radio(
        "選擇策略模組：",
        ("🛡️ 牙醫策略 (拉回找支撐)", "🐉 小豪策略 (籌碼量縮)", "🚀 動能策略 (PE+黃金交叉)")
    )
    
    st.divider()
    
    # 動態參數調整區
    if "牙醫" in strategy_mode:
        st.caption("🛠️ 牙醫參數 (防守型)")
        pullback_tolerance = st.slider("支撐容許誤差 (%)", 1, 5, 3)
        st.markdown(f"> 尋找回測 **月線(20MA)** `{pullback_tolerance}%` 內的股票。")
        
    elif "小豪" in strategy_mode:
        st.caption("🛠️ 小豪參數 (籌碼型)")
        vol_shrink_ratio = st.slider("量縮標準 (0.7=7成量)", 0.3, 1.0, 0.7)
        st.markdown(f"> 尋找成交量 < **5日均量** `{vol_shrink_ratio}` 倍的股票。")
        st.markdown("> *邏輯：主力鎖碼，散戶不賣，量縮價穩。*")
        
    else: # 動能策略
        st.caption("🛠️ 動能參數 (攻擊型)")
        pe_tech_bull = st.slider("科技股-多頭 PE", 15, 30, 22)
        pe_tech_bear = st.slider("科技股-空頭 PE", 10, 20, 14)
        pe_fin_bull  = st.slider("金融/傳產-多頭 PE", 10, 20, 15)

    run_btn = st.button("🔄 執行全自動掃描", type="primary")

# ==========================================
# 4. 策略邏輯說明卡 (SOP Card)
# ==========================================
st.title(f"📊 T100 顧問級選股系統 V4.0")

if "牙醫" in strategy_mode:
    st.info("""
    **【🛡️ 牙醫策略 SOP】** (來源：股市牙醫心得.pdf)
    1. **大趨勢：** 股價 > 60MA (季線)，確保長多格局。
    2. **進場點：** 股價回檔至 **20MA (月線)** 附近。
    3. **核心精神：** 「買在支撐，停損設在跌破支撐」。不追高，只買回檔。
    """)
elif "小豪" in strategy_mode:
    st.warning("""
    **【🐉 小豪策略 SOP】** (來源：小豪籌碼投資心法.pdf)
    1. **趨勢保護：** 股價 > 60MA (季線)，多頭排列。
    2. **量縮整理：** 今日成交量 明顯低於 5日均量 (代表主力惜售/洗盤)。
    3. **位置：** 股價維持在 5MA 或 10MA 附近震盪，未跌破。
    4. **核心精神：** 「籌碼集中，量縮拉回是買點」。
    """)
else:
    st.success("""
    **【🚀 動能策略 SOP】** (來源：基本面+技術面雙刀流)
    1. **價值濾網：** 股價被低估 (PE Gap > 15%)。
    2. **攻擊訊號：** 5MA 突破 20MA (黃金交叉)。
    3. **核心精神：** 「便宜」且「剛發動」，適合積極操作。
    """)

# ==========================================
# 5. 核心運算引擎 (Calculation Engine)
# ==========================================
def get_pe_params(sector):
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
            
            # 基礎數據
            sector = info.get('sector', 'Unknown')
            eps_ttm = info.get('trailingEps', 0)
            current_price = info.get('currentPrice', 0)
            
            if current_price == 0: 
                hist_fast = stock.history(period='1d')
                if not hist_fast.empty:
                    current_price = hist_fast['Close'].iloc[-1]

            # 技術指標 (抓取足夠資料計算均量)
            hist = stock.history(period="3mo") 
            if len(hist) < 60: continue

            # 價的均線
            ma_5  = hist['Close'].rolling(window=5).mean().iloc[-1]
            ma_10 = hist['Close'].rolling(window=10).mean().iloc[-1]
            ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            ma_60 = hist['Close'].rolling(window=60).mean().iloc[-1]
            
            # 量的均線 (小豪策略專用)
            vol_now = hist['Volume'].iloc[-1]
            vol_ma5 = hist['Volume'].rolling(window=5).mean().iloc[-1]
            
            action = "觀望"
            detail_msg = ""
            
            # ==========================
            # 策略 A: 牙醫策略 (Pullback)
            # ==========================
            if "牙醫" in strategy_mode:
                if current_price > ma_60: # 季線之上
                    bias_20 = (current_price - ma_20) / ma_20 # 乖離率
                    tolerance = pullback_tolerance / 100
                    
                    if 0 < bias_20 < tolerance:
                        action = "🛡️ 拉回買點"
                        detail_msg = f"回測月線 (距支撐 {bias_20:.1%})"
                    elif bias_20 < 0:
                        action = "⚠️ 跌破月線"
                        detail_msg = "支撐已破，觀望"
                    else:
                        detail_msg = f"乖離過大 ({bias_20:.1%})"
                else:
                    detail_msg = "空頭趨勢 (破季線)"

            # ==========================
            # 策略 B: 小豪策略 (Chips/Volume)
            # ==========================
            elif "小豪" in strategy_mode:
                # 1. 趨勢保護：季線之上
                if current_price > ma_60:
                    # 2. 量縮判斷：今日量 < 5日均量 * 係數 (e.g. 0.7)
                    is_vol_shrink = vol_now < (vol_ma5 * vol_shrink_ratio)
                    
                    # 3. 支撐位置：在 5MA 或 10MA 附近 (上下 2% 內)
                    dist_ma5 = abs(current_price - ma_5) / ma_5
                    dist_ma10 = abs(current_price - ma_10) / ma_10
                    is_near_support = dist_ma5 < 0.02 or dist_ma10 < 0.02
                    
                    if is_vol_shrink and is_near_support:
                        action = "🐉 籌碼潛伏"
                        vol_ratio = vol_now / vol_ma5 if vol_ma5 > 0 else 0
                        detail_msg = f"量縮 ({vol_ratio:.1f}倍) + 均線有撐"
                    elif not is_vol_shrink:
                        detail_msg = "成交量未縮"
                    else:
                        detail_msg = "乖離過大/無支撐"
                else:
                    detail_msg = "空頭趨勢"

            # ==========================
            # 策略 C: 動能策略 (Momentum)
            # ==========================
            else:
                is_bull_trend = current_price > ma_60
                is_golden_cross = ma_5 > ma_20
                
                if eps_ttm > 0 and '0050' not in ticker_id:
                    pe_params = get_pe_params(sector)
                    target_pe = pe_params['pe_bull'] if is_bull_trend else pe_params['pe_bear']
                    predicted_price = eps_ttm * target_pe
                    gap_rate = (predicted_price - current_price) / current_price
                    
                    if gap_rate > 0.15 and is_golden_cross:
                        action = "★ 強力買進"
                        detail_msg = f"低估 {gap_rate:.1%} + 黃金交叉"
                    elif gap_rate > 0.15:
                        action = "觀察"
                        detail_msg = "便宜但無動能"
                else:
                    detail_msg = "N/A"

            # --- 彙整結果 ---
            # 只收集符合該策略「買進/潛伏/拉回」條件的，或者顯示觀望
            results.append({
                '代號': ticker_id.replace('.TW', ''),
                '名稱': ch_name,
                '現價': round(current_price, 1),
                '系統建議': action,
                '判斷理由': detail_msg,
                'MA5': round(ma_5, 1),
                'MA20 (月)': round(ma_20, 1),
                'MA60 (季)': round(ma_60, 1)
            })

        except Exception as e:
            pass
            
    status_text.text("掃描完成！")
    return pd.DataFrame(results)

# ==========================================
# 6. 報表呈現 (Report View)
# ==========================================
if run_btn:
    df = run_analysis()
    
    if df.empty:
        st.warning("🔍 掃描完成，但沒有抓到資料，請稍後再試。")
    else:
        # 篩選出重點股票 (不顯示觀望的，除非想看全部)
        # 這裡我們做一個簡單的過濾，把 "買" 或 "潛伏" 的排前面
        
        def sort_priority(row):
            if "買" in row['系統建議'] or "潛伏" in row['系統建議']: return 0
            if "觀察" in row['系統建議']: return 1
            return 2
            
        df['Sort'] = df.apply(sort_priority, axis=1)
        df = df.sort_values(by=['Sort'])
        
        st.subheader(f"📋 掃描結果：{strategy_mode}")
        
        # 樣式：綠色底代表符合策略
        def highlight_row(row):
            is_buy = "買" in row['系統建議'] or "潛伏" in row['系統建議']
            return ['background-color: #e6fffa; color: black']*len(row) if is_buy else ['']*len(row)

        display_cols = ['代號', '名稱', '現價', '系統建議', '判斷理由', 'MA5', 'MA20 (月)', 'MA60 (季)']
        
        st.dataframe(
            df[display_cols].style.apply(highlight_row, axis=1),
            use_container_width=True,
            hide_index=True
        )
else:
    st.write("👈 請點擊側邊欄按鈕開始掃描")
