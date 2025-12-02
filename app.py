import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 頁面設定 (UI Layout)
# ==========================================
st.set_page_config(
    page_title="T100 智力夥伴選股系統",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 T100 ERP 顧問級選股儀表板")
st.markdown("### 核心邏輯：基本面 (PE估值) + 技術面 (MA黃金交叉)")

# ==========================================
# 2. 側邊欄參數設定
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統參數設定")
    st.info("這裡可以動態調整採購策略，不需改Code。")
    
    st.subheader("估值標準 (PE Ratio)")
    pe_tech_bull = st.slider("科技股-多頭 PE", 15, 30, 22)
    pe_tech_bear = st.slider("科技股-空頭 PE", 10, 20, 14)
    pe_fin_bull  = st.slider("金融/傳產-多頭 PE", 10, 20, 15)
    
    run_btn = st.button("🔄 執行全自動掃描", type="primary")

# ==========================================
# 3. 資料來源 (台灣50 - 中文主檔對照表)
# ==========================================
# 這是你的「料件主檔」，確保名稱顯示為中文
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
# 4. 運算函數 (Logic Core)
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
    
    # 遍歷 Dictionary
    for i, (ticker_id, ch_name) in enumerate(tw50_dict.items()):
        # 更新進度條
        progress = (i + 1) / total_stocks
        progress_bar.progress(progress)
        status_text.text(f"正在掃描: {ch_name} ({ticker_id})...")

        try:
            stock = yf.Ticker(ticker_id)
            info = stock.info
            
            sector = info.get('sector', 'Unknown')
            eps_ttm = info.get('trailingEps', 0)
            current_price = info.get('currentPrice', 0)
            
            # 防呆：補抓收盤價
            if current_price == 0:
                hist_fast = stock.history(period='1d')
                if not hist_fast.empty:
                    current_price = hist_fast['Close'].iloc[-1]

            # 技術面運算 (需 60 天以上資料)
            hist = stock.history(period="6mo") 
            if len(hist) < 60: continue

            ma_5  = hist['Close'].rolling(window=5).mean().iloc[-1]
            ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            ma_60 = hist['Close'].rolling(window=60).mean().iloc[-1]
            
            is_bull_trend = current_price > ma_60
            trend_str = "多頭" if is_bull_trend else "空頭"
            is_golden_cross = ma_5 > ma_20
            tech_signal = "🔥黃金交叉" if is_golden_cross else "☁️整理中"

            # 估值運算
            pe_params = get_pe_params(sector)
            target_pe = pe_params['pe_bull'] if is_bull_trend else pe_params['pe_bear']
            predicted_price = eps_ttm * target_pe
            
            # 決策訊號與例外管理
            action = "觀望"
            gap_rate = -999 # 排序用預設值
            pred_display = "-"
            gap_display = "N/A"

            # 針對 ETF 或虧損股 (預測價<=0) 的處理
            if predicted_price <= 0:
                 gap_display = "N/A (ETF/虧損)"
                 action = "參考趨勢"
            elif current_price > 0:
                gap_rate = (predicted_price - current_price) / current_price
                gap_display = f"{gap_rate:.1%}"
                pred_display = round(predicted_price, 1)
                
                # 策略核心：基本面 + 技術面
                if gap_rate > 0.15 and is_golden_cross:
                    action = "★ 強力買進"
                elif gap_rate > 0.15 and not is_golden_cross:
                    action = "觀察 (低估但弱)"
                elif gap_rate > 0.05 and is_golden_cross:
                    action = "買進 (動能強)"
                elif gap_rate < -0.15:
                    action = "避開 (高估)"

            results.append({
                '代號': ticker_id.replace('.TW', ''),
                '名稱': ch_name, # 強制使用中文名稱
                '現價': round(current_price, 1),
                '建議': action,
                '技術': tech_signal,
                '預測價': pred_display,
                '潛在漲幅': gap_rate, # 用於排序
                '漲幅顯示': gap_display
            })

        except Exception as e:
            pass
            
    status_text.text("掃描完成！")
    return pd.DataFrame(results)

# ==========================================
# 5. 主程式執行與顯示 (Main Execution)
# ==========================================

if run_btn:
    df = run_analysis()
    
    # 資料處理：排序 (強力買進優先 -> 潛在漲幅高優先)
    def sort_score(row):
        if "強力買進" in row['建議']: return 3
        if "買進" in row['建議'] and "強力" not in row['建議']: return 2
        if "觀察" in row['建議']: return 1
        return 0
    
    df['SortScore'] = df.apply(sort_score, axis=1)
    df = df.sort_values(by=['SortScore', '潛在漲幅'], ascending=[False, False])
    
    # --- 顯示區塊 1: 重點關注 (Top Picks) ---
    st.subheader("🏆 本週首選 (強力買進)")
    top_picks = df[df['建議'].str.contains("強力買進")]
    
    if not top_picks.empty:
        for index, row in top_picks.iterrows():
            col1, col2, col3 = st.columns(3)
            col1.metric("股票", f"{row['名稱']} ({row['代號']})")
            col2.metric("現價", f"{row['現價']}", f"{row['漲幅顯示']} (空間)")
            col3.metric("狀態", row['技術'])
            st.divider()
    else:
        st.warning("目前沒有符合「強力買進」雙重條件的標的，建議觀望。")

    # --- 顯示區塊 2: 完整報表 ---
    st.subheader("📊 完整掃描清單")
    
    # 樣式美化
    def color_survived(val):
        color = ''
        if '強力買進' in str(val):
            color = 'background-color: #90EE90; color: black' # 淺綠
        elif '避開' in str(val):
            color = 'background-color: #FFB6C1; color: black' # 淺紅
        return color

    display_cols = ['代號', '名稱', '現價', '建議', '技術', '預測價', '漲幅顯示']
    
    st.dataframe(
        df[display_cols].style.applymap(color_survived, subset=['建議']),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("👈 請點擊側邊欄的按鈕開始掃描")
