import os
import pandas as pd
import glob
import traceback

# --- 路徑設定 ---
source_directory = r"C:\Users\KH00002\電催過程指標追蹤\每日資料底稿"
output_directory = r"C:\Users\KH00002\電催過程指標追蹤"
group_file_path = r"C:\Users\KH00002\電催過程指標追蹤\分組名單.xlsx"
output_filename = "consolidated_report.csv"
output_path = os.path.join(output_directory, output_filename)

# --- 主要邏輯 ---
def main():
    try:
        # 尋找所有匹配的 Excel 檔案
        file_pattern = os.path.join(source_directory, "Report_Outbound_CTD_*.xlsx")
        file_paths = glob.glob(file_pattern)

        if not file_paths:
            return

        # --- 整合每日報告 ---
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
                continue 

        if not all_data:
            return

        consolidated_df = pd.concat(all_data, ignore_index=True)
        consolidated_df['Agent ID'] = consolidated_df['Agent ID'].astype(str).str.strip()

        # --- 【架構升級】使用權威映射表進行團隊與姓名分配 ---
        try:
            group_df = pd.read_excel(group_file_path)
            group_df.columns = group_df.columns.str.strip()
            
            group_df['ID'] = group_df['ID'].astype(str).str.strip()
            
            id_to_group_map = group_df.drop_duplicates(subset=['ID']).set_index('ID')['Group']
            id_to_name_map = group_df.drop_duplicates(subset=['ID']).set_index('ID')['Agent Name']
            
            consolidated_df['Group'] = consolidated_df['Agent ID'].map(id_to_group_map)
            consolidated_df['Agent Name'] = consolidated_df['Agent ID'].map(id_to_name_map)
            
            final_df = consolidated_df.dropna(subset=['Group', 'Agent Name'])

        except FileNotFoundError:
            return
        except Exception as e:
            return

        # --- 儲存最終報告 ---
        final_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    except Exception as e:
        pass

if __name__ == "__main__":
    main()