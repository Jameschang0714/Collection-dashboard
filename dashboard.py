import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os

# --- 自定義組別排序 ---
CUSTOM_GROUP_ORDER = [
    "Motor M1 Team1", "Motor M1 Team2", "Motor M1 Team3", "Motor M1 Team4",
    "SR Team", "Vehicle M1", "Motor M2", "Vehicle M2", "M3"
]

# --- 頁面配置 ---
st.set_page_config(
    page_title="電話催收過程指標追蹤儀表板",
    page_icon="📊",
    layout="wide"
)

# --- 輔助函數 ---
def format_timedelta(td):
    """將 timedelta 物件格式化為 HH:MM:SS 字串。"""
    if pd.isnull(td) or not isinstance(td, pd.Timedelta):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# --- 資料載入與快取 ---
def load_data(path):
    """載入並預處理主要通話資料。"""
    try:
        # Get file modification time to use as part of the cache key
        file_mtime = os.path.getmtime(path)
        df = pd.read_csv(path)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Talk Durations'] = pd.to_timedelta(df['Talk Durations'].fillna('00:00:00'), errors='coerce')
        return df
    except FileNotFoundError:
        st.error(f"錯誤：找不到資料檔案於 '{path}'。請確認檔案存在並重新整理。")
        return None
    except Exception as e:
        st.error(f"載入資料時發生錯誤：{e}")
        return None

@st.cache_data
def load_thresholds(path):
    """載入績效上下限設定檔。"""
    try:
        df = pd.read_excel(path)
        df.set_index('組別', inplace=True)
        return df.to_dict('index')
    except FileNotFoundError:
        st.warning(f"注意：找不到績效上下限設定檔於 '{path}'。將無法顯示顏色標記。")
        return None
    except Exception as e:
        st.error(f"載入績效上下限設定檔時發生錯誤：{e}")
        return None

# --- 顯示模式 ---
def display_daily_view(df, selected_group, thresholds):
    st.header("催員每日撥打狀況報告")
    
    available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
    if not available_dates:
        st.info("沒有可用的資料。")
        return
    
    selected_date = st.selectbox("選擇日期", available_dates)

    if selected_date:
        df_daily = df[df['Date'].dt.date == selected_date].copy()

        if df_daily.empty:
            st.info(f"在 {selected_date} 沒有通話紀錄。")
            return

        # 1. 計算核心 KPI
        summary = df_daily.groupby(['Group', 'Agent ID', 'Agent Name']).agg(
            Total_Outbound_Call=('Case No', 'size'),
            Total_Outbound_Call_Success=('Connected', 'sum'),
            Total_Case_call=('Case No', 'nunique'),
            Total_Talk_Duration=('Talk Durations', 'sum')
        ).reset_index()

        # 2. 計算成功案件數
        success_cases = df_daily[df_daily['Connected'] == 1].groupby(['Agent ID'])['Case No'].nunique().reset_index()
        success_cases.rename(columns={'Case No': 'Total_Success_Case'}, inplace=True)
        
        # 3. 合併成功案件數
        summary = pd.merge(summary, success_cases, on='Agent ID', how='left')
        summary['Total_Success_Case'] = summary['Total_Success_Case'].fillna(0).astype(int)

        # 4. 計算衍生指標
        summary['Repetition_rate'] = np.where(summary['Total_Success_Case'] > 0, summary['Total_Outbound_Call_Success'] / summary['Total_Success_Case'], 0)
        
        # --- 【架構升級】採用顯性流程計算平均通話時長 ---
        total_seconds = summary['Total_Talk_Duration'].dt.total_seconds()
        total_cases = summary['Total_Case_call']
        average_seconds = np.where(total_cases > 0, total_seconds / total_cases, 0)
        summary['Average_Talk_Duration'] = pd.to_timedelta(average_seconds, unit='s')
        
        # 5. 格式化輸出
        summary['Total_Talk_Duration'] = summary['Total_Talk_Duration'].apply(format_timedelta)
        summary['Average_Talk_Duration'] = summary['Average_Talk_Duration'].apply(format_timedelta)
        summary['Repetition_rate'] = summary['Repetition_rate'].round(3)
        
        # 6. 重新命名欄位
        summary.rename(columns={
            'Group': '組別', 'Agent ID': 'ID', 'Agent Name': '姓名',
            'Total_Outbound_Call': '總撥打數', 'Total_Outbound_Call_Success': '總成功撥打數',
            'Total_Case_call': '總處理案件數', 'Total_Success_Case': '總成功案件數',
            'Repetition_rate': '重複撥打率', 'Total_Talk_Duration': '總通話時長',
            'Average_Talk_Duration': '平均通話時長'
        }, inplace=True)

        # 7. 調整最終欄位順序
        final_columns_order = [
            '組別', 'ID', '姓名', '總撥打數', '總成功撥打數', '總處理案件數',
            '總成功案件數', '重複撥打率', '總通話時長', '平均通話時長'
        ]
        summary = summary[final_columns_order]
        
        # 8. 根據團隊進行最終篩選
        if selected_group != "所有團隊":
            summary = summary[summary['組別'] == selected_group]

        # 9. 定義並套用績效視覺化樣式
        def style_daily_kpi(row):
            styles = pd.Series('', index=row.index)
            group_name = row['組別']
            
            if not thresholds or group_name not in thresholds:
                return styles
            
            value_to_check = row['總成功撥打數']
            lower_bound = thresholds[group_name]['下限']
            upper_bound = thresholds[group_name]['上限']
            
            if value_to_check > 0:
                if value_to_check < lower_bound:
                    styles['總成功撥打數'] = 'background-color: #FFCDD2' # 淡紅色
                elif value_to_check >= upper_bound:
                    styles['總成功撥打數'] = 'background-color: #C8E6C9' # 淡綠色
            return styles

        styled_summary = summary.style.apply(style_daily_kpi, axis=1)
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)

