import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 1. 設定網頁標題與排版
st.set_page_config(page_title="台積電 AI 交易訊號", layout="wide")

def main():
    # --- 側邊欄設定 ---
    st.sidebar.title("⚙️ 參數設定")
    fixed_exchange_rate = st.sidebar.number_input("美元匯率 (USD/TWD)", value=31.5, step=0.1, format="%.2f")
    st.sidebar.caption("調整匯率可觀察溢價率的敏感度變化")
    
    run_btn = st.sidebar.button("🚀 啟動 AI 分析", type="primary")

    # --- 主畫面 ---
    st.title("💰 台積電 (2330 vs ADR) 智能套利系統")
    st.markdown("---")

    if run_btn:
        with st.spinner('正在連線 Yahoo Finance 取得最新報價...'):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            try:
                # 乾淨俐落的下載數據，不再需要 session 救援
                df_tw = yf.download('2330.TW', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
                df_us = yf.download('TSM', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
            except Exception as e:
                st.error(f"數據下載失敗: {e}")
                return

            # 數據清洗
            if hasattr(df_tw.index, 'tz'): df_tw.index = df_tw.index.tz_localize(None)
            if hasattr(df_us.index, 'tz'): df_us.index = df_us.index.tz_localize(None)
            
            df = pd.concat([df_tw, df_us], axis=1)
            df.columns = ['2330_TW', 'TSM_US']
            df = df.ffill().dropna()

            if df.empty:
                st.error("錯誤：抓不到數據")
                return

            # --- 核心計算 ---
            df['ADR_Implied_TWD'] = (df['TSM_US'] * fixed_exchange_rate) / 5
            df['Premium_Rate'] = ((df['ADR_Implied_TWD'] - df['2330_TW']) / df['2330_TW']) * 100

            # 計算統計指標
            current_premium = df['Premium_Rate'].iloc[-1]
            mean_val = df['Premium_Rate'].mean()
            std_val = df['Premium_Rate'].std()
            
            # 定義買賣區間
            buy_threshold = mean_val - std_val
            sell_threshold = mean_val + std_val

            # --- 顯示結果 ---
            
            # 第一區：儀表板
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("目前溢價率", f"{current_premium:.2f}%", delta=f"{current_premium-mean_val:.2f}%")
            col2.metric("平均水準", f"{mean_val:.2f}%")
            col3.metric("合理區間 (下限)", f"{buy_threshold:.2f}%")
            col4.metric("合理區間 (上限)", f"{sell_threshold:.2f}%")

            # 第二區：交易建議
            st.subheader("📢 交易策略建議")
            
            if current_premium < 0:
                st.error("🔥🔥 強力買進訊號 (STRONG BUY)")
                st.markdown("#### 🚨 ADR 出現極罕見「折價」！這是無風險套利機會，建議全力買進 ADR。")
            elif current_premium < buy_threshold:
                st.success("🟢 買進訊號 (BUY)")
                st.markdown(f"#### ADR 溢價率低於 {buy_threshold:.2f}%，相對台股便宜，適合分批佈局。")
            elif current_premium > sell_threshold:
                st.warning("🔴 賣出訊號 (SELL)")
                st.markdown(f"#### ADR 溢價率高於 {sell_threshold:.2f}%，價格過熱，建議獲利了結。")
            else:
                st.info("⚪ 觀望持有 (HOLD)")
                st.markdown("#### 目前價格在合理區間波動，建議多看少做。")

            # 第三區：趨勢圖
            st.subheader("📊 溢價率趨勢圖 (布林通道概念)")
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(df.index, df['Premium_Rate'], label='Premium %', color='#333', linewidth=1.5)
            ax.axhline(y=mean_val, color='green', linestyle='--', alpha=0.7, label='Average')
            ax.axhline(y=sell_threshold, color='red', linestyle=':', label='Overvalued (Sell)')
            ax.axhline(y=buy_threshold, color='blue', linestyle=':', label='Undervalued (Buy)')
            
            # 填色
            ax.fill_between(df.index, sell_threshold, max(df['Premium_Rate'])+5, color='red', alpha=0.1)
            ax.fill_between(df.index, min(df['Premium_Rate'])-5, buy_threshold, color='green', alpha=0.1)
            ax.scatter(df.index[-1], current_premium, color='orange', s=150, zorder=5, edgecolors='black', label='Current')

            ax.set_title(f"TSMC Arbitrage Spread (FX={fixed_exchange_rate})", fontsize=14)
            ax.set_ylabel("Premium (%)")
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            
            st.pyplot(fig)

    else:
        st.info("👈 請點擊左側 sidebar 的「啟動 AI 分析」按鈕開始")

if __name__ == "__main__":
    main()