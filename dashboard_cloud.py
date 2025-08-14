import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
import io
import json

# --- 【V8.0 升級】導入 Google 官方 API 函式庫 ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- 【V8.0 升級】建立多語言資源庫 ---
LANGUAGES = {
    "zh_tw": {
        "page_title": "電話催收過程指標追蹤儀表板 (生產環境)",
        "main_title": "電話催收過程指標追蹤儀表板",
        "lang_selector_label": "語言 (Language)",
        "load_data_success": "數據已透過 Google 官方 API 安全載入。",
        "load_data_error": "透過 Google 官方 API 載入資料時發生錯誤：",
        "load_thresholds_warning": "注意：找不到績效上下限設定檔於 '{path}'。將無法顯示顏色標記。",
        "load_thresholds_error": "載入績效上下限設定檔時發生錯誤：{e}",
        "data_load_failed": "資料未能成功載入，請根據上方的錯誤訊息檢查您的設定。",
        "sidebar_view_mode": "選擇檢視模式",
        "sidebar_filter_team": "篩選團隊",
        "view_modes": ["催員每日撥打狀況報告", "月度催員接通數儀表板", "催員催收行為分析", "催員時點撥打與接通分析", "催員行為與高績效人員比較"],
        "all_teams": "所有團隊",
        # Daily View
        "daily_view_header": "催員每日撥打狀況報告",
        "daily_view_no_data_for_team": "在選定的團隊中，沒有可用的資料。",
        "daily_view_date_selector": "選擇日期",
        "daily_view_no_records_for_date": "在 {selected_date} 沒有通話紀錄。",
        "daily_view_columns": {
            '組別': '組別', 'ID': 'ID', '姓名': '姓名', '總撥打數': '總撥打數', 
            '總成功撥打數': '總成功撥打數', '總處理案件數': '總處理案件數',
            '總成功案件數': '總成功案件數', '重複撥打率': '重複撥打率', 
            '總通話時長': '總通話時長', '平均通話時長': '平均通話時長'
        },
        # Monthly View
        "monthly_view_header": "月度催員接通數儀表板",
        "monthly_view_no_month_data": "在選定的團隊中，沒有可用的月份資料。",
        "monthly_view_month_selector": "選擇月份",
        "monthly_view_no_data_for_month": "在選定的月份中，沒有資料可供顯示。",
        # Behavior Analysis
        "behavior_view_header": "催員催收行為分析",
        "behavior_view_agent_selector": "選擇催員或全體",
        "behavior_view_all_agents": "全體",
        "behavior_view_no_data_in_team": "團隊 '{selected_group}' 中沒有可用的資料。",
        "behavior_view_no_records_warning": "{analysis_subject_name} 在選定的時間範圍內沒有通話紀錄。",
        "behavior_view_analysis_period": "選擇分析區間",
        "behavior_view_period_options": ["單日分析", "月份分析"],
        "behavior_view_no_valid_talk_duration": "在選定的時間範圍內，沒有有效通話時長紀錄。",
        "behavior_view_y_axis_option": "選擇 Y 軸顯示方式",
        "behavior_view_y_axis_options": ["通話筆數", "通話比例"],
        "behavior_view_chart_title": "{analysis_subject_name} 通話時長分佈",
        "behavior_view_x_axis": "通話時長區間",
        "behavior_view_y_axis_count": "通話筆數",
        "behavior_view_y_axis_percentage": "通話比例",
        "behavior_view_tooltip_category": "時長區間",
        "behavior_view_tooltip_count": "通話筆數",
        "behavior_view_tooltip_percentage": "通話比例",
        "behavior_view_data_subheader": "詳細數據",
        # Call Time Analysis
        "call_time_view_header": "催員時點撥打與接通分析",
        "call_time_view_granularity_selector": "選擇時間粒度",
        "call_time_view_granularity_options": ["小時", "30分鐘", "15分鐘"],
        "call_time_view_display_mode": "選擇顯示模式",
        "call_time_view_display_mode_options": ["總撥出電話數", "總接通電話數", "綜合分析 (撥出數 + 接通率熱力圖)"],
        "call_time_view_y_axis_mode": "選擇 Y 軸顯示方式",
        "call_time_view_y_axis_options": ["數量", "比例"],
        "call_time_view_combined_chart_caption": "註：為清晰呈現投入量與接通效率的關係，綜合分析圖 Y 軸固定為「數量」。",
        "call_time_view_chart_title": "{analysis_subject_name} 的通話時點分佈 ({time_granularity})",
        "call_time_view_chart_title_outbound": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_connected": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_combined": "{analysis_subject_name} {y_title}與接通率 ({time_granularity})",
        "call_time_view_y_outbound_count": "總撥出電話數",
        "call_time_view_y_outbound_ratio": "撥出電話比例",
        "call_time_view_y_connected_count": "總接通電話數",
        "call_time_view_y_connected_ratio": "接通電話比例",
        "call_time_view_x_axis": "時間區間",
        "call_time_view_color_legend": "接通率",
        "call_time_view_tooltip_time": "時間區間",
        "call_time_view_tooltip_outbound_count": "總撥出數",
        "call_time_view_tooltip_outbound_ratio": "撥出比例",
        "call_time_view_tooltip_connected_count": "總接通數",
        "call_time_view_tooltip_connected_ratio": "接通比例",
        "call_time_view_tooltip_connection_rate": "接通率",
        # Profiling View
        "profiling_view_header": "催員行為與高績效人員比較 (Agent vs. Benchmark)",
        "profiling_view_agent_selector": "選擇要分析的催員",
        "profiling_view_benchmark_selector": "選擇績效標竿群組 (可多選)",
        "profiling_view_period_selector": "選擇分析區間",
        "profiling_view_period_options": ["單日", "月份"],
        "profiling_view_no_date_warning": "資料中沒有可用的日期。",
        "profiling_view_no_month_warning": "資料中沒有可用的月份。",
        "profiling_view_time_chart_title": "通話時點模式分析：{selected_agent} vs. 標竿群組",
        "profiling_view_time_y_axis": "撥打數",
        "profiling_view_time_tooltip_time": "時間",
        "profiling_view_time_tooltip_agent": "個人撥打數",
        "profiling_view_time_tooltip_benchmark": "標竿平均",
        "profiling_view_duration_chart_title": "通話時長模式分析：{selected_agent} vs. 標竿群組",
        "profiling_view_duration_y_axis": "比例",
        "profiling_view_duration_tooltip_category": "時長區間",
        "profiling_view_duration_tooltip_agent": "個人比例",
        "profiling_view_duration_tooltip_benchmark": "標竿平均",
    },
    "en": {
        "page_title": "Collector Performance Dashboard (Production)",
        "main_title": "Collector Performance Dashboard",
        "lang_selector_label": "Language",
        "load_data_success": "Data loaded securely via official Google API.",
        "load_data_error": "Error loading data via official Google API:",
        "load_thresholds_warning": "Warning: Threshold file not found at '{path}'. Color styling will be disabled.",
        "load_thresholds_error": "Error loading threshold file: {e}",
        "data_load_failed": "Failed to load data. Please check your settings based on the error message above.",
        "sidebar_view_mode": "Select View Mode",
        "sidebar_filter_team": "Filter Team",
        "view_modes": ["Daily Agent Report", "Monthly Connection Dashboard", "Agent Behavior Analysis", "Call Time Analysis", "Agent vs. Benchmark Profiling"],
        "all_teams": "All Teams",
        # Daily View
        "daily_view_header": "Daily Agent Call Report",
        "daily_view_no_data_for_team": "No data available for the selected team.",
        "daily_view_date_selector": "Select Date",
        "daily_view_no_records_for_date": "No call records on {selected_date}.",
        "daily_view_columns": {
            '組別': 'Group', 'ID': 'ID', '姓名': 'Name', '總撥打數': 'Total Calls', 
            '總成功撥打數': 'Connected Calls', '總處理案件數': 'Total Cases Handled',
            '總成功案件數': 'Successful Cases', '重複撥打率': 'Repetition Rate', 
            '總通話時長': 'Total Talk Duration', '平均通話時長': 'Avg. Talk Duration'
        },
        # Monthly View
        "monthly_view_header": "Monthly Agent Connection Dashboard",
        "monthly_view_no_month_data": "No month data available for the selected team.",
        "monthly_view_month_selector": "Select Month",
        "monthly_view_no_data_for_month": "No data to display for the selected month.",
        # Behavior Analysis
        "behavior_view_header": "Agent Behavior Analysis",
        "behavior_view_agent_selector": "Select Agent or All",
        "behavior_view_all_agents": "All",
        "behavior_view_no_data_in_team": "No data available in team '{selected_group}'.",
        "behavior_view_no_records_warning": "{analysis_subject_name} has no call records for the selected period.",
        "behavior_view_analysis_period": "Select Analysis Period",
        "behavior_view_period_options": ["Daily Analysis", "Monthly Analysis"],
        "behavior_view_no_valid_talk_duration": "No records with valid talk duration in the selected period.",
        "behavior_view_y_axis_option": "Select Y-Axis Display",
        "behavior_view_y_axis_options": ["Call Count", "Call Percentage"],
        "behavior_view_chart_title": "{analysis_subject_name} Talk Duration Distribution",
        "behavior_view_x_axis": "Talk Duration Category",
        "behavior_view_y_axis_count": "Call Count",
        "behavior_view_y_axis_percentage": "Call Percentage",
        "behavior_view_tooltip_category": "Duration Category",
        "behavior_view_tooltip_count": "Call Count",
        "behavior_view_tooltip_percentage": "Call Percentage",
        "behavior_view_data_subheader": "Detailed Data",
        # Call Time Analysis
        "call_time_view_header": "Agent Call Time & Connection Analysis",
        "call_time_view_granularity_selector": "Select Time Granularity",
        "call_time_view_granularity_options": ["Hourly", "30-Min", "15-Min"],
        "call_time_view_display_mode": "Select Display Mode",
        "call_time_view_display_mode_options": ["Total Outbound Calls", "Total Connected Calls", "Combined Analysis (Outbound + Connection Rate Heatmap)"],
        "call_time_view_y_axis_mode": "Select Y-Axis Display",
        "call_time_view_y_axis_options": ["Count", "Percentage"],
        "call_time_view_combined_chart_caption": "Note: For clarity, the Y-axis for Combined Analysis is fixed to 'Count'.",
        "call_time_view_chart_title": "{analysis_subject_name}'s Call Time Distribution ({time_granularity})",
        "call_time_view_chart_title_outbound": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_connected": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_combined": "{analysis_subject_name} {y_title} & Connection Rate ({time_granularity})",
        "call_time_view_y_outbound_count": "Total Outbound Calls",
        "call_time_view_y_outbound_ratio": "Outbound Call Ratio",
        "call_time_view_y_connected_count": "Total Connected Calls",
        "call_time_view_y_connected_ratio": "Connected Call Ratio",
        "call_time_view_x_axis": "Time Interval",
        "call_time_view_color_legend": "Connection Rate",
        "call_time_view_tooltip_time": "Time Interval",
        "call_time_view_tooltip_outbound_count": "Total Outbound",
        "call_time_view_tooltip_outbound_ratio": "Outbound Ratio",
        "call_time_view_tooltip_connected_count": "Total Connected",
        "call_time_view_tooltip_connected_ratio": "Connected Ratio",
        "call_time_view_tooltip_connection_rate": "Connection Rate",
        # Profiling View
        "profiling_view_header": "Agent vs. Benchmark Profiling",
        "profiling_view_agent_selector": "Select Agent to Analyze",
        "profiling_view_benchmark_selector": "Select Benchmark Group (multi-select)",
        "profiling_view_period_selector": "Select Analysis Period",
        "profiling_view_period_options": ["Daily", "Monthly"],
        "profiling_view_no_date_warning": "No available dates in the data.",
        "profiling_view_no_month_warning": "No available months in the data.",
        "profiling_view_time_chart_title": "Call Time Pattern Analysis: {selected_agent} vs. Benchmark",
        "profiling_view_time_y_axis": "Call Count",
        "profiling_view_time_tooltip_time": "Time",
        "profiling_view_time_tooltip_agent": "Agent's Calls",
        "profiling_view_time_tooltip_benchmark": "Benchmark Avg",
        "profiling_view_duration_chart_title": "Talk Duration Pattern Analysis: {selected_agent} vs. Benchmark",
        "profiling_view_duration_y_axis": "Percentage",
        "profiling_view_duration_tooltip_category": "Duration Category",
        "profiling_view_duration_tooltip_agent": "Agent's Ratio",
        "profiling_view_duration_tooltip_benchmark": "Benchmark Avg",
    }
}

