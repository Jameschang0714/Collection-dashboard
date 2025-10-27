import os
import pandas as pd
import glob
import traceback
import re

# --- 1. 路徑設定 ---
source_directory = r"C:\Users\KH00002\電催過程指標追蹤\每日資料底稿"
output_directory = r"C:\Users\KH00002\電催過程指標追蹤"
group_file_path = r"C:\Users\KH00002\電催過程指標追蹤\分組名單.xlsx"
kpi_source_directory = r"C:\Users\KH00002\電催過程指標追蹤\每日資料底稿" 
output_filename = "consolidated_report_enriched.csv"
output_path = os.path.join(output_directory, output_filename)

# --- 2. 函數：處理前端通話紀錄 (邏輯不變) ---
def process_call_logs(source_dir, group_file):
    """整合每日通話紀錄 Excel 檔案，並匹配團隊與催員姓名。"""
    print("開始處理前端通話紀錄...")
    file_pattern = os.path.join(source_dir, "Report_Outbound_CTD_*.xlsx")
    file_paths = glob.glob(file_pattern)
    if not file_paths:
        print("警告：在指定目錄下找不到任何 'Report_Outbound_CTD_*.xlsx' 檔案。")
        return pd.DataFrame()

    all_data = []
    for path in file_paths:
        try:
            df = pd.read_excel(path, skiprows=9)
            df.columns = df.columns.str.strip()
            filename = os.path.basename(path)
            date_str = filename[20:-5]
            df['Date'] = pd.to_datetime(date_str, format='%Y%m%d')
            df['Talk Durations'] = pd.to_timedelta(df['Talk Durations'].fillna('00:00:00'), errors='coerce')
            df['Connected'] = (df['Call Status'] == 'Success').astype(int)
            all_data.append(df)
        except Exception as e:
            print(f"處理檔案 {os.path.basename(path)} 時發生錯誤: {e}")
            continue

    if not all_data:
        print("錯誤：所有通話紀錄檔案都處理失敗。")
        return pd.DataFrame()

    consolidated_df = pd.concat(all_data, ignore_index=True)
    consolidated_df['Agent ID'] = consolidated_df['Agent ID'].astype(str).str.strip()

    try:
        group_df = pd.read_excel(group_file)
        group_df.columns = group_df.columns.str.strip()
        group_df['ID'] = group_df['ID'].astype(str).str.strip()
        id_to_group_map = group_df.drop_duplicates(subset=['ID']).set_index('ID')['Group']
        id_to_name_map = group_df.drop_duplicates(subset=['ID']).set_index('ID')['Agent Name']
        consolidated_df['Group'] = consolidated_df['Agent ID'].map(id_to_group_map)
        consolidated_df['Agent Name'] = consolidated_df['Agent ID'].map(id_to_name_map)
        final_df = consolidated_df.dropna(subset=['Group', 'Agent Name'])
        print(f"成功處理 {len(final_df)} 筆通話紀錄。")
        return final_df
    except FileNotFoundError:
        print(f"錯誤：找不到分組名單檔案 '{group_file}'。")
        return pd.DataFrame()
    except Exception as e:
        print(f"處理分組名單時發生錯誤: {e}")
        return pd.DataFrame()

