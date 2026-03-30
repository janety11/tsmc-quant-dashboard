import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 1. 設定網頁
st.set_page_config(page_title="台積電 AI 交易與回測系統", layout="wide")

def main():
    # --- 側邊欄設定 ---
    st.sidebar.title("⚙️ 系統參數")
    fixed_exchange_rate = st.sidebar.number_input("美元匯率 (USD/TWD)", value=32.0, step=0.1, format="%.2f")
    initial_capital = st.sidebar.number_input("回測初始資金 (USD)", value=10000, step=1000)
    
    run_btn = st.sidebar.button("🚀 啟動 AI 分析與回測", type="primary")

    # --- 主畫面 ---
    st.title("💰 台積電 (2330 vs ADR) 智能套利與回測系統")
    st.markdown("---")

    if run_btn:
        with st.spinner('正在連線 Yahoo Finance 下載歷史數據並執行回測...'):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=3650)
            
            try:
                # 下載數據
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

            # --- 核心計算 (訊號產生) ---
            df['ADR_Implied_TWD'] = (df['TSM_US'] * fixed_exchange_rate) / 5
            df['Premium_Rate'] = ((df['ADR_Implied_TWD'] - df['2330_TW']) / df['2330_TW']) * 100

            mean_val = df['Premium_Rate'].mean()
            std_val = df['Premium_Rate'].std()
            buy_threshold = mean_val - std_val
            sell_threshold = mean_val + std_val

            current_premium = df['Premium_Rate'].iloc[-1]

            # ==========================================
            # 💡 新增功能：歷史回測引擎 (Backtesting Engine)
            # ==========================================
            capital = initial_capital
            position = 0  # 0代表空手，大於0代表持有股數
            trades_count = 0
            win_count = 0
            equity_curve = []
            buy_price = 0

            # 迴圈模擬每一天的交易
            for i in range(len(df)):
                daily_premium = df['Premium_Rate'].iloc[i]
                daily_price = df['TSM_US'].iloc[i] # 這裡我們簡化為操作 ADR

                # 買進條件：溢價率跌破便宜線，且目前空手
                if daily_premium < buy_threshold and position == 0:
                    position = capital / daily_price
                    capital = 0
                    buy_price = daily_price

                # 賣出條件：溢價率突破昂貴線，且目前持有部位
                elif daily_premium > sell_threshold and position > 0:
                    capital = position * daily_price
                    if daily_price > buy_price:
                        win_count += 1
                    trades_count += 1
                    position = 0

                # 紀錄每天的總資產 (現金 + 股票市值)
                current_equity = capital if position == 0 else position * daily_price
                equity_curve.append(current_equity)

            df['Equity'] = equity_curve
            
            # 計算回測績效指標
            final_equity = df['Equity'].iloc[-1]
            total_return_pct = ((final_equity / initial_capital) - 1) * 100
            win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0

            # ==========================================
            # UI 顯示區塊
            # ==========================================
            
            st.subheader("📢 當前市場狀態")
            col1, col2, col3 = st.columns(3)
            col1.metric("目前溢價率", f"{current_premium:.2f}%")
            col2.metric("便宜買進線", f"{buy_threshold:.2f}%")
            col3.metric("昂貴賣出線", f"{sell_threshold:.2f}%")

            st.markdown("---")
            
            # 顯示回測結果
            st.subheader("📈 策略回測績效 (過去十年)")
            st.caption(f"回測邏輯：當溢價率跌入綠區買進 TSM ADR，進入紅區全數賣出。初始資金：${initial_capital} USD")
            
            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            rcol1.metric("最終總資產", f"${final_equity:,.2f}", f"{total_return_pct:.2f}%")
            rcol2.metric("總報酬率", f"{total_return_pct:.2f}%")
            rcol3.metric("總交易次數", f"{trades_count} 次")
            rcol4.metric("交易勝率", f"{win_rate:.1f}%")

            # 畫圖：分成上下兩張圖
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
            
            # 上圖：溢價率與紅綠燈區間
            ax1.plot(df.index, df['Premium_Rate'], color='#333', linewidth=1.5)
            ax1.axhline(y=mean_val, color='green', linestyle='--', alpha=0.5)
            ax1.axhline(y=sell_threshold, color='red', linestyle=':')
            ax1.axhline(y=buy_threshold, color='blue', linestyle=':')
            ax1.fill_between(df.index, sell_threshold, max(df['Premium_Rate'])+5, color='red', alpha=0.1)
            ax1.fill_between(df.index, min(df['Premium_Rate'])-5, buy_threshold, color='green', alpha=0.1)
            ax1.set_title("TSMC Premium Spread Signal", fontsize=12)
            ax1.set_ylabel("Premium (%)")
            ax1.grid(True, alpha=0.3)

            # 下圖：資金成長曲線 (Equity Curve)
            ax2.plot(df.index, df['Equity'], color='#1f77b4', linewidth=2)
            ax2.fill_between(df.index, initial_capital, df['Equity'], where=(df['Equity'] >= initial_capital), color='green', alpha=0.3)
            ax2.fill_between(df.index, initial_capital, df['Equity'], where=(df['Equity'] < initial_capital), color='red', alpha=0.3)
            ax2.axhline(y=initial_capital, color='black', linestyle='--', alpha=0.5)
            ax2.set_title("Strategy Equity Curve (Capital Growth)", fontsize=12)
            ax2.set_ylabel("Capital (USD)")
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            st.pyplot(fig)

    else:
        st.info("👈 請點擊左側按鈕開始分析")

if __name__ == "__main__":
    main()