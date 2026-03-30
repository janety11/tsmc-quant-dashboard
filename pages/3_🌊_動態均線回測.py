import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="台積電 AI 交易與回測系統 (動態均線版)", layout="wide")

def main():
    # --- 側邊欄設定 ---
    st.sidebar.title("⚙️ 系統參數")
    # 修正了匯率 step 報錯的問題 (確保 value 是 32.0 浮點數)
    fixed_exchange_rate = st.sidebar.number_input("美元匯率 (USD/TWD)", value=32.0, step=0.1, format="%.2f")
    initial_capital = st.sidebar.number_input("回測初始資金 (USD)", value=10000.0, step=1000.0)
    
    # 💡 新增：滾動平均天數的滑桿
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 策略參數")
    rolling_window = st.sidebar.slider("動態均線天數 (Rolling Window)", min_value=30, max_value=365, value=120, step=10)
    st.sidebar.caption(f"目前設定：以過去 {rolling_window} 天的數據來計算當天的合理溢價區間。")
    
    run_btn = st.sidebar.button("🚀 啟動 AI 分析與回測", type="primary")

    # --- 主畫面 ---
    st.title("💰 台積電 (2330 vs ADR) 動態套利回測系統")
    st.markdown("---")

    if run_btn:
        with st.spinner('正在連線 Yahoo Finance 下載歷史數據並執行回測...'):
            end_date = datetime.now()
            # 為了展示長期效果，這裡預設抓取過去 10 年 (3650天)
            start_date = end_date - timedelta(days=3650)
            
            try:
                df_tw = yf.download('2330.TW', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
                df_us = yf.download('TSM', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
            except Exception as e:
                st.error(f"數據下載失敗: {e}")
                return

            if hasattr(df_tw.index, 'tz'): df_tw.index = df_tw.index.tz_localize(None)
            if hasattr(df_us.index, 'tz'): df_us.index = df_us.index.tz_localize(None)
            
            df = pd.concat([df_tw, df_us], axis=1)
            df.columns = ['2330_TW', 'TSM_US']
            df = df.ffill().dropna()

            if df.empty:
                st.error("錯誤：抓不到數據")
                return

            # --- 核心計算 (計算溢價率) ---
            df['ADR_Implied_TWD'] = (df['TSM_US'] * fixed_exchange_rate) / 5
            df['Premium_Rate'] = ((df['ADR_Implied_TWD'] - df['2330_TW']) / df['2330_TW']) * 100

            # ==========================================
            # 💡 核心升級：計算「滾動」的平均與標準差
            # ==========================================
            # 使用 .rolling(window).mean() 來計算移動平均
            df['Rolling_Mean'] = df['Premium_Rate'].rolling(window=rolling_window).mean()
            df['Rolling_Std']  = df['Premium_Rate'].rolling(window=rolling_window).std()
            
            # 動態的買賣紅綠燈線
            df['Buy_Threshold'] = df['Rolling_Mean'] - df['Rolling_Std']
            df['Sell_Threshold'] = df['Rolling_Mean'] + df['Rolling_Std']

            current_premium = df['Premium_Rate'].iloc[-1]
            current_buy_line = df['Buy_Threshold'].iloc[-1]
            current_sell_line = df['Sell_Threshold'].iloc[-1]

            # ==========================================
            # 歷史回測引擎 (Backtesting Engine)
            # ==========================================
            capital = initial_capital
            position = 0
            trades_count = 0
            win_count = 0
            equity_curve = []
            buy_price = 0

            for i in range(len(df)):
                daily_premium = df['Premium_Rate'].iloc[i]
                daily_price = df['TSM_US'].iloc[i]
                
                # 取得當天的動態紅綠燈線
                buy_line = df['Buy_Threshold'].iloc[i]
                sell_line = df['Sell_Threshold'].iloc[i]

                # 如果前幾天還沒有足夠的數據算出平均線 (NaN)，就跳過不交易
                if pd.isna(buy_line) or pd.isna(sell_line):
                    equity_curve.append(capital if position == 0 else position * daily_price)
                    continue

                # 買進條件：跌破「當天的」便宜線
                if daily_premium < buy_line and position == 0:
                    position = capital / daily_price
                    capital = 0
                    buy_price = daily_price

                # 賣出條件：突破「當天的」昂貴線
                elif daily_premium > sell_line and position > 0:
                    capital = position * daily_price
                    if daily_price > buy_price:
                        win_count += 1
                    trades_count += 1
                    position = 0

                current_equity = capital if position == 0 else position * daily_price
                equity_curve.append(current_equity)

            df['Equity'] = equity_curve
            
            final_equity = df['Equity'].iloc[-1]
            total_return_pct = ((final_equity / initial_capital) - 1) * 100
            win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0

            # --- UI 顯示區塊 ---
            st.subheader("📢 當前市場狀態 (基於動態均線)")
            col1, col2, col3 = st.columns(3)
            col1.metric("目前溢價率", f"{current_premium:.2f}%")
            col2.metric("當前便宜買進線", f"{current_buy_line:.2f}%")
            col3.metric("當前昂貴賣出線", f"{current_sell_line:.2f}%")

            st.markdown("---")
            
            st.subheader(f"📈 策略回測績效 (過去10年, 滾動天數={rolling_window}天)")
            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            rcol1.metric("最終總資產", f"${final_equity:,.2f}", f"{total_return_pct:.2f}%")
            rcol2.metric("總報酬率", f"{total_return_pct:.2f}%")
            rcol3.metric("總交易次數", f"{trades_count} 次")
            rcol4.metric("交易勝率", f"{win_rate:.1f}%")

            # --- 繪圖區塊 ---
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
            
            # 上圖：這一次我們畫的是「曲線」而不是水平直線
            ax1.plot(df.index, df['Premium_Rate'], color='#333', linewidth=1.5, label='Premium Rate')
            ax1.plot(df.index, df['Rolling_Mean'], color='green', linestyle='--', alpha=0.7, label=f'{rolling_window}d Average')
            ax1.plot(df.index, df['Sell_Threshold'], color='red', linestyle=':', label='Sell Line')
            ax1.plot(df.index, df['Buy_Threshold'], color='blue', linestyle=':', label='Buy Line')
            
            # 填滿動態區間
            ax1.fill_between(df.index, df['Sell_Threshold'], max(df['Premium_Rate'].dropna())+5, color='red', alpha=0.1)
            ax1.fill_between(df.index, min(df['Premium_Rate'].dropna())-5, df['Buy_Threshold'], color='green', alpha=0.1)
            
            ax1.set_title("TSMC Premium Spread with Rolling Bands", fontsize=12)
            ax1.set_ylabel("Premium (%)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 下圖：資金曲線
            ax2.plot(df.index, df['Equity'], color='#1f77b4', linewidth=2)
            ax2.fill_between(df.index, initial_capital, df['Equity'], where=(df['Equity'] >= initial_capital), color='green', alpha=0.3)
            ax2.fill_between(df.index, initial_capital, df['Equity'], where=(df['Equity'] < initial_capital), color='red', alpha=0.3)
            ax2.axhline(y=initial_capital, color='black', linestyle='--', alpha=0.5)
            ax2.set_title("Strategy Equity Curve", fontsize=12)
            ax2.set_ylabel("Capital (USD)")
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            st.pyplot(fig)

    else:
        st.info("👈 請點擊左側按鈕開始分析")

if __name__ == "__main__":
    main()