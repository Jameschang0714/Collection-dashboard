# **催收績效儀表板專案總結報告**

文件版本： 8.0

最後更新日期： 2025年8月14日

專案負責人： James, VP, Chailease Royal Finance Plc.

## **1\. 專案戰略目標 (Strategic Objective)**

本專案的核心戰略目標，是將原始、分散的每日通話紀錄，轉化為一個能夠提供即時、可行動管理洞察的**動態戰情中心 (Dynamic Command Center)**。此儀表板旨在賦能管理層，透過數據驅動的方式，精準掌握團隊與個人的績效表現與行為模式，從而優化資源分配、提升營運效率，並最終實現業務目標。

## **2\. 核心系統架構 (Core Architecture)**

本專案採用了現代化的「**程式碼與數據分離**」雲端架構，確保系統的可擴展性、安全性與可維護性。

* **數據倉儲層 (Data Warehouse):** 位於 **Google Drive**，專門儲存超過 100MB 的大型核心資料集 (consolidated\_report.csv)。  
* **程式碼儲存庫 (Code Repository):** 位於 **GitHub** (Collection-dashboard)，採用 Git 進行版本控制，僅存放輕量的應用程式程式碼、設定檔與輔助文件。  
* **商業智慧與執行層 (BI & Runtime):** 部署於 **Streamlit Community Cloud**，負責執行儀表板應用。此層透過安全的服務帳號憑證 (GCP Service Account)，以 **Google 官方核心 API** (google-api-python-client) 直接與數據倉儲層進行通訊，實現高效、穩定的數據調用。  
* **開發維護流程 (Dev/Prod Workflow):** 建立了一套**雙軌制**的開發流程。所有新功能首先在 dashboard\_local.py（本地開發版）上進行開發與驗證，確保核心邏輯無誤後，再將更新同步至 dashboard\_cloud.py（雲端生產版），並透過 Git 推送至雲端進行部署。

## **3\. 版本演進與功能迭代日誌 (Version & Feature Log)**

### **V1-V3: 基礎建設與分析深化**

* 實現了核心數據的整合、每日/每月績效報告的視覺化，並深化了多個分析維度，包括催員行為分析與時點分析。

### **V4: 從績效觀測到戰略賦能**

* **V4.0-V4.4 \- 引入【催員行為與高績效人員比較】模組**: 將儀表板從「績效觀測」升級為「模式識別」，賦予管理者自定義績效標竿群組、進行戰略模擬的能力。  
* **V4.5-V4.7 \- 架構升級：雲端數據整合**: 成功將大型數據集從本地遷移至 Google Drive，並建立了初步的雲端數據接口。

### **V5: 雙軌制架構與本地端穩定化 (Dual-Track Architecture & Local Stabilization)**

* **V5.0 \- 戰略轉向：本地優先原則 (Strategic Pivot: Local-First Principle)**: 在雲端部署遭遇環境挑戰後，果斷採取「先求穩、再求遠」的策略。建立了一個完全在本地運行的版本 (dashboard\_local.py)，該版本直接讀取本地 CSV 檔案，用於快速、無干擾地驗證所有核心業務邏輯與視覺化功能。  
* **V5.1 \- 建立開發維護流程 (Establishing Dev/Prod Workflow)**: 正式確立了**開發與生產環境分離**的最佳實踐。建立了 dashboard\_cloud.py 作為雲端生產版的專用腳本，並定義了標準作業程序：所有新功能必須先在本地版 (dashboard\_local.py) 驗證成功，才能將程式碼同步至雲端版 (dashboard\_cloud.py)。

### **V6 & V7: 雲端架構最終定版 (Finalized Cloud Architecture)**

* **V6.0 \- 雲端部署與環境除錯 (Cloud Deployment & Environment Debugging)**: 在部署 dashboard\_cloud.py 的過程中，遭遇了由第三方函式庫 (gdown) 在 Streamlit Cloud 特定執行環境下引發的、頑固的版本衝突問題。此挑戰暴露了依賴非官方中介函式庫在生產環境中的潛在風險。  
* **V7.0 \- 架構最終升級：採用 Google 官方核心 API (Final Architecture Upgrade: Adopting Official Google Core API)**:  
  * **戰略決策**: 為徹底根除不可控的第三方依賴風險，決定放棄 gdown，將數據接口直接升級為 **Google 官方的 API 客戶端函式庫** (google-api-python-client)。  
  * **實現**:  
    * 更新 requirements.txt，移除 gdown 並加入 google-api-python-client 與 google-auth-oauthlib。  
    * 重構 dashboard\_cloud.py 中的 load\_data() 函數，使用 googleapiclient 直接與 Google Drive API 進行通訊，下載數據。  
  * **最終成果**: 成功建立了一個**技術堆疊完全自主可控、不受第三方函式庫不明確行為影響**的企業級數據接口。此最終架構不僅解決了部署問題，更大幅提升了應用程式的長期穩定性、安全性與專業性。

### **V8.0: 企業級通用性升級：導入雙語系國際化架構 (Enterprise Usability Upgrade: Implementing Bilingual Internationalization)**

* **戰略決策 (Strategic Rationale)**: 為提升儀表板在跨國團隊中的通用性與易用性，並使其符合企業級軟體的專業標準，決定進行國際化 (Internationalization, i18n) 升級，導入中英雙語一鍵切換功能。此舉旨在消除語言隔閡，賦能所有同仁無障礙地使用此數據工具。  
* **技術實現 (Technical Implementation)**:  
  1. **建立語言資源中心**: 在 dashboard\_cloud.py 的頂層建立了一個集中的 LANGUAGES 字典。此字典將所有使用者介面 (UI) 的文字（包括標題、按鈕、圖表標籤等）與程式碼邏輯完全分離，並為繁體中文 (zh\_tw) 和英文 (en) 分別提供完整的文本對應。  
  2. **引入狀態管理**: 採用 Streamlit 的核心功能 st.session\_state 來持久化存儲使用者選擇的語言。這確保了用戶在儀表板的不同頁面間導航時，其語言偏好設定能夠保持一致。  
  3. **動態文本渲染**: 重構了所有 UI 組件，使其顯示的文字不再是靜態的硬編碼字串，而是通過一個 get\_text() 輔助函數，根據 st.session\_state 中當前的語言設定，從語言資源中心動態獲取對應的文本。  
  4. **新增語言切換器**: 在側邊欄頂部增加了一個 st.radio 組件，提供「中文」與「English」選項，讓使用者可以直觀、便捷地即時切換界面語言。  
* **最終成果 (Final Outcome)**: 成功將儀表板從單一語言應用，升級為一個具備國際化架構的雙語 BI 工具。此升級不僅大幅提升了使用者體驗與團隊協作效率，更為未來擴展至更多語系奠定了堅實、可擴展的技術基礎，使專案成果更具企業級價值。