# --- 【V8.0 升級】初始化 Session State ---
if 'lang' not in st.session_state:
    st.session_state.lang = "zh_tw"

# --- 【V8.0 升級】語言文本獲取函數 ---
def get_text(key):
    """根據 session_state 中的語言選擇，返回對應的文本。"""
    return LANGUAGES[st.session_state.lang].get(key, key)

# --- 頁面配置 ---
st.set_page_config(
    page_title=get_text("page_title"),
    page_icon="🌐",
    layout="wide"
)

# --- 自定義組別排序 ---
CUSTOM_GROUP_ORDER = [
    "Motor M1 Team1", "Motor M1 Team2", "Motor M1 Team3", "Motor M1 Team4",
    "SR Team", "Vehicle M1", "Motor M2", "Vehicle M2", "M3", "Write off"
]

# --- 輔助函數 ---
def format_timedelta(td):
    if pd.isnull(td) or not isinstance(td, pd.Timedelta):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# --- 透過 Google 官方 API 載入數據 ---
@st.cache_data(ttl=600)
def load_data():
    try:
        creds_json = json.loads(st.secrets.gcp_service_account.credentials)
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)
        file_id = "1O9Po49F7TkV4c_Q8Y0yaufhI15HFKGyT"
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Talk Durations'] = pd.to_timedelta(df['Talk Durations'].fillna('00:00:00'), errors='coerce')
        df['Call Assigned'] = pd.to_datetime(df['Call Assigned'])
        st.success(get_text("load_data_success"))
        return df
    except Exception as e:
        st.error(get_text("load_data_error"))
        st.exception(e)
        return None

@st.cache_data
def load_thresholds(path):
    try:
        df = pd.read_excel(path)
        df.set_index('組別', inplace=True)
        return df.to_dict('index')
    except FileNotFoundError:
        st.warning(get_text("load_thresholds_warning").format(path=path))
        return None
    except Exception as e:
        st.error(get_text("load_thresholds_error").format(e=e))
        return None

# --- 顯示模式 ---
def display_daily_view(df, selected_group, thresholds):
    st.header(get_text("daily_view_header"))
    
    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
    if not available_dates:
        st.info(get_text("daily_view_no_data_for_team"))
        return
    
    selected_date = st.selectbox(get_text("daily_view_date_selector"), available_dates)

    if selected_date:
        df_daily = df[df['Date'].dt.date == selected_date].copy()

        if df_daily.empty:
            st.info(get_text("daily_view_no_records_for_date").format(selected_date=selected_date))
            return

        summary = df_daily.groupby(['Group', 'Agent ID', 'Agent Name']).agg(
            Total_Outbound_Call=('Case No', 'size'),
            Total_Outbound_Call_Success=('Connected', 'sum'),
            Total_Case_call=('Case No', 'nunique'),
            Total_Talk_Duration=('Talk Durations', 'sum')
        ).reset_index()

        success_cases = df_daily[df_daily['Connected'] == 1].groupby(['Agent ID'])['Case No'].nunique().reset_index()
        success_cases.rename(columns={'Case No': 'Total_Success_Case'}, inplace=True)
        
        summary = pd.merge(summary, success_cases, on='Agent ID', how='left')
        summary['Total_Success_Case'] = summary['Total_Success_Case'].fillna(0).astype(int)

        summary['Repetition_rate'] = np.where(summary['Total_Success_Case'] > 0, summary['Total_Outbound_Call_Success'] / summary['Total_Success_Case'], 0)
        
        total_seconds = summary['Total_Talk_Duration'].dt.total_seconds()
        total_cases = summary['Total_Case_call']
        average_seconds = np.where(total_cases > 0, total_seconds / total_cases, 0)
        summary['Average_Talk_Duration'] = pd.to_timedelta(average_seconds, unit='s')
        
        summary['Total_Talk_Duration'] = summary['Total_Talk_Duration'].apply(format_timedelta)
        summary['Average_Talk_Duration'] = summary['Average_Talk_Duration'].apply(format_timedelta)
        summary['Repetition_rate'] = summary['Repetition_rate'].round(3)
        
        # 動態載入欄位名稱
        column_map_keys = list(get_text("daily_view_columns").keys())
        original_columns = ['Group', 'Agent ID', 'Agent Name', 'Total_Outbound_Call', 'Total_Outbound_Call_Success', 'Total_Case_call', 'Total_Success_Case', 'Repetition_rate', 'Total_Talk_Duration', 'Average_Talk_Duration']
        
        rename_dict = {orig: get_text("daily_view_columns")[key] for orig, key in zip(original_columns, column_map_keys)}
        summary.rename(columns=rename_dict, inplace=True)

        final_columns_order = list(get_text("daily_view_columns").values())
        summary = summary[final_columns_order]
        
        def style_daily_kpi(row):
            styles = pd.Series('', index=row.index)
            group_name = row[get_text("daily_view_columns")['組別']]
            
            if not thresholds or group_name not in thresholds:
                return styles
            
            value_to_check = row[get_text("daily_view_columns")['總成功撥打數']]
            lower_bound = thresholds[group_name]['下限']
            upper_bound = thresholds[group_name]['上限']
            
            if value_to_check > 0:
                if value_to_check < lower_bound:
                    styles[get_text("daily_view_columns")['總成功撥打數']] = 'background-color: #FFCDD2'
                elif value_to_check >= upper_bound:
                    styles[get_text("daily_view_columns")['總成功撥打數']] = 'background-color: #C8E6C9'
            return styles

        styled_summary = summary.style.apply(style_daily_kpi, axis=1)
        st.dataframe(styled_summary, use_container_width=True, hide_index=True)