def display_monthly_view(df, selected_group, thresholds):
    st.header("月度催員接通數儀表板")

    if selected_group != "所有團隊":
        df = df[df['Group'] == selected_group].copy()

    available_months = sorted(df['Date'].dt.month.unique())
    if not available_months:
        st.info("在選定的團隊中，沒有可用的月份資料。")
        return
        
    selected_month = st.selectbox("選擇月份", available_months, format_func=lambda x: f"2025-{x:02d}")

    if selected_month:
        df_filtered_by_month = df[df['Date'].dt.month == selected_month]

        if df_filtered_by_month.empty:
            st.info("在選定的月份中，沒有資料可供顯示。")
            return

        daily_sum = df_filtered_by_month.groupby(['Date', 'Group', 'Agent ID', 'Agent Name'])['Connected'].sum()
        pivot = daily_sum.unstack(level='Date', fill_value=0).reset_index()
        
        def style_performance(row, date_cols_to_style):
            styles = pd.Series('', index=row.index)
            group_name = row['Group']
            
            if not thresholds or group_name not in thresholds:
                return styles
            
            lower_bound = thresholds[group_name]['下限']
            upper_bound = thresholds[group_name]['上限']
            
            for col in date_cols_to_style:
                if col in row.index:
                    val = row[col]
                    if val > 0:
                        if val < lower_bound:
                            styles[col] = 'background-color: #FFCDD2'
                        elif val >= upper_bound:
                            styles[col] = 'background-color: #C8E6C9'
            return styles

        display_groups = [g for g in CUSTOM_GROUP_ORDER if g in pivot['Group'].unique()]
        
        for group_name in display_groups:
            st.subheader(group_name)
            group_df = pivot[pivot['Group'] == group_name]
            
            date_cols = [col for col in group_df.columns if isinstance(col, pd.Timestamp)]
            
            formatted_date_cols = [d.strftime('%m/%d') for d in date_cols]
            rename_mapping = dict(zip(date_cols, formatted_date_cols))
            renamed_group_df = group_df.rename(columns=rename_mapping)
            
            styled_df = renamed_group_df.style.apply(
                style_performance,
                date_cols_to_style=formatted_date_cols,
                axis=1
            )
            
            st.dataframe(
                styled_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={"Group": None}
            )