# --- 3. 【重大升級】兼容多格式的單日績效檔案處理函數 ---
def process_daily_kpi_file(kpi_file_path, report_date):
    """
    讀取單一績效底稿，並根據精準的業務邏輯計算「金額摘要」與「在手案件數」。
    """
    try:
        df_kpi_full = pd.DataFrame()
        # --- Part 1: 智能讀取檔案 ---
        if kpi_file_path.endswith('.xlsx'):
            df_kpi_full = pd.read_excel(kpi_file_path, skiprows=1, header=1)
            column_mapping = {
                '資料日期\nDATA DATE': 'DATA_DATE',
                '催員編號\nCOLLECTOR ID': 'USR_ID',
                '逾期金額\nOVERDUE AMOUNT': 'ASSIGN_AMT',
                '派件日期\nASSIGN DATE': 'ASSIGN_YMD',
                '移出日期\nSHIFT OUT DATE': 'REMOVE_YMD',
                '回推/回收日期\nRECEIVABLE DATE': 'RCV_DT',
                '實際回收金額\nACTUAL RECOVERY AMOUNT': 'RCV_AMT_ACTUAL'
            }
            df_kpi_full.rename(columns=column_mapping, inplace=True)
            if 'TMRENT_TAR' not in df_kpi_full.columns:
                df_kpi_full['TMRENT_TAR'] = 0
        else:
            df_kpi_full = pd.read_csv(kpi_file_path, low_memory=False)

        # --- Part 2: 計算金額摘要 (採用新邏輯) ---
        
        # 獲取當天所有催員的列表，作為合併的基礎
        all_agents_today = pd.DataFrame(df_kpi_full['USR_ID'].unique(), columns=['Agent ID'])
        all_agents_today['Agent ID'] = all_agents_today['Agent ID'].astype(str).str.strip()
        
        # 2a. 精準計算當日回收金額
        daily_received_summary = pd.DataFrame()
        if 'RCV_DT' in df_kpi_full.columns and 'RCV_AMT_ACTUAL' in df_kpi_full.columns:
            df_kpi_full['RCV_DT'] = pd.to_datetime(df_kpi_full['RCV_DT'], errors='coerce')
            df_kpi_full['RCV_AMT_ACTUAL'] = pd.to_numeric(
                df_kpi_full['RCV_AMT_ACTUAL'].astype(str).str.replace(',', ''), errors='coerce'
            ).fillna(0)
            
            # 核心篩選邏輯：只選擇回收日期為報告日期的紀錄
            recoveries_today = df_kpi_full[df_kpi_full['RCV_DT'].dt.date == report_date.date()].copy()
            
            if not recoveries_today.empty:
                daily_received_summary = recoveries_today.groupby('USR_ID')['RCV_AMT_ACTUAL'].sum().reset_index()
                daily_received_summary.rename(columns={'USR_ID': 'Agent ID', 'RCV_AMT_ACTUAL': 'Daily Received Amount'}, inplace=True)
                daily_received_summary['Agent ID'] = daily_received_summary['Agent ID'].astype(str).str.strip()

        # 2b. 計算其他指標 (如分配金額、目標等)
        other_metrics = df_kpi_full.groupby('USR_ID').agg(
            ASSIGN_AMT=('ASSIGN_AMT', 'sum'),
            TMRENT_TAR=('TMRENT_TAR', 'first')
        ).reset_index()
        other_metrics.rename(columns={'USR_ID': 'Agent ID', 'ASSIGN_AMT': 'Daily Assigned Amount', 'TMRENT_TAR': 'Target Amount'}, inplace=True)
        other_metrics['Agent ID'] = other_metrics['Agent ID'].astype(str).str.strip()

        # 2c. 合併所有金額指標
        daily_amounts_summary = pd.merge(all_agents_today, other_metrics, on='Agent ID', how='left')
        if not daily_received_summary.empty:
            daily_amounts_summary = pd.merge(daily_amounts_summary, daily_received_summary, on='Agent ID', how='left')
        
        daily_amounts_summary['Date'] = report_date
        daily_amounts_summary.fillna(0, inplace=True)

        # --- Part 3: 計算在手案件數 (邏輯不變) ---
        case_cols = ['USR_ID', 'ASSIGN_YMD', 'REMOVE_YMD']
        if not all(col in df_kpi_full.columns for col in case_cols):
            daily_cases_summary = pd.DataFrame()
        else:
            df_cases = df_kpi_full[case_cols].copy()
            df_cases.rename(columns={'USR_ID': 'Agent ID'}, inplace=True)
            df_cases['Agent ID'] = df_cases['Agent ID'].astype(str).str.strip()
            df_cases['ASSIGN_YMD'] = pd.to_datetime(df_cases['ASSIGN_YMD'], errors='coerce')
            df_cases['REMOVE_YMD'] = pd.to_datetime(df_cases['REMOVE_YMD'], errors='coerce')
            
            future_date = pd.to_datetime('2099-12-31')
            df_cases['REMOVE_YMD'] = df_cases['REMOVE_YMD'].fillna(future_date)
            df_cases.dropna(subset=['ASSIGN_YMD'], inplace=True)

            active_mask = (df_cases['ASSIGN_YMD'] <= report_date) & (df_cases['REMOVE_YMD'] >= report_date)
            active_cases_today = df_cases[active_mask]
            
            daily_cases_summary = active_cases_today.groupby('Agent ID').size().reset_index(name='Cases on Hand')
            daily_cases_summary['Date'] = report_date
        
        return daily_amounts_summary, daily_cases_summary

    except Exception as e:
        print(f"處理績效檔案 {os.path.basename(kpi_file_path)} 時發生錯誤: {e}")
        return pd.DataFrame(), pd.DataFrame()