def display_monthly_view(df, selected_group, thresholds):
    st.header(get_text("monthly_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    available_months = sorted(df['Date'].dt.month.unique())
    if not available_months:
        st.info(get_text("monthly_view_no_month_data"))
        return
        
    selected_month = st.selectbox(get_text("monthly_view_month_selector"), available_months, format_func=lambda x: f"2025-{x:02d}")

    if selected_month:
        df_filtered_by_month = df[df['Date'].dt.month == selected_month]

        if df_filtered_by_month.empty:
            st.info(get_text("monthly_view_no_data_for_month"))
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

def display_behavior_analysis_view(df, selected_group):
    st.header(get_text("behavior_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    agent_list = [get_text("behavior_view_all_agents")] + sorted(df['Agent Name'].unique())
    if len(agent_list) == 1:
        st.info(get_text("behavior_view_no_data_in_team").format(selected_group=selected_group))
        return
    
    selected_agent = st.selectbox(get_text("behavior_view_agent_selector"), agent_list, key="behavior_agent_select")

    if selected_agent == get_text("behavior_view_all_agents"):
        df_to_analyze = df.copy()
        analysis_subject_name = f"{selected_group} {get_text('behavior_view_all_agents')}" if selected_group != get_text("all_teams") else f"{get_text('all_teams')} {get_text('behavior_view_all_agents')}"
    else:
        df_to_analyze = df[df['Agent Name'] == selected_agent].copy()
        analysis_subject_name = selected_agent

    analysis_period = st.radio(get_text("behavior_view_analysis_period"), get_text("behavior_view_period_options"), horizontal=True, key="behavior_period")

    if analysis_period == get_text("behavior_view_period_options")[0]: # 單日分析
        available_dates = sorted(df_to_analyze['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_date = st.selectbox(get_text("daily_view_date_selector"), available_dates, key="behavior_date_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.date == selected_date]
    else: # 月份分析
        available_months = sorted(df_to_analyze['Date'].dt.month.unique())
        if not available_months:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_month = st.selectbox(get_text("monthly_view_month_selector"), available_months, format_func=lambda x: f"2025-{x:02d}", key="behavior_month_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.month == selected_month]

    if df_filtered.empty:
        st.info(get_text("daily_view_no_records_for_date").format(selected_date="selected period"))
        return

    df_filtered = df_filtered[df_filtered['Talk Durations'].dt.total_seconds() > 0].copy()
    if df_filtered.empty:
        st.info(get_text("behavior_view_no_valid_talk_duration"))
        return

    def categorize_talk_duration(seconds):
        if seconds <= 5: return "~5s"
        elif 5 < seconds <= 10: return "5s - 10s"
        elif 10 < seconds <= 30: return "10s - 30s"
        elif 30 < seconds <= 60: return "30s - 1min"
        elif 60 < seconds <= 120: return "1min - 2min"
        elif 120 < seconds <= 180: return "2min - 3min"
        else: return "> 3min"

    df_filtered['Talk_Duration_Category'] = df_filtered['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)

    category_counts = df_filtered['Talk_Duration_Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']

    category_order = ["~5s", "5s - 10s", "10s - 30s", "30s - 1min", "1min - 2min", "2min - 3min", "> 3min"]
    category_counts['Category'] = pd.Categorical(category_counts['Category'], categories=category_order, ordered=True)
    category_counts = category_counts.sort_values('Category')

    total_calls = category_counts['Count'].sum()
    category_counts['Percentage'] = (category_counts['Count'] / total_calls) if total_calls > 0 else 0

    y_axis_option = st.radio(get_text("behavior_view_y_axis_option"), get_text("behavior_view_y_axis_options"), horizontal=True, key="behavior_y_axis_option")

    if y_axis_option == get_text("behavior_view_y_axis_options")[0]:
        y_field, y_title, y_axis_format = 'Count', get_text("behavior_view_y_axis_count"), 's'
    else:
        y_field, y_title, y_axis_format = 'Percentage', get_text("behavior_view_y_axis_percentage"), '%'

    chart = alt.Chart(category_counts).mark_bar().encode(
        x=alt.X('Category', sort=category_order, title=get_text("behavior_view_x_axis"), axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_axis_format)),
        tooltip=[
            alt.Tooltip('Category', title=get_text("behavior_view_tooltip_category")),
            alt.Tooltip('Count', title=get_text("behavior_view_tooltip_count")),
            alt.Tooltip('Percentage', title=get_text("behavior_view_tooltip_percentage"), format='.1%')
        ]
    ).properties(title=get_text("behavior_view_chart_title").format(analysis_subject_name=analysis_subject_name))
    st.altair_chart(chart, use_container_width=True)

    st.subheader(get_text("behavior_view_data_subheader"))
    st.dataframe(category_counts.style.format({'Percentage': '{:.1%}'}), use_container_width=True, hide_index=True)

def display_call_time_analysis_view(df, selected_group):
    st.header(get_text("call_time_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    agent_list = [get_text("behavior_view_all_agents")] + sorted(df['Agent Name'].unique())
    if len(agent_list) == 1:
        st.info(get_text("behavior_view_no_data_in_team").format(selected_group=selected_group))
        return
        
    selected_agent = st.selectbox(get_text("behavior_view_agent_selector"), agent_list, key="call_time_agent_select")

    if selected_agent == get_text("behavior_view_all_agents"):
        df_to_analyze = df.copy()
        analysis_subject_name = f"{selected_group} {get_text('behavior_view_all_agents')}" if selected_group != get_text("all_teams") else f"{get_text('all_teams')} {get_text('behavior_view_all_agents')}"
    else:
        df_to_analyze = df[df['Agent Name'] == selected_agent].copy()
        analysis_subject_name = selected_agent

    analysis_period = st.radio(get_text("behavior_view_analysis_period"), get_text("behavior_view_period_options"), horizontal=True, key="call_time_period")

    if analysis_period == get_text("behavior_view_period_options")[0]:
        available_dates = sorted(df_to_analyze['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_date = st.selectbox(get_text("daily_view_date_selector"), available_dates, key="call_time_date_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.date == selected_date]
    else:
        available_months = sorted(df_to_analyze['Date'].dt.month.unique())
        if not available_months:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_month = st.selectbox(get_text("monthly_view_month_selector"), available_months, format_func=lambda x: f"2025-{x:02d}", key="call_time_month_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.month == selected_month]

    if df_filtered.empty:
        st.info(get_text("daily_view_no_records_for_date").format(selected_date="selected period"))
        return

    granularity_map = dict(zip(get_text("call_time_view_granularity_options"), ["小時", "30分鐘", "15分鐘"]))
    time_granularity_display = st.selectbox(get_text("call_time_view_granularity_selector"), get_text("call_time_view_granularity_options"), key="time_granularity")
    time_granularity = granularity_map[time_granularity_display]

    if time_granularity == "小時":
        df_filtered['Time_Interval_Label'] = df_filtered['Call Assigned'].dt.strftime('%H:00')
    elif time_granularity == "30分鐘":
        df_filtered['Time_Interval_Label'] = df_filtered['Call Assigned'].dt.floor('30min').dt.strftime('%H:%M')
    else:
        df_filtered['Time_Interval_Label'] = df_filtered['Call Assigned'].dt.floor('15min').dt.strftime('%H:%M')

    hourly_stats = df_filtered.groupby('Time_Interval_Label').agg(
        Total_Outbound_Calls=('Case No', 'size'),
        Total_Connected_Calls=('Connected', 'sum')
    ).reset_index()

    hourly_stats['Time_Interval_Sort'] = pd.to_datetime(hourly_stats['Time_Interval_Label'], format='%H:%M').dt.time
    hourly_stats = hourly_stats.sort_values('Time_Interval_Sort').drop(columns='Time_Interval_Sort')

    hourly_stats['Connection_Rate'] = np.where(hourly_stats['Total_Outbound_Calls'] > 0, hourly_stats['Total_Connected_Calls'] / hourly_stats['Total_Outbound_Calls'], 0)
    
    total_outbound = hourly_stats['Total_Outbound_Calls'].sum()
    total_connected = hourly_stats['Total_Connected_Calls'].sum()
    hourly_stats['Outbound_Call_Percentage'] = (hourly_stats['Total_Outbound_Calls'] / total_outbound) if total_outbound > 0 else 0
    hourly_stats['Connected_Call_Percentage'] = (hourly_stats['Total_Connected_Calls'] / total_connected) if total_connected > 0 else 0
    
    display_mode = st.radio(get_text("call_time_view_display_mode"), get_text("call_time_view_display_mode_options"), horizontal=True, key="call_time_display_mode")

    if display_mode != get_text("call_time_view_display_mode_options")[2]:
        y_axis_mode = st.radio(get_text("call_time_view_y_axis_mode"), get_text("call_time_view_y_axis_options"), horizontal=True, key="call_time_y_axis_mode")
    else:
        y_axis_mode = get_text("call_time_view_y_axis_options")[0]
        st.caption(get_text("call_time_view_combined_chart_caption"))

    st.subheader(get_text("call_time_view_chart_title").format(analysis_subject_name=analysis_subject_name, time_granularity=time_granularity_display))

    y_field, y_title, chart = None, None, None

    if display_mode == get_text("call_time_view_display_mode_options")[0]: # Total Outbound
        if y_axis_mode == get_text("call_time_view_y_axis_options")[0]: # Count
            y_field, y_title, y_format = 'Total_Outbound_Calls', get_text("call_time_view_y_outbound_count"), 's'
        else: # Percentage
            y_field, y_title, y_format = 'Outbound_Call_Percentage', get_text("call_time_view_y_outbound_ratio"), '%'
        
        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title=get_text("call_time_view_x_axis"), axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_format)),
            tooltip=[alt.Tooltip('Time_Interval_Label', title=get_text("call_time_view_tooltip_time")),
                     alt.Tooltip('Total_Outbound_Calls', title=get_text("call_time_view_tooltip_outbound_count")),
                     alt.Tooltip('Outbound_Call_Percentage', title=get_text("call_time_view_tooltip_outbound_ratio"), format='.1%')]
        ).properties(title=get_text("call_time_view_chart_title_outbound").format(analysis_subject_name=analysis_subject_name, y_title=y_title, time_granularity=time_granularity_display))

    elif display_mode == get_text("call_time_view_display_mode_options")[1]: # Total Connected
        if y_axis_mode == get_text("call_time_view_y_axis_options")[0]: # Count
            y_field, y_title, y_format = 'Total_Connected_Calls', get_text("call_time_view_y_connected_count"), 's'
        else: # Percentage
            y_field, y_title, y_format = 'Connected_Call_Percentage', get_text("call_time_view_y_connected_ratio"), '%'
        
        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title=get_text("call_time_view_x_axis"), axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_format)),
            tooltip=[alt.Tooltip('Time_Interval_Label', title=get_text("call_time_view_tooltip_time")),
                     alt.Tooltip('Total_Connected_Calls', title=get_text("call_time_view_tooltip_connected_count")),
                     alt.Tooltip('Connected_Call_Percentage', title=get_text("call_time_view_tooltip_connected_ratio"), format='.1%')]
        ).properties(title=get_text("call_time_view_chart_title_connected").format(analysis_subject_name=analysis_subject_name, y_title=y_title, time_granularity=time_granularity_display))

    else: # Combined Analysis
        y_field, y_title = 'Total_Outbound_Calls', get_text("call_time_view_y_outbound_count")

        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title=get_text("call_time_view_x_axis"), axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format='s')),
            color=alt.Color('Connection_Rate', scale=alt.Scale(scheme='blues', domain=[0, 0.50]), title=get_text("call_time_view_color_legend")),
            tooltip=[alt.Tooltip('Time_Interval_Label', title=get_text("call_time_view_tooltip_time")),
                     alt.Tooltip('Total_Outbound_Calls', title=get_text("call_time_view_tooltip_outbound_count")),
                     alt.Tooltip('Outbound_Call_Percentage', title=get_text("call_time_view_tooltip_outbound_ratio"), format='.1%'),
                     alt.Tooltip('Total_Connected_Calls', title=get_text("call_time_view_tooltip_connected_count")),
                     alt.Tooltip('Connection_Rate', title=get_text("call_time_view_tooltip_connection_rate"), format='.1%')]
        ).properties(title=get_text("call_time_view_chart_title_combined").format(analysis_subject_name=analysis_subject_name, y_title=y_title, time_granularity=time_granularity_display))
    
    st.altair_chart(chart, use_container_width=True)

    st.subheader(get_text("behavior_view_data_subheader"))
    st.dataframe(
        hourly_stats[[
            'Time_Interval_Label', 'Total_Outbound_Calls', 'Outbound_Call_Percentage',
            'Total_Connected_Calls', 'Connected_Call_Percentage', 'Connection_Rate'
        ]].style.format({
            'Connection_Rate': '{:.1%}',
            'Outbound_Call_Percentage': '{:.1%}',
            'Connected_Call_Percentage': '{:.1%}'
        }), 
        use_container_width=True, 
        hide_index=True
    )

def display_profiling_view(df, selected_group):
    st.header(get_text("profiling_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()
    
    agent_list = sorted(df['Agent Name'].unique())
    if not agent_list:
        st.info(get_text("behavior_view_no_data_in_team").format(selected_group=selected_group))
        return
        
    if 'profiling_benchmark_select' not in st.session_state:
        st.session_state.profiling_benchmark_select = []

    col1, col2, col3 = st.columns([2, 2, 1.5])
    with col1:
        selected_agent = st.selectbox(get_text("profiling_view_agent_selector"), agent_list, key="profiling_agent_select")
    
    benchmark_options = [agent for agent in agent_list if agent != selected_agent]
    st.session_state.profiling_benchmark_select = [
        agent for agent in st.session_state.profiling_benchmark_select if agent in benchmark_options
    ]

    with col2:
        benchmark_agents = st.multiselect(
            get_text("profiling_view_benchmark_selector"), 
            benchmark_options, 
            key="profiling_benchmark_select"
        )
    with col3:
        analysis_period = st.radio(get_text("profiling_view_period_selector"), get_text("profiling_view_period_options"), horizontal=True, key="profiling_period")

    if analysis_period == get_text("profiling_view_period_options")[0]: # Daily
        available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(get_text("profiling_view_no_date_warning"))
            return
        selected_date = st.selectbox(get_text("daily_view_date_selector"), available_dates, key="profiling_date_select")
        df_period = df[df['Date'].dt.date == selected_date]
    else: # Monthly
        available_months = sorted(df['Date'].dt.month.unique())
        if not available_months:
            st.warning(get_text("profiling_view_no_month_warning"))
            return
        selected_month = st.selectbox(get_text("monthly_view_month_selector"), available_months, format_func=lambda x: f"2025-{x:02d}", key="profiling_month_select")
        df_period = df[df['Date'].dt.month == selected_month]

    if df_period.empty:
        st.info(get_text("daily_view_no_records_for_date").format(selected_date="selected period"))
        return

    df_agent = df_period[df_period['Agent Name'] == selected_agent]
    
    df_benchmark = pd.DataFrame()
    if benchmark_agents:
        df_benchmark = df_period[df_period['Agent Name'].isin(benchmark_agents)]

    st.subheader(get_text("profiling_view_time_chart_title").format(selected_agent=selected_agent))

    df_agent['Time_Interval'] = df_agent['Call Assigned'].dt.floor('H').dt.strftime('%H:00')
    agent_time_stats = df_agent['Time_Interval'].value_counts().reset_index()
    agent_time_stats.columns = ['Time_Interval', 'Agent_Calls']

    if not df_benchmark.empty:
        df_benchmark['Time_Interval'] = df_benchmark['Call Assigned'].dt.floor('H').dt.strftime('%H:00')
        benchmark_time_stats = df_benchmark.groupby('Time_Interval')['Case No'].count()
        num_benchmark_agents = df_benchmark['Agent ID'].nunique()
        benchmark_avg_time_stats = (benchmark_time_stats / num_benchmark_agents).reset_index()
        benchmark_avg_time_stats.columns = ['Time_Interval', 'Benchmark_Avg_Calls']
        
        comparison_df = pd.merge(agent_time_stats, benchmark_avg_time_stats, on='Time_Interval', how='outer').fillna(0)
    else:
        comparison_df = agent_time_stats
        comparison_df['Benchmark_Avg_Calls'] = 0

    comparison_df = comparison_df.sort_values('Time_Interval')

    base = alt.Chart(comparison_df).encode(x=alt.X('Time_Interval', title=get_text("call_time_view_x_axis"), sort=None, axis=alt.Axis(labelAngle=0)))
    bar = base.mark_bar().encode(
        y=alt.Y('Agent_Calls', title=get_text("profiling_view_time_y_axis")),
        tooltip=[alt.Tooltip('Time_Interval', title=get_text("profiling_view_time_tooltip_time")), alt.Tooltip('Agent_Calls', title=get_text("profiling_view_time_tooltip_agent"))]
    )
    
    chart_layers = [bar]
    if not df_benchmark.empty:
        line = base.mark_line(color='red', strokeDash=[5,5]).encode(
            y=alt.Y('Benchmark_Avg_Calls', title=get_text("profiling_view_time_y_axis")),
        )
        points = base.mark_point(color='red', filled=True, size=60).encode(
            y=alt.Y('Benchmark_Avg_Calls'),
            tooltip=[alt.Tooltip('Time_Interval', title=get_text("profiling_view_time_tooltip_time")), alt.Tooltip('Benchmark_Avg_Calls', title=get_text("profiling_view_time_tooltip_benchmark"), format='.1f')]
        )
        chart_layers.extend([line, points])

    st.altair_chart(
        alt.layer(*chart_layers).resolve_scale(y='shared'),
        use_container_width=True
    )

    st.subheader(get_text("profiling_view_duration_chart_title").format(selected_agent=selected_agent))

    def categorize_talk_duration(seconds):
        if seconds <= 5: return "~5s"
        elif 5 < seconds <= 10: return "5s - 10s"
        elif 10 < seconds <= 30: return "10s - 30s"
        elif 30 < seconds <= 60: return "30s - 1min"
        elif 60 < seconds <= 120: return "1min - 2min"
        elif 120 < seconds <= 180: return "2min - 3min"
        else: return "> 3min"
    
    category_order = ["~5s", "5s - 10s", "10s - 30s", "30s - 1min", "1min - 2min", "2min - 3min", "> 3min"]

    df_agent_valid_talk = df_agent[df_agent['Talk Durations'].dt.total_seconds() > 0]
    if not df_agent_valid_talk.empty:
        df_agent_valid_talk['Category'] = df_agent_valid_talk['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)
        agent_duration_dist = df_agent_valid_talk['Category'].value_counts(normalize=True).reset_index()
        agent_duration_dist.columns = ['Category', 'Agent_Ratio']
    else:
        agent_duration_dist = pd.DataFrame(columns=['Category', 'Agent_Ratio'])

    if not df_benchmark.empty:
        df_benchmark_valid_talk = df_benchmark[df_benchmark['Talk Durations'].dt.total_seconds() > 0]
        if not df_benchmark_valid_talk.empty:
            df_benchmark_valid_talk['Category'] = df_benchmark_valid_talk['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)
            benchmark_duration_dist = df_benchmark_valid_talk['Category'].value_counts(normalize=True).reset_index()
            benchmark_duration_dist.columns = ['Category', 'Benchmark_Avg_Ratio']
            duration_comparison_df = pd.merge(agent_duration_dist, benchmark_duration_dist, on='Category', how='outer').fillna(0)
        else:
            duration_comparison_df = agent_duration_dist
            duration_comparison_df['Benchmark_Avg_Ratio'] = 0
    else:
        duration_comparison_df = agent_duration_dist
        duration_comparison_df['Benchmark_Avg_Ratio'] = 0

    base_dur = alt.Chart(duration_comparison_df).encode(x=alt.X('Category', title=get_text("behavior_view_x_axis"), sort=category_order, axis=alt.Axis(labelAngle=0)))
    bar_dur = base_dur.mark_bar().encode(
        y=alt.Y('Agent_Ratio', title=get_text("profiling_view_duration_y_axis"), axis=alt.Axis(format='%')),
        tooltip=[alt.Tooltip('Category', title=get_text("profiling_view_duration_tooltip_category")), alt.Tooltip('Agent_Ratio', title=get_text("profiling_view_duration_tooltip_agent"), format='.1%')]
    )
    
    chart_dur_layers = [bar_dur]
    if not df_benchmark.empty:
        line_dur = base_dur.mark_line(color='red', strokeDash=[5,5]).encode(
            y=alt.Y('Benchmark_Avg_Ratio', title=get_text("profiling_view_duration_y_axis"), axis=alt.Axis(format='%')),
        )
        points_dur = base_dur.mark_point(color='red', filled=True, size=60).encode(
            y=alt.Y('Benchmark_Avg_Ratio'),
            tooltip=[alt.Tooltip('Category', title=get_text("profiling_view_duration_tooltip_category")), alt.Tooltip('Benchmark_Avg_Ratio', title=get_text("profiling_view_duration_tooltip_benchmark"), format='.1%')]
        )
        chart_dur_layers.extend([line_dur, points_dur])

    st.altair_chart(
        alt.layer(*chart_dur_layers).resolve_scale(y='shared'),
        use_container_width=True
    )

# --- 主應用程式 ---
def main():
    # --- 【V8.0 升級】語言切換器 ---
    st.sidebar.header(get_text("lang_selector_label"))
    lang_choice = st.sidebar.radio(
        "", 
        ["中文", "English"], 
        index=0 if st.session_state.lang == 'zh_tw' else 1,
        label_visibility="collapsed"
    )
    
    # 更新 session_state
    new_lang = 'zh_tw' if lang_choice == '中文' else 'en'
    if st.session_state.lang != new_lang:
        st.session_state.lang = new_lang
        st.rerun() # 當語言改變時，重新執行整個腳本

    st.title(get_text("main_title"))
    
    df = load_data()
    thresholds = load_thresholds("各組每日撥通數上下限.xlsx")

    if df is not None:
        st.sidebar.header(get_text("sidebar_view_mode"))
        
        # 使用 get_text 獲取選項
        view_mode_options = get_text("view_modes")
        view_mode = st.sidebar.radio(
            "",
            view_mode_options,
            label_visibility="collapsed"
        )
        
        # 建立選項到函數的映射
        view_functions = {
            view_mode_options[0]: display_daily_view,
            view_mode_options[1]: display_monthly_view,
            view_mode_options[2]: display_behavior_analysis_view,
            view_mode_options[3]: display_call_time_analysis_view,
            view_mode_options[4]: display_profiling_view,
        }

        st.sidebar.header(get_text("sidebar_filter_team"))
        if 'Group' in df.columns:
            df['Group'] = df['Group'].astype(str)
            all_groups = [get_text("all_teams")] + [g for g in CUSTOM_GROUP_ORDER if g in df['Group'].unique()]
        else:
            all_groups = [get_text("all_teams")]
        
        selected_group = st.sidebar.selectbox("", all_groups, label_visibility="collapsed")

        # 根據選擇的 view_mode 呼叫對應的函數
        if view_mode in view_functions:
            if view_mode in [view_mode_options[0], view_mode_options[1]]:
                 view_functions[view_mode](df, selected_group, thresholds)
            else:
                 view_functions[view_mode](df, selected_group)
        
    else:
        st.warning(get_text("data_load_failed"))

if __name__ == "__main__":
    main()