def display_behavior_analysis_view(df):
    """新增的催員催收行為分析視圖"""
    st.header("催員催收行為分析")

    # 1. UI 過濾器
    agent_list = sorted(df['Agent Name'].unique())
    if not agent_list:
        st.info("資料中沒有任何催員可供分析。")
        return
    selected_agent = st.selectbox("選擇催員", agent_list)

    analysis_period = st.radio("選擇分析區間", ["單日分析", "月份分析"], horizontal=True, key="behavior_analysis_period")

    df_agent = df[df['Agent Name'] == selected_agent].copy()

    # 2. 根據選擇的區間過濾資料
    if analysis_period == "單日分析":
        available_dates = sorted(df_agent['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(f"催員 {selected_agent} 沒有任何通話紀錄。")
            return
        
        selected_date = st.selectbox("選擇日期", available_dates)
        df_filtered = df_agent[df_agent['Date'].dt.date == selected_date]
    else:  # 月份分析
        available_months = sorted(df_agent['Date'].dt.month.unique())
        
        if not available_months:
            st.warning(f"催員 {selected_agent} 沒有任何通話紀錄。")
            return
        selected_month = st.selectbox("選擇月份", available_months, format_func=lambda x: f"2025-{x:02d}")
        df_filtered = df_agent[df_agent['Date'].dt.month == selected_month]

    if df_filtered.empty:
        st.info("在選定的時間範圍內，這位催員沒有通話紀錄。")
        return

    # 3. 分析邏輯：根據規則分類
    df_filtered['Duration_sec'] = df_filtered['Talk Durations'].dt.total_seconds()
    # 排除通話時長為0的紀錄，因為這不代表實際通話
    df_filtered = df_filtered[df_filtered['Duration_sec'] > 0].copy()

    bins = [-1, 5, 10, 30, 60, 120, 180, float('inf')]
    labels = [
        "~ 5秒",
        "5秒 - 10秒",
        "10秒 - 30秒",
        "30秒 - 1分鐘",
        "1分鐘 - 2分鐘",
        "2分鐘 - 3分鐘",
        "3分鐘以上"
    ]

    df_filtered['Duration_Category'] = pd.cut(df_filtered['Duration_sec'], bins=bins, labels=labels, right=True)

    # 4. 資料彙總
    call_counts = df_filtered.groupby('Duration_Category').size().reindex(labels).fillna(0)
    
    # 5. 視覺化呈現
    st.subheader(f"{selected_agent} 的通話時長分佈")

    y_axis_mode = st.radio(
        "選擇 Y 軸顯示方式",
        ["通話筆數", "通話比例"],
        horizontal=True,
        key="y_axis_mode"
    )
    
    chart_data = pd.DataFrame({
        "通話區間": call_counts.index,
        "通話筆數": call_counts.values.astype(int)
    })

    if y_axis_mode == "通話比例":
        total_calls = chart_data["通話筆數"].sum()
        chart_data["通話比例"] = (chart_data["通話筆數"] / total_calls).fillna(0)
        y_field = "通話比例"
        y_title = "通話比例"
        y_axis = alt.Axis(format=".1%")
        tooltip_content = ['通話區間', alt.Tooltip('通話比例', format=".1%")]
    else:
        y_field = "通話筆數"
        y_title = "通話筆數"
        y_axis = alt.Axis()
        tooltip_content = ['通話區間', '通話筆數']

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('通話區間', sort=labels, title="通話時長區間", axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y_field, title=y_title, axis=y_axis),
        tooltip=tooltip_content
    ).properties(
        title=f"{selected_agent} 在選定時間內的通話時長分佈"
    )

    st.altair_chart(chart, use_container_width=True)

    st.subheader("詳細數據")
    # 根據選擇的模式顯示不同的數據框
    if y_axis_mode == "通話比例":
        st.dataframe(chart_data[['通話區間', '通話筆數', '通話比例']].style.format({'通話比例': '{:.1%}'}), use_container_width=True, hide_index=True)
    else:
        st.dataframe(chart_data[['通話區間', '通話筆數']], use_container_width=True, hide_index=True)


# --- 主應用程式 ---
def main():
    df = load_data("consolidated_report.csv")
    thresholds = load_thresholds("各組每日撥通數上下限.xlsx")

    if df is not None:
        st.sidebar.header("選擇檢視模式")
        view_mode = st.sidebar.radio(
            "",
            ["催員每日撥打狀況報告", "月度催員接通數儀表板", "催員催收行為分析"],
            label_visibility="collapsed"
        )

        # 催收行為分析模式有自己的篩選器，故在此模式下隱藏通用團隊篩選器
        if view_mode != "催員催收行為分析":
            st.sidebar.header("篩選團隊")
            if 'Group' in df.columns:
                df['Group'] = df['Group'].astype(str)
                all_groups = ["所有團隊"] + [g for g in CUSTOM_GROUP_ORDER if g in df['Group'].unique()]
            else:
                all_groups = ["所有團隊"]
            
            selected_group = st.sidebar.selectbox("", all_groups, label_visibility="collapsed")
        else:
            selected_group = None  # 在新模式下不需要

        if view_mode == "催員每日撥打狀況報告":
            display_daily_view(df, selected_group, thresholds)
        elif view_mode == "月度催員接通數儀表板":
            display_monthly_view(df, selected_group, thresholds)
        elif view_mode == "催員催收行為分析":
            display_behavior_analysis_view(df)

if __name__ == "__main__":
    main()