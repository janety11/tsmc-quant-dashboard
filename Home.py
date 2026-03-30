import streamlit as st

st.set_page_config(
    page_title="YCY 量化交易終端機",
    page_icon="🏦",
    layout="centered"
)

st.title("🏦 歡迎來到 YCY 量化交易終端機")
st.markdown("---")
st.markdown("""
### 這是你的專屬台積電 ADR 套利分析中心 🚀

請點擊左側導覽列，切換不同的分析模組：

* **📊 基礎套利系統**：每日盤前必看！快速確認今天的溢價率紅綠燈與無風險套利機會。
* **📈 靜態回測系統**：以過去一年的固定平均線，驗證紅綠燈策略的歷史勝率。
* **🌊 動態均線回測**：(進階版) 採用滾動移動平均線 (Rolling Window)，不偷看未來數據的真實壓力測試。

*開發者：YCY | 版本：v1.0*
""")