# --- 輔助函數：從績效檔名解析日期 ---
def extract_report_date_from_filename(filename):
    """從績效檔名取得日期，優先處理 9 碼格式 (YYYYMMMDD)，再回退到標準 8 碼。"""

    def try_parse(candidate: str):
        try:
            return pd.to_datetime(candidate, format='%Y%m%d')
        except ValueError:
            return None

    # 先處理 9 碼格式，例如 202501010 (代表 2025-10-10)
    match_9 = re.search(r'(\d{9})', filename)
    if match_9:
        raw = match_9.group(1)
        year = raw[:4]
        month_part = raw[4:7]
        day_part = raw[7:]
        try:
            month = int(month_part)
            day = int(day_part)
        except ValueError:
            month = day = None

        if month and day and 1 <= month <= 12 and 1 <= day <= 31:
            candidate = f"{year}{month:02d}{day:02d}"
            parsed = try_parse(candidate)
            if parsed is not None:
                return parsed

    # 再處理標準 8 碼日期 (YYYYMMDD)
    match_8 = re.search(r'(\d{8})', filename)
    if match_8:
        parsed = try_parse(match_8.group(1))
        if parsed is not None:
            return parsed

    return None


# --- 4. 主邏輯 (已升級) ---
def main():
    """主執行函數"""
    print("--- 開始執行數據增強流程 ---")
    
    # 步驟一：處理前端通話紀錄
    df_calls = process_call_logs(source_directory, group_file_path)
    if df_calls.empty:
        print("因無法處理通話紀錄，流程中止。")
        return

    # 步驟二：建立日期到績效檔案路徑的映射表
    print("正在掃描並映射每日績效檔案...")
    
    all_files_in_dir = glob.glob(os.path.join(kpi_source_directory, "*"))
    kpi_file_list = []
    print(f"在目錄中找到 {len(all_files_in_dir)} 個項目。開始過濾績效檔案...")
    for f_path in all_files_in_dir:
        filename = os.path.basename(f_path)
        if (filename.startswith("COLL_KPI_DTL ") and filename.endswith(".xlsx")) or \
           (filename.startswith("KH_DM_FACT_COLL_KPI_DTL_") and filename.endswith(".csv")):
            kpi_file_list.append(f_path)
            print(f"  [符合] -> {filename}")
    
    print(f"過濾後，找到 {len(kpi_file_list)} 個有效的績效檔案。")

    kpi_file_map = {}
    for f_path in kpi_file_list:
        filename = os.path.basename(f_path)
        try:
            file_date = extract_report_date_from_filename(filename)
        except Exception as e:
            print(f"警告：解析檔案 {filename} 日期時出錯 ({e})，已略過。")
            continue

        if file_date is not None:
            kpi_file_map[file_date.date()] = f_path
        else:
            print(f"警告：檔案 {filename} 名稱中找不到可用的日期，已略過。")

    if not kpi_file_map:
        print("錯誤：找不到任何有效的每日績效檔案。將僅產出基礎通話報告。")
        df_calls.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"報告已儲存至： {output_path}")
        return
    print(f"成功映射 {len(kpi_file_map)} 個績效檔案。")

    # 步驟三：逐日處理績效數據
    all_daily_amounts = []
    all_daily_cases = []
    
    unique_report_dates = sorted(df_calls['Date'].unique())

    for report_date in unique_report_dates:
        report_date_obj = pd.to_datetime(report_date).date()
        
        if report_date_obj in kpi_file_map:
            daily_kpi_file = kpi_file_map[report_date_obj]
            print(f"處理日期 {report_date_obj.strftime('%Y-%m-%d')} 的數據 (來源: {os.path.basename(daily_kpi_file)})...")
            
            df_amounts, df_cases = process_daily_kpi_file(daily_kpi_file, report_date)
            
            if not df_amounts.empty:
                all_daily_amounts.append(df_amounts)
            if not df_cases.empty:
                all_daily_cases.append(df_cases)
        else:
            print(f"警告：日期 {report_date_obj.strftime('%Y-%m-%d')} 找不到對應的績效檔案，將留空處理。")

    # 步驟四：合併所有處理好的每日數據
    df_kpi_amounts_final = pd.concat(all_daily_amounts, ignore_index=True) if all_daily_amounts else pd.DataFrame()
    df_cases_on_hand_final = pd.concat(all_daily_cases, ignore_index=True) if all_daily_cases else pd.DataFrame()

    # 步驟五：將匯總後的績效數據合併回主通話紀錄
    print("正在合併最終數據...")
    df_enriched = pd.merge(df_calls, df_kpi_amounts_final, on=['Date', 'Agent ID'], how='left')
    if not df_cases_on_hand_final.empty:
        df_enriched = pd.merge(df_enriched, df_cases_on_hand_final, on=['Date', 'Agent ID'], how='left')
    
    # 清理合併後可能產生的空值
    new_kpi_cols = ['Daily Received Amount', 'Daily Assigned Amount', 'Target Amount', 'Cases on Hand']
    for col in new_kpi_cols:
        if col in df_enriched.columns:
            df_enriched[col] = df_enriched[col].fillna(0)
    
    if 'Cases on Hand' in df_enriched.columns:
        df_enriched['Cases on Hand'] = df_enriched['Cases on Hand'].astype(int)
    
    print("數據合併完成。")

    # 步驟六：篩選必要欄位並儲存最終報告
    try:
        print("正在篩選最終報告的欄位，只保留儀表板需要的資訊...")
        
        used_cols = [
            'Date', 'Group', 'Agent ID', 'Agent Name', 'Case No', 'Connected', 
            'Talk Durations', 'Call Assigned', 'Cases on Hand', 'Daily Received Amount'
        ]
        
        final_cols_to_keep = [col for col in used_cols if col in df_enriched.columns]
        
        if len(final_cols_to_keep) != len(used_cols):
            print("警告：部分儀表板必要的欄位在資料中找不到，可能影響儀表板功能。")
            print(f"預期欄位: {used_cols}")
            print(f"實際找到的欄位: {final_cols_to_keep}")

        df_final_filtered = df_enriched[final_cols_to_keep]
        
        print(f"欄位篩選完成，報告將從 {len(df_enriched.columns)} 個欄位減為 {len(df_final_filtered.columns)} 個。")

        df_final_filtered.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"--- 流程成功結束 ---")
        print(f"增強版報告已成功儲存至： {output_path}")
    except Exception as e:
        print(f"儲存最終報告時發生錯誤: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
