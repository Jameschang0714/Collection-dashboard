import os
import pandas as pd
import glob
import traceback

print("腳本已啟動。")

# --- 路徑設定 ---
source_directory = "每日資料底稿"
output_directory = "."
group_file_path = "分組名單.xlsx"
output_filename = "consolidated_report.csv"
output_path = os.path.join(output_directory, output_filename)

# --- 主要邏輯 ---
def main():
    try:
        # 尋找所有匹配的 Excel 檔案
        file_pattern = os.path.join(source_directory, "Report_Outbound_CTD_*.xlsx")
        file_paths = glob.glob(file_pattern)

        if not file_paths:
            print(f"在 {source_directory} 中找不到任何匹配 'Report_Outbound_CTD_*.xlsx' 的檔案。")
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
                print(f"處理檔案 {path} 時發生錯誤: {e}")
                continue 

        if not all_data:
            print("處理檔案後沒有資料可供整合。")
            return

        consolidated_df = pd.concat(all_data, ignore_index=True)
        consolidated_df['Agent ID'] = consolidated_df['Agent ID'].astype(str).str.strip()

        # --- 【架構升級】使用權威映射表進行團隊與姓名分配 ---
        try:
            group_df = pd.read_excel(group_file_path)
            group_df.columns = group_df.columns.str.strip()
            
            group_df['ID'] = group_df['ID'].astype(str).str.strip()
            
            # 1. 建立權威性的 ID -> Group 和 ID -> Name 映射表
            #    使用 drop_duplicates 確保每個 ID 只對應一個團隊與姓名，以分組名單中的第一筆為準。
            id_to_group_map = group_df.drop_duplicates(subset=['ID']).set_index('ID')['Group']
            id_to_name_map = group_df.drop_duplicates(subset=['ID']).set_index('ID')['Agent Name']
            
            # 2. 使用 .map() 方法，根據權威映射表，為每一筆紀錄分配團隊與姓名
            consolidated_df['Group'] = consolidated_df['Agent ID'].map(id_to_group_map)
            consolidated_df['Agent Name'] = consolidated_df['Agent ID'].map(id_to_name_map)
            
            print("\n>>> 已根據權威映射表，完成團隊與姓名分配 <<<")

            # 移除任何未能成功分配團隊或姓名的紀錄
            final_df = consolidated_df.dropna(subset=['Group', 'Agent Name'])
            print(">>> 已移除所有不在分組名單中的催員紀錄 <<<")

        except FileNotFoundError:
            print(f"找不到分組檔案: {group_file_path}。將無法進行團隊分配。")
            return
        except Exception as e:
            print(f"處理分組檔案時發生錯誤: {e}")
            print(traceback.format_exc())
            return

        # --- 儲存最終報告 ---
        final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n成功！ {len(all_data)} 個檔案已被整合與合併。")
        print("最終報告已成功儲存。")

    except Exception as e:
        print(f"在 main() 中發生錯誤: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
