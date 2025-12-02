import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 頁面設定 (UI Layout)
# ==========================================
st.set_page_config(
    page_title="T100 智力夥伴選股系統",
    page_icon="📈",
    layout="wide" # 寬版配置，適合看報表
)

st.title("🚀 T100 ERP 顧問級選股儀表板")
st.markdown("### 核心邏輯：基本面 (PE估值) + 技術面 (MA黃金交叉)")

# ==========================================
# 2. 側邊欄參數設定 (Control Panel)
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統參數設定")
    st.info("這裡可以動態調整採購策略，不需改Code。")
    
    # 動態調整 PE 參數
    st.subheader("估值標準 (PE Ratio)")
    pe_tech_bull = st.slider("科技股-多頭 PE", 15, 30, 22)
    pe_tech_bear = st.slider("科技股-空頭 PE", 10, 20, 14)
    pe_fin_bull  = st.slider("金融/傳產-多頭 PE", 10, 20, 15)
    
    # 執行按鈕
    run_btn = st.button("🔄 執行全自動掃描", type="primary")

# ==========================================
# 3. 資料來源 (台灣50)
# ==========================================
tw50_tickers = [
    '2330.TW', '2317.TW', '2454.TW', '2308.TW', '2303.TW', '2881.TW', '2882.TW', 
    '2382.TW', '2891.TW', '2886.TW', '2884.TW', '2885.TW', '2412.TW', '2892.TW', 
    '1216.TW', '2880.TW', '5880.TW', '2883.TW', '2887.TW', '2357.TW', '3711.TW', 
    '2327.TW', '2395.TW', '2379.TW', '2890.TW', '3008.TW', '3231.TW', '1101.TW', 
    '3034.TW', '2002.TW', '2345.TW', '3045.TW', '4938.TW', '5871.TW', '2603.TW', 
    '2888.TW', '2408.TW', '3037.TW', '6669.TW', '1303.TW', '1301.TW', '5876.TW', 
    '3017.TW', '1326.TW', '2912.TW', '4904.TW', '2301.TW', '1605.TW', '1102.TW',
    '2207.TW'
]

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
    
    total_stocks = len(tw50_tickers)
    
    for i, ticker_id in enumerate(tw50_tickers):
        # 更新進度條
        progress = (i + 1) / total_stocks
        progress_bar.progress(progress)
        status_text.text(f"正在掃描: {ticker_id} ({i+1}/{total_stocks})...")

        try:
            stock = yf.Ticker(ticker_id)
            info = stock.info
            
            sector = info.get('sector', 'Unknown')
            name = info.get('longName', ticker_id)
            eps_ttm = info.get('trailingEps', 0)
            current_price = info.get('currentPrice', 0)
            
            if current_price == 0:
                hist_fast = stock.history(period='1d')
                if not hist_fast.empty:
                    current_price = hist_fast['Close'].iloc[-1]

            # 技術面運算
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
            
            # 決策訊號
            action = "觀望"
            gap_rate = -999 # 排序用預設值

            if predicted_price > 0 and current_price > 0:
                gap_rate = (predicted_price - current_price) / current_price
                
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
                '名稱': name, # 雖然yfinance英文居多，但有的會有中文
                '現價': round(current_price, 1),
                '建議': action,
                '技術': tech_signal,
                '預測價': round(predicted_price, 1) if predicted_price > 0 else "-",
                '潛在漲幅': gap_rate,
                '漲幅顯示': f"{gap_rate:.1%}" if gap_rate != -999 else "N/A"
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
    
    # 資料處理：排序
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
            # 使用 Metric 卡片顯示，手機上看很漂亮
            col1, col2, col3 = st.columns(3)
            col1.metric("股票", f"{row['代號']}")
            col2.metric("現價", f"{row['現價']}", f"{row['漲幅顯示']} (空間)")
            col3.metric("狀態", row['技術'])
            st.divider()
    else:
        st.warning("目前沒有符合「強力買進」雙重條件的標的，建議觀望。")

    # --- 顯示區塊 2: 完整報表 ---
    st.subheader("📊 完整掃描清單")
    
    # 對 dataframe 做樣式美化 (Highlight)
    def color_survived(val):
        color = 'white'
        if '強力買進' in str(val):
            color = '#90EE90' # 淺綠色
        elif '避開' in str(val):
            color = '#FFB6C1' # 淺紅色
        return f'background-color: {color}; color: black'

    display_cols = ['代號', '現價', '建議', '技術', '預測價', '漲幅顯示']
    st.dataframe(df[display_cols].style.applymap(color_survived, subset=['建議']), use_container_width=True)

else:
    st.info("👈 請點擊側邊欄的按鈕開始掃描")