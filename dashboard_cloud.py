import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- 【V18.2 升級】同步本地版優化，實現動態適應座標軸 ---
LANGUAGES = {
    "zh_tw": {
        "page_title": "電話催收過程指標追蹤儀表板 (雲端生產版 V18.2)",
        "main_title": "電話催收過程指標追蹤儀表板 (整合版)",
        "lang_selector_label": "語言 (Language)",
        "load_data_success": "已透過 Google API 安全載入主數據。",
        "load_data_error": "透過 Google API 載入主數據時發生錯誤。",
        "load_thresholds_success": "已從 Git 儲存庫成功載入績效上下限設定。",
        "load_thresholds_warning": "注意：在 Git 儲存庫中找不到績效上下限設定檔 '{path}'。顏色標記功能將無法使用。",
        "load_thresholds_error": "從 Git 儲存庫載入績效上下限設定檔時發生錯誤: {e}",
        "data_load_failed": "資料未能成功載入，請根據上方的錯誤訊息檢查您的設定。",
        "sidebar_view_mode": "選擇檢視模式",
        "sidebar_filter_team": "篩選團隊",
        "view_modes": ["催員每日撥打狀況報告", "月度催員接通數儀表板", "催員催收行為分析", "催員時點撥打與接通分析", "催員行為與高績效人員比較", "覆蓋率與績效關聯分析"],
        "all_teams": "所有團隊",
        # Daily View
        "daily_view_header": "催員每日撥打狀況報告",
        "daily_view_no_data_for_team": "在選定的團隊中，沒有可用的資料。",
        "daily_view_date_selector": "選擇日期",
        "daily_view_no_records_for_date": "在 {selected_date} 沒有通話紀錄。",
        "daily_view_focus_info": "已帶入 {date} 的 {agent} 資料。",
        "daily_view_columns": {
            '組別': '組別', 'ID': 'ID', '姓名': '姓名',
            '在手案件數': '在手案件數',
            '總撥打數': '總撥打數',
            '總處理案件數': '總處理案件數',
            '撥打案件覆蓋率': '撥打案件覆蓋率',
            '總成功撥打數': '總成功撥打數',
            '總成功案件數': '總成功案件數',
            '接通案件覆蓋率': '接通案件覆蓋率',
            '重複撥打率': '重複撥打率',
            '總通話時長': '總通話時長',
            '平均通話時長': '平均通話時長',
            '當日回收金額': '當日回收金額'
        },
        # Monthly View
        "monthly_view_header": "月度催員接通數與回收金額儀表板",
        "monthly_view_no_month_data": "在選定的團隊中，沒有可用的月份資料。",
        "monthly_view_month_selector": "選擇月份",
        "monthly_view_no_data_for_month": "在選定的月份中，沒有資料可供顯示。",
        "monthly_view_no_recovery_data": "本月無回收金額資料，無法顯示趨勢分析。",
        "monthly_view_tab_trend": "趨勢分析",
        "monthly_view_tab_heatmap": "熱力圖分析",
        "monthly_view_kpi_total_connections": "本月總接通數",
        "monthly_view_kpi_total_amount": "本月總回收金額",
        "monthly_view_kpi_avg_amount_per_call": "平均每次接通回收金額",
        "monthly_view_trend_subheader": "宏觀趨勢分析 (接通數 vs. 回收金額)",
        "monthly_view_heatmap_subheader": "各組每日績效熱力圖",
        "monthly_view_heatmap_metric_selector": "選擇熱力圖指標",
        "heatmap_metric_connections": "總接通數",
        "heatmap_metric_total_calls": "總撥打數",
        "heatmap_metric_called_coverage": "撥打案件覆蓋率",
        "monthly_view_jump_header": "快速跳轉至每日報告",
        "monthly_view_jump_agent_label": "選擇催員",
        "monthly_view_jump_date_label": "選擇日期",
        "monthly_view_jump_button": "查看每日報告",
        "monthly_view_y_axis_calls": "總接通數",
        "monthly_view_y_axis_amount": "總回收金額",
        "monthly_view_tooltip_date": "日期",
        "monthly_view_tooltip_connections": "接通數",
        "monthly_view_tooltip_amount": "回收金額",
        # Behavior Analysis
        "behavior_view_header": "催員催收行為分析",
        "behavior_view_tab_original": "通話量分佈",
        "behavior_view_tab_effective": "通話效率分析 (量 vs. 轉換率)",
        "behavior_view_no_recovery_data": "選定範圍內無回收資料，無法進行有效行為分析。",
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
        "behavior_view_effective_chart_title": "{analysis_subject_name} 的通話效率分析 (投入 vs. 產出)",
        "behavior_view_x_axis": "通話時長區間",
        "behavior_view_y_axis_count": "總通話筆數 (投入)",
        "behavior_view_y_axis_conversion_rate": "回收轉換率 (產出)",
        "behavior_view_tooltip_category": "時長區間",
        "behavior_view_tooltip_count": "通話筆數",
        "behavior_view_tooltip_recovered_cases": "回收案件數",
        "behavior_view_tooltip_conversion_rate": "回收轉換率",
        "behavior_view_tooltip_percentage": "通話比例",
        "behavior_view_data_subheader": "詳細數據",
        # Call Time Analysis
        "call_time_view_header": "催員時點撥打與接通分析",
        "call_time_view_granularity_selector": "選擇時間粒度",
        "call_time_view_granularity_options": ["小時", "30分鐘", "15分鐘"],
        "call_time_view_display_mode": "選擇顯示模式",
        "call_time_view_display_mode_options": ["總撥出電話數", "總接通電話數", "綜合分析 (撥出數 + 熱力圖)"],
        "call_time_view_heatmap_metric": "熱力圖指標",
        "call_time_view_heatmap_options": ["接通率", "平均回收金額"],
        "call_time_view_no_recovery_data": "選定範圍內無回收資料，無法顯示平均回收金額熱力圖。",
        "call_time_view_y_axis_mode": "選擇 Y 軸顯示方式",
        "call_time_view_y_axis_options": ["數量", "比例"],
        "call_time_view_combined_chart_caption": "註：為清晰呈現投入量與效率的關係，綜合分析圖 Y 軸固定為「數量」。",
        "call_time_view_chart_title": "{analysis_subject_name} 的通話時點分佈 ({time_granularity})",
        "call_time_view_chart_title_outbound": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_connected": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_combined": "{analysis_subject_name} {y_title}與{metric_name} ({time_granularity})",
        "call_time_view_y_outbound_count": "總撥出電話數",
        "call_time_view_y_outbound_ratio": "撥出電話比例",
        "call_time_view_y_connected_count": "總接通電話數",
        "call_time_view_y_connected_ratio": "接通電話比例",
        "call_time_view_x_axis": "時間區間",
        "call_time_view_color_legend_connection": "接通率",
        "call_time_view_color_legend_amount": "平均回收金額",
        "call_time_view_tooltip_time": "時間區間",
        "call_time_view_tooltip_outbound_count": "總撥出數",
        "call_time_view_tooltip_outbound_ratio": "撥出比例",
        "call_time_view_tooltip_connected_count": "總接通數",
        "call_time_view_tooltip_connected_ratio": "接通比例",
        "call_time_view_tooltip_connection_rate": "接通率",
        "call_time_view_tooltip_avg_amount": "平均回收金額",
        # Profiling View
        "profiling_view_header": "催員行為與高績效人員比較 (Agent vs. Benchmark)",
        "profiling_view_agent_selector": "選擇要分析的催員",
        "profiling_view_benchmark_selector": "選擇績效標竿群組 (可多選)",
        "profiling_view_period_selector": "選擇分析區間",
        "profiling_view_period_options": ["單日", "月份"],
        "profiling_view_no_date_warning": "資料中沒有可用的日期。",
        "profiling_view_no_month_warning": "資料中沒有可用的月份。",
        "profiling_view_behavior_subheader": "行為模式比較",
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
        "profiling_view_performance_subheader": "績效指標比較",
        "profiling_view_performance_chart_title": "關鍵績效指標：{selected_agent} vs. 標竿群組",
        "profiling_view_performance_metric": "指標",
        "profiling_view_performance_value": "數值",
        "profiling_view_performance_group": "比較對象",
        "profiling_view_performance_agent": "個人",
        "profiling_view_performance_benchmark": "標竿",
        "profiling_metric_recovery_amount": "回收總金額",
        "profiling_metric_connected_coverage": "接通案件覆蓋率",
        "profiling_metric_avg_talk_duration": "平均通話時長 (秒)",
        # V18.2 Coverage-Performance View
        "coverage_view_header": "覆蓋率與績效關聯分析",
        "coverage_view_agent_selector": "選擇焦點分析催員",
        "coverage_view_no_data": "選定範圍內沒有足夠的數據進行關聯分析。",
        "coverage_view_chart_subheader": "每日績效分佈 (投入 vs. 產出)",
        "coverage_view_x_axis": "接通案件覆蓋率 (投入)",
        "coverage_view_y_axis": "當日回收金額 (產出)",
        "coverage_view_chart_title": "{month} 績效分佈：{agent} vs. 標竿群組",
        "coverage_view_kpi_subheader": "關鍵指標比較 (個人 vs. 標竿平均)",
        "coverage_kpi_avg_coverage": "期間平均接通覆蓋率",
        "coverage_kpi_avg_amount": "期間日均回收金額",
        "coverage_kpi_total_amount": "期間總回收金額",
    },
    "en": {
        "page_title": "Collector Performance Dashboard (Cloud Production V18.2)",
        "main_title": "Collector Performance Dashboard (Enriched)",
        "lang_selector_label": "Language",
        "load_data_success": "Successfully loaded main data via Google API.",
        "load_data_error": "An error occurred while loading main data via Google API.",
        "load_thresholds_success": "Successfully loaded performance thresholds from Git repository.",
        "load_thresholds_warning": "Warning: Threshold file not found in Git repository at '{path}'. Color styling will be disabled.",
        "load_thresholds_error": "Error loading performance thresholds from Git repository: {e}",
        "data_load_failed": "Failed to load data. Please check your settings based on the error message above.",
        "sidebar_view_mode": "Select View Mode",
        "sidebar_filter_team": "Filter Team",
        "view_modes": ["Daily Agent Report", "Monthly Dashboard", "Behavior Analysis", "Call Time Analysis", "Agent Profiling", "Coverage & Performance Analysis"],
        "all_teams": "All Teams",
        # Daily View
        "daily_view_header": "Daily Agent Report",
        "daily_view_no_data_for_team": "No data available for the selected team.",
        "daily_view_date_selector": "Select Date",
        "daily_view_no_records_for_date": "No call records on {selected_date}.",
        "daily_view_focus_info": "Showing data for {agent} on {date}.",
        "daily_view_columns": {
            '組別': 'Group', 'ID': 'ID', '姓名': 'Name',
            '在手案件數': 'Cases on Hand',
            '總撥打數': 'Total Calls',
            '總處理案件數': 'Called Cases',
            '撥打案件覆蓋率': 'Called Coverage',
            '總成功撥打數': 'Connected Calls',
            '總成功案件數': 'Connected Cases',
            '接通案件覆蓋率': 'Connected Coverage',
            '重複撥打率': 'Repetition Rate',
            '總通話時長': 'Total Talk Duration',
            '平均通話時長': 'Avg. Talk Duration',
            '當日回收金額': 'Daily Received Amount'
        },
        # Monthly View
        "monthly_view_header": "Monthly Connection & Recovery Dashboard",
        "monthly_view_no_month_data": "No month data available for the selected team.",
        "monthly_view_month_selector": "Select Month",
        "monthly_view_no_data_for_month": "No data to display for the selected month.",
        "monthly_view_no_recovery_data": "No recovery data for this month, trend analysis is unavailable.",
        "monthly_view_tab_trend": "Trend Analysis",
        "monthly_view_tab_heatmap": "Heatmap Analysis",
        "monthly_view_kpi_total_connections": "Total Connections This Month",
        "monthly_view_kpi_total_amount": "Total Amount Received This Month",
        "monthly_view_kpi_avg_amount_per_call": "Avg. Amount / Connection",
        "monthly_view_trend_subheader": "Macro Trend Analysis (Connections vs. Amount)",
        "monthly_view_heatmap_subheader": "Daily Performance Heatmap",
        "monthly_view_heatmap_metric_selector": "Select Heatmap Metric",
        "heatmap_metric_connections": "Total Connections",
        "heatmap_metric_total_calls": "Total Calls",
        "heatmap_metric_called_coverage": "Called Coverage",
        "monthly_view_jump_header": "Quick Access to Daily Report",
        "monthly_view_jump_agent_label": "Select Agent",
        "monthly_view_jump_date_label": "Select Date",
        "monthly_view_jump_button": "View Daily Report",
        "monthly_view_y_axis_calls": "Total Connections",
        "monthly_view_y_axis_amount": "Total Received Amount",
        "monthly_view_tooltip_date": "Date",
        "monthly_view_tooltip_connections": "Connections",
        "monthly_view_tooltip_amount": "Received Amount",
        # Behavior Analysis
        "behavior_view_header": "Agent Behavior Analysis",
        "behavior_view_tab_original": "Call Volume Distribution",
        "behavior_view_tab_effective": "Call Efficiency Analysis (Volume vs. Conversion)",
        "behavior_view_no_recovery_data": "No recovery data in the selected period, efficiency analysis is unavailable.",
        "behavior_view_agent_selector": "Select Agent or All",
        "behavior_view_all_agents": "All Agents",
        "behavior_view_no_data_in_team": "No data available in team '{selected_group}'.",
        "behavior_view_no_records_warning": "{analysis_subject_name} has no call records for the selected period.",
        "analysis_period": "Select Analysis Period",
        "behavior_view_period_options": ["Daily Analysis", "Monthly Analysis"],
        "behavior_view_no_valid_talk_duration": "No records with valid talk duration in the selected period.",
        "behavior_view_y_axis_option": "Select Y-Axis Display",
        "behavior_view_y_axis_options": ["Call Count", "Call Percentage"],
        "behavior_view_chart_title": "{analysis_subject_name} Talk Duration Distribution",
        "behavior_view_effective_chart_title": "{analysis_subject_name}'s Call Efficiency Analysis (Input vs. Output)",
        "behavior_view_x_axis": "Talk Duration Category",
        "behavior_view_y_axis_count": "Total Calls (Input)",
        "behavior_view_y_axis_conversion_rate": "Recovery Conversion Rate (Output)",
        "behavior_view_tooltip_category": "Duration Category",
        "behavior_view_tooltip_count": "Call Count",
        "behavior_view_tooltip_recovered_cases": "Recovered Cases",
        "behavior_view_tooltip_conversion_rate": "Conversion Rate",
        "behavior_view_tooltip_percentage": "Call Percentage",
        "behavior_view_data_subheader": "Detailed Data",
        # Call Time Analysis
        "call_time_view_header": "Agent Call Time Analysis",
        "call_time_view_granularity_selector": "Select Time Granularity",
        "call_time_view_granularity_options": ["Hourly", "30-Min", "15-Min"],
        "call_time_view_display_mode": "Select Display Mode",
        "call_time_view_display_mode_options": ["Total Outbound Calls", "Total Connected Calls", "Combined Analysis (Outbound + Heatmap)"],
        "call_time_view_heatmap_metric": "Heatmap Metric",
        "call_time_view_heatmap_options": ["Connection Rate", "Avg. Received Amount"],
        "call_time_view_no_recovery_data": "No recovery data in the selected period, amount heatmap is unavailable.",
        "call_time_view_y_axis_mode": "Select Y-Axis Display",
        "call_time_view_y_axis_options": ["Count", "Percentage"],
        "call_time_view_combined_chart_caption": "Note: For clarity, the Y-axis for Combined Analysis is fixed to 'Count'.",
        "call_time_view_chart_title": "{analysis_subject_name}'s Call Time Distribution ({time_granularity})",
        "call_time_view_chart_title_outbound": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_connected": "{analysis_subject_name} {y_title} ({time_granularity})",
        "call_time_view_chart_title_combined": "{analysis_subject_name} {y_title} & {metric_name} ({time_granularity})",
        "call_time_view_y_outbound_count": "Total Outbound Calls",
        "call_time_view_y_outbound_ratio": "Outbound Call Ratio",
        "call_time_view_y_connected_count": "Total Connected Calls",
        "call_time_view_y_connected_ratio": "Connected Call Ratio",
        "call_time_view_x_axis": "Time Interval",
        "call_time_view_color_legend_connection": "Connection Rate",
        "call_time_view_color_legend_amount": "Avg. Received Amount",
        "call_time_view_tooltip_time": "Time Interval",
        "call_time_view_tooltip_outbound_count": "Total Outbound",
        "call_time_view_tooltip_outbound_ratio": "Outbound Ratio",
        "call_time_view_tooltip_connected_count": "Total Connected",
        "call_time_view_tooltip_connected_ratio": "Connected Ratio",
        "call_time_view_tooltip_connection_rate": "Connection Rate",
        "call_time_view_tooltip_avg_amount": "Avg. Received Amount",
        # Profiling View
        "profiling_view_header": "Agent vs. Benchmark Profiling",
        "profiling_view_agent_selector": "Select Agent to Analyze",
        "profiling_view_benchmark_selector": "Select Benchmark Group (multi-select)",
        "profiling_view_period_selector": "Select Analysis Period",
        "profiling_view_period_options": ["Daily", "Monthly"],
        "profiling_view_no_date_warning": "No available dates in the data.",
        "profiling_view_no_month_warning": "No available months in the data.",
        "profiling_view_behavior_subheader": "Behavioral Pattern Comparison",
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
        "profiling_view_performance_subheader": "Performance Metric Comparison",
        "profiling_view_performance_chart_title": "Key Performance Indicators: {selected_agent} vs. Benchmark",
        "profiling_view_performance_metric": "Metric",
        "profiling_view_performance_value": "Value",
        "profiling_view_performance_group": "Group",
        "profiling_view_performance_agent": "Agent",
        "profiling_view_performance_benchmark": "Benchmark",
        "profiling_metric_recovery_amount": "Total Recovery Amount",
        "profiling_metric_connected_coverage": "Connected Case Coverage",
        "profiling_metric_avg_talk_duration": "Avg. Talk Duration (sec)",
        # V18.2 Coverage-Performance View
        "coverage_view_header": "Coverage & Performance Correlation Analysis",
        "coverage_view_agent_selector": "Select Agent for Focus Analysis",
        "coverage_view_no_data": "Not enough data in the selected range for correlation analysis.",
        "coverage_view_chart_subheader": "Daily Performance Distribution (Input vs. Output)",
        "coverage_view_x_axis": "Connected Case Coverage (Input)",
        "coverage_view_y_axis": "Daily Received Amount (Output)",
        "coverage_view_chart_title": "{month} Performance Distribution: {agent} vs. Benchmark Group",
        "coverage_view_kpi_subheader": "KPI Comparison (Agent vs. Benchmark Average)",
        "coverage_kpi_avg_coverage": "Avg. Connected Coverage",
        "coverage_kpi_avg_amount": "Avg. Daily Recovery Amount",
        "coverage_kpi_total_amount": "Total Recovery Amount",
    }
}

# --- 初始化 Session State ---
if 'lang' not in st.session_state:
    st.session_state.lang = "zh_tw"

# --- 語言文本獲取函數 ---
def get_text(key):
    return LANGUAGES[st.session_state.lang].get(key, key)

# --- 頁面配置 ---
st.set_page_config(
    page_title=get_text("page_title"),
    page_icon="🚀",
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

@st.cache_data(ttl=600)
def download_gdrive_file(_creds, file_id):
    service = build('drive', 'v3', credentials=_creds)
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

# --- 透過 Google 官方 API 載入數據 ---
@st.cache_data(ttl=600)
def load_data(_creds):
    try:
        main_file_id = "1O9Po49F7TkV4c_Q8Y0yaufhI15HFKGyT"
        main_fh = download_gdrive_file(_creds, main_file_id)
        df = pd.read_csv(main_fh)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Talk Durations'] = pd.to_timedelta(df['Talk Durations'].fillna('00:00:00'), errors='coerce')
        df['Call Assigned'] = pd.to_datetime(df['Call Assigned'])
        st.success(get_text("load_data_success"))
        return df
    except Exception as e:
        st.error(get_text("load_data_error"))
        st.exception(e)
        return None

# --- 從本地端(Git儲存庫)載入績效上下限設定檔 ---
@st.cache_data
def load_thresholds(path):
    try:
        df = pd.read_excel(path)
        df.set_index('組別', inplace=True)
        st.success(get_text("load_thresholds_success"))
        return df.to_dict('index')
    except FileNotFoundError:
        st.warning(get_text("load_thresholds_warning").format(path=path))
        return None
    except Exception as e:
        st.error(get_text("load_thresholds_error").format(e=e))
        return None

# --- 每日報告視圖 ---
def display_daily_view(df, selected_group, thresholds):
    st.header(get_text("daily_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
    if not available_dates:
        st.info(get_text("daily_view_no_data_for_team"))
        return

    preselected_date = st.session_state.pop('daily_view_preselect_date', None)
    default_date_index = 0
    if preselected_date:
        try:
            preselected_date_obj = pd.to_datetime(preselected_date).date()
            if preselected_date_obj in available_dates:
                default_date_index = available_dates.index(preselected_date_obj)
        except Exception:
            preselected_date_obj = None
    selected_date = st.selectbox(
        get_text("daily_view_date_selector"),
        available_dates,
        index=default_date_index,
        key="daily_view_date_select"
    )

    if selected_date:
        df_daily = df[df['Date'].dt.date == selected_date].copy()

        if df_daily.empty:
            st.info(get_text("daily_view_no_records_for_date").format(selected_date=selected_date))
            return

        summary = df_daily.groupby(['Group', 'Agent ID', 'Agent Name']).agg(
            Total_Outbound_Call=('Case No', 'size'),
            Total_Outbound_Call_Success=('Connected', 'sum'),
            Total_Case_call=('Case No', 'nunique'),
            Total_Talk_Duration=('Talk Durations', 'sum'),
            Cases_on_Hand=('Cases on Hand', 'first'),
            Daily_Received_Amount=('Daily Received Amount', 'first')
        ).reset_index()

        success_cases = df_daily[df_daily['Connected'] == 1].groupby(['Agent ID'])['Case No'].nunique().reset_index()
        success_cases.rename(columns={'Case No': 'Total_Success_Case'}, inplace=True)
        summary = pd.merge(summary, success_cases, on='Agent ID', how='left')
        summary['Total_Success_Case'] = summary['Total_Success_Case'].fillna(0).astype(int)

        preselected_agent = st.session_state.pop('daily_view_preselect_agent', None)
        if preselected_agent:
            summary['__priority'] = np.where(summary['Agent Name'] == preselected_agent, 0, 1)
            summary = summary.sort_values(['__priority', 'Agent Name']).drop(columns='__priority')
            st.info(get_text("daily_view_focus_info").format(
                agent=preselected_agent,
                date=selected_date.strftime('%Y-%m-%d')
            ))

        summary['Repetition_rate'] = np.where(summary['Total_Success_Case'] > 0, summary['Total_Outbound_Call_Success'] / summary['Total_Success_Case'], 0)

        total_seconds = summary['Total_Talk_Duration'].dt.total_seconds()
        total_cases = summary['Total_Case_call']
        average_seconds = np.where(total_cases > 0, total_seconds / total_cases, 0)
        summary['Average_Talk_Duration'] = pd.to_timedelta(average_seconds, unit='s')

        summary['Called_Coverage'] = np.where(summary['Cases_on_Hand'] > 0, summary['Total_Case_call'] / summary['Cases_on_Hand'], 0)
        summary['Connected_Coverage'] = np.where(summary['Cases_on_Hand'] > 0, summary['Total_Success_Case'] / summary['Cases_on_Hand'], 0)

        summary_to_style = summary.copy()

        summary['Total_Talk_Duration'] = summary['Total_Talk_Duration'].apply(format_timedelta)
        summary['Average_Talk_Duration'] = summary['Average_Talk_Duration'].apply(format_timedelta)
        summary['Repetition_rate'] = summary['Repetition_rate'].round(3)
        summary['Daily_Received_Amount'] = summary['Daily_Received_Amount'].map('{:,.0f}'.format)
        summary['Called_Coverage'] = summary['Called_Coverage'].map('{:.1%}'.format)
        summary['Connected_Coverage'] = summary['Connected_Coverage'].map('{:.1%}'.format)

        column_map_keys = list(get_text("daily_view_columns").keys())
        original_columns = [
            'Group', 'Agent ID', 'Agent Name', 'Cases_on_Hand', 'Total_Outbound_Call',
            'Total_Case_call', 'Called_Coverage', 'Total_Outbound_Call_Success', 'Total_Success_Case',
            'Connected_Coverage', 'Repetition_rate', 'Total_Talk_Duration',
            'Average_Talk_Duration', 'Daily_Received_Amount'
        ]
        rename_dict = {orig: get_text("daily_view_columns")[key] for orig, key in zip(original_columns, column_map_keys)}
        summary.rename(columns=rename_dict, inplace=True)
        summary_to_style.rename(columns=rename_dict, inplace=True)

        final_columns_order = list(get_text("daily_view_columns").values())

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

        styled_summary = summary_to_style[final_columns_order].style.apply(style_daily_kpi, axis=1).format({
            get_text("daily_view_columns")['總通話時長']: format_timedelta,
            get_text("daily_view_columns")['平均通話時長']: format_timedelta,
            get_text("daily_view_columns")['重複撥打率']: '{:.3f}',
            get_text("daily_view_columns")['當日回收金額']: '{:,.0f}',
            get_text("daily_view_columns")['撥打案件覆蓋率']: '{:.1%}',
            get_text("daily_view_columns")['接通案件覆蓋率']: '{:.1%}'
        })

        st.dataframe(styled_summary, use_container_width=True, hide_index=True)

# --- 月度報告視圖 ---
def display_monthly_view(df, selected_group, thresholds):
    st.header(get_text("monthly_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    available_months = sorted(df['Date'].dt.to_period('M').unique())
    if not available_months:
        st.info(get_text("monthly_view_no_month_data"))
        return

    selected_month_period = st.selectbox(
        get_text("monthly_view_month_selector"),
        available_months,
        format_func=lambda p: p.strftime('%Y-%m')
    )

    if selected_month_period:
        df_month = df[df['Date'].dt.to_period('M') == selected_month_period].copy()

        if df_month.empty:
            st.info(get_text("monthly_view_no_data_for_month"))
            return

        tab1, tab2 = st.tabs([
            get_text("monthly_view_tab_trend"),
            get_text("monthly_view_tab_heatmap")
        ])

        with tab1:
            st.subheader(get_text("monthly_view_trend_subheader"))

            if 'Daily Received Amount' in df_month.columns and df_month['Daily Received Amount'].sum() > 0:
                total_connections = df_month['Connected'].sum()
                total_amount = df_month['Daily Received Amount'].sum()
                avg_amount_per_call = (total_amount / total_connections) if total_connections > 0 else 0

                col1, col2, col3 = st.columns(3)
                col1.metric(get_text("monthly_view_kpi_total_connections"), f"{total_connections:,.0f}")
                col2.metric(get_text("monthly_view_kpi_total_amount"), f"${total_amount:,.0f}")
                col3.metric(get_text("monthly_view_kpi_avg_amount_per_call"), f"${avg_amount_per_call:,.2f}")
                st.divider()

                daily_summary = df_month.groupby('Date').agg(
                    Total_Connections=('Connected', 'sum'),
                    Total_Received_Amount=('Daily Received Amount', 'sum')
                ).reset_index()

                base = alt.Chart(daily_summary).encode(x=alt.X('Date:T', title=get_text("monthly_view_tooltip_date")))
                bar = base.mark_bar(color='#4c78a8', opacity=0.7).encode(y=alt.Y('Total_Connections:Q', title=get_text("monthly_view_y_axis_calls")))
                line = base.mark_line(color='#e45756', strokeWidth=3).encode(y=alt.Y('Total_Received_Amount:Q', title=get_text("monthly_view_y_axis_amount")))
                chart = alt.layer(bar, line).resolve_scale(y='independent').interactive()
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info(get_text("monthly_view_no_recovery_data"))

        with tab2:
            st.subheader(get_text("monthly_view_heatmap_subheader"))

            metric_options = [
                get_text("heatmap_metric_connections"), 
                get_text("heatmap_metric_total_calls"), 
                get_text("heatmap_metric_called_coverage")
            ]
            selected_metric = st.radio(
                get_text("monthly_view_heatmap_metric_selector"),
                metric_options,
                horizontal=True,
                key="heatmap_metric_selector"
            )

            format_spec = None
            if selected_metric == get_text("heatmap_metric_connections"):
                daily_agg = df_month.groupby(['Date', 'Group', 'Agent ID', 'Agent Name'])['Connected'].sum()
            elif selected_metric == get_text("heatmap_metric_total_calls"):
                daily_agg = df_month.groupby(['Date', 'Group', 'Agent ID', 'Agent Name'])['Case No'].size()
            else:  # Called Coverage
                daily_agg_raw = df_month.groupby(['Date', 'Group', 'Agent ID', 'Agent Name']).agg(
                    Total_Case_call=('Case No', 'nunique'),
                    Cases_on_Hand=('Cases on Hand', 'first')
                ).reset_index()
                daily_agg_raw['Called_Coverage'] = np.where(
                    daily_agg_raw['Cases_on_Hand'] > 0,
                    daily_agg_raw['Total_Case_call'] / daily_agg_raw['Cases_on_Hand'],
                    0
                )
                daily_agg = daily_agg_raw.set_index(['Date', 'Group', 'Agent ID', 'Agent Name'])['Called_Coverage']
                format_spec = '{:.1%}'

            pivot = daily_agg.unstack(level='Date', fill_value=0).reset_index()

            def style_performance(row, date_cols_to_style, metric_for_styling, weekend_cols):
                styles = pd.Series('', index=row.index)

                def append_style(existing, addition):
                    return f"{existing}; {addition}" if existing else addition

                is_connections_metric = metric_for_styling == get_text("heatmap_metric_connections")
                is_total_calls_metric = metric_for_styling == get_text("heatmap_metric_total_calls")
                group_name = row['Group']

                lower_bound = None
                upper_bound = None
                total_calls_lower_bound = None

                if thresholds and group_name in thresholds:
                    threshold_info = thresholds[group_name]
                    if is_connections_metric:
                        lower_bound = threshold_info.get('下限')
                        upper_bound = threshold_info.get('上限')
                    if is_total_calls_metric:
                        total_calls_lower_bound = threshold_info.get('總撥打數下限')

                for col in date_cols_to_style:
                    if col not in row.index:
                        continue

                    value = row[col]
                    is_weekend = col in weekend_cols

                    if is_connections_metric and lower_bound is not None and upper_bound is not None and value > 0:
                        if value < lower_bound:
                            styles[col] = append_style(styles[col], 'background-color: #FFCDD2')
                        elif value >= upper_bound:
                            styles[col] = append_style(styles[col], 'background-color: #C8E6C9')

                    if is_total_calls_metric and total_calls_lower_bound is not None and value > 0:
                        if value < total_calls_lower_bound:
                            styles[col] = append_style(styles[col], 'background-color: #FFCDD2')

                    if is_weekend and 'background-color' not in styles[col]:
                        styles[col] = append_style(styles[col], 'background-color: #FFFDE7')

                return styles

            
            display_groups = [g for g in CUSTOM_GROUP_ORDER if g in pivot['Group'].unique()]

            for group_name in display_groups:
                group_df = pivot[pivot['Group'] == group_name]
                date_cols = [col for col in group_df.columns if isinstance(col, pd.Timestamp)]
                dates_in_group = sorted(date_cols, reverse=True)

                header_cols = st.columns([0.78, 0.22])
                with header_cols[0]:
                    st.subheader(group_name)
                if dates_in_group:
                    with header_cols[1]:
                        st.caption(get_text("monthly_view_jump_header"))
                        control_cols = st.columns([0.65, 0.35])
                        with control_cols[0]:
                            selected_date_for_jump = st.selectbox(
                                get_text("monthly_view_jump_date_label"),
                                dates_in_group,
                                format_func=lambda d: d.strftime('%Y-%m-%d'),
                                key=f"monthly_jump_date_{group_name}",
                                label_visibility="collapsed"
                            )
                        with control_cols[1]:
                            if st.button(
                                get_text("monthly_view_jump_button"),
                                key=f"monthly_jump_button_{group_name}",
                                use_container_width=True
                            ):
                                st.session_state['pending_view_mode'] = get_text("view_modes")[0]
                                st.session_state['pending_group'] = group_name
                                st.session_state['daily_view_preselect_date'] = selected_date_for_jump.strftime('%Y-%m-%d')
                                st.rerun()

                if not date_cols:
                    st.dataframe(group_df.drop(columns=['Group'], errors='ignore'), use_container_width=True, hide_index=True, column_config={"Group": None})
                    continue

                formatted_date_cols = [d.strftime('%m/%d') for d in date_cols]
                rename_mapping = dict(zip(date_cols, formatted_date_cols))
                renamed_group_df = group_df.rename(columns=rename_mapping)
                weekend_formatted_cols = [
                    fmt
                    for fmt, original_date in zip(formatted_date_cols, date_cols)
                    if original_date.weekday() >= 5
                ]

                styled_df = renamed_group_df.style.apply(
                    style_performance,
                    date_cols_to_style=formatted_date_cols,
                    metric_for_styling=selected_metric,
                    weekend_cols=weekend_formatted_cols,
                    axis=1
                )

                if format_spec:
                    formatter = {col: format_spec for col in formatted_date_cols}
                    styled_df = styled_df.format(formatter, na_rep="-")

                column_config = {
                    "Group": None,
                    "Agent ID": st.column_config.Column(pinned="left"),
                    "Agent Name": st.column_config.Column(pinned="left")
                }

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config=column_config
                )

# --- 催員催收行為分析 ---
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

    if analysis_period == get_text("behavior_view_period_options")[0]:
        available_dates = sorted(df_to_analyze['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_date = st.selectbox(get_text("daily_view_date_selector"), available_dates, key="behavior_date_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.date == selected_date]
    else:
        available_months = sorted(df_to_analyze['Date'].dt.to_period('M').unique())
        if not available_months:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_month = st.selectbox(get_text("monthly_view_month_selector"), available_months, format_func=lambda p: p.strftime('%Y-%m'), key="behavior_month_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.to_period('M') == selected_month]

    if df_filtered.empty:
        st.info(get_text("daily_view_no_records_for_date").format(selected_date="selected period"))
        return

    df_filtered = df_filtered[df_filtered['Talk Durations'].dt.total_seconds() > 0].copy()
    if df_filtered.empty:
        st.info(get_text("behavior_view_no_valid_talk_duration"))
        return

    tab1, tab2 = st.tabs([
        get_text("behavior_view_tab_original"),
        get_text("behavior_view_tab_effective")
    ])

    def categorize_talk_duration(seconds):
        if seconds <= 5: return "~5s"
        elif 5 < seconds <= 10: return "5s - 10s"
        elif 10 < seconds <= 30: return "10s - 30s"
        elif 30 < seconds <= 60: return "30s - 1min"
        elif 60 < seconds <= 120: return "1min - 2min"
        elif 120 < seconds <= 180: return "2min - 3min"
        else: return "> 3min"

    df_filtered['Talk_Duration_Category'] = df_filtered['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)
    category_order = ["~5s", "5s - 10s", "10s - 30s", "30s - 1min", "1min - 2min", "2min - 3min", "> 3min"]

    with tab1:
        category_counts = df_filtered['Talk_Duration_Category'].value_counts().reset_index()
        category_counts.columns = ['Category', 'Count']
        category_counts['Category'] = pd.Categorical(category_counts['Category'], categories=category_order, ordered=True)
        category_counts = category_counts.sort_values('Category')
        total_calls = category_counts['Count'].sum()
        category_counts['Percentage'] = (category_counts['Count'] / total_calls) if total_calls > 0 else 0

        y_axis_option = st.radio(get_text("behavior_view_y_axis_option"), get_text("behavior_view_y_axis_options"), horizontal=True, key="behavior_y_axis_original")
        y_field, y_title, y_axis_format = ('Count', get_text("behavior_view_y_axis_count"), 's') if y_axis_option == get_text("behavior_view_y_axis_options")[0] else ('Percentage', get_text("behavior_view_y_axis_percentage"), '%')

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

    with tab2:
        if 'Daily Received Amount' in df_filtered.columns and df_filtered['Daily Received Amount'].sum() > 0:

            total_calls_agg = df_filtered.groupby('Talk_Duration_Category').agg(
                Count=('Case No', 'size')
            ).reset_index()

            recovered_calls_df = df_filtered[df_filtered['Daily Received Amount'] > 0]
            recovered_cases_agg = recovered_calls_df.groupby('Talk_Duration_Category').agg(
                Recovered_Cases=('Case No', 'nunique')
            ).reset_index()

            agg_data = pd.merge(total_calls_agg, recovered_cases_agg, on='Talk_Duration_Category', how='left').fillna(0)
            agg_data['Conversion_Rate'] = np.where(agg_data['Count'] > 0, agg_data['Recovered_Cases'] / agg_data['Count'], 0)
            agg_data['Category'] = pd.Categorical(agg_data['Talk_Duration_Category'], categories=category_order, ordered=True)
            agg_data = agg_data.sort_values('Category')
            agg_data['Recovered_Cases'] = agg_data['Recovered_Cases'].astype(int)

            base = alt.Chart(agg_data).encode(
                x=alt.X('Talk_Duration_Category:N', sort=category_order, title=get_text("behavior_view_x_axis"), axis=alt.Axis(labelAngle=0))
            )

            bar = base.mark_bar(color='#4c78a8', opacity=0.7).encode(
                y=alt.Y('Count:Q', title=get_text("behavior_view_y_axis_count")),
                tooltip=[
                    alt.Tooltip('Talk_Duration_Category', title=get_text("behavior_view_tooltip_category")),
                    alt.Tooltip('Count', title=get_text("behavior_view_tooltip_count"))
                ]
            )

            line = base.mark_line(color='#e45756', strokeWidth=3, point=True).encode(
                y=alt.Y('Conversion_Rate:Q', title=get_text("behavior_view_y_axis_conversion_rate"), axis=alt.Axis(format='%')),
                tooltip=[
                    alt.Tooltip('Talk_Duration_Category', title=get_text("behavior_view_tooltip_category")),
                    alt.Tooltip('Conversion_Rate', title=get_text("behavior_view_tooltip_conversion_rate"), format=".2%"),
                    alt.Tooltip('Recovered_Cases', title=get_text("behavior_view_tooltip_recovered_cases"))
                ]
            )

            chart_effective = alt.layer(bar, line).resolve_scale(
                y='independent'
            ).properties(
                title=get_text("behavior_view_effective_chart_title").format(analysis_subject_name=analysis_subject_name)
            ).interactive()

            st.altair_chart(chart_effective, use_container_width=True)
        else:
            st.info(get_text("behavior_view_no_recovery_data"))


# --- 催員時點撥打與接通分析 ---
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
        available_months = sorted(df_to_analyze['Date'].dt.to_period('M').unique())
        if not available_months:
            st.warning(get_text("behavior_view_no_records_warning").format(analysis_subject_name=analysis_subject_name))
            return
        selected_month = st.selectbox(get_text("monthly_view_month_selector"), available_months, format_func=lambda p: p.strftime('%Y-%m'), key="call_time_month_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.to_period('M') == selected_month]

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
        Total_Connected_Calls=('Connected', 'sum'),
        Total_Received_Amount=('Daily Received Amount', 'sum')
    ).reset_index()

    hourly_stats['Time_Interval_Sort'] = pd.to_datetime(hourly_stats['Time_Interval_Label'], format='%H:%M').dt.time
    hourly_stats = hourly_stats.sort_values('Time_Interval_Sort').drop(columns='Time_Interval_Sort')

    hourly_stats['Connection_Rate'] = np.where(hourly_stats['Total_Outbound_Calls'] > 0, hourly_stats['Total_Connected_Calls'] / hourly_stats['Total_Outbound_Calls'], 0)
    hourly_stats['Avg_Amount_per_Call'] = np.where(hourly_stats['Total_Outbound_Calls'] > 0, hourly_stats['Total_Received_Amount'] / hourly_stats['Total_Outbound_Calls'], 0)

    total_outbound = hourly_stats['Total_Outbound_Calls'].sum()
    total_connected = hourly_stats['Total_Connected_Calls'].sum()
    hourly_stats['Outbound_Call_Percentage'] = (hourly_stats['Total_Outbound_Calls'] / total_outbound) if total_outbound > 0 else 0
    hourly_stats['Connected_Call_Percentage'] = (hourly_stats['Total_Connected_Calls'] / total_connected) if total_connected > 0 else 0

    display_mode = st.radio(get_text("call_time_view_display_mode"), get_text("call_time_view_display_mode_options"), horizontal=True, key="call_time_display_mode")

    heatmap_metric = get_text("call_time_view_heatmap_options")[0]
    if display_mode == get_text("call_time_view_display_mode_options")[2]:
        if 'Daily Received Amount' in df_filtered.columns and df_filtered['Daily Received Amount'].sum() > 0:
            heatmap_metric = st.radio(get_text("call_time_view_heatmap_metric"), get_text("call_time_view_heatmap_options"), horizontal=True, key="heatmap_metric_select")
        else:
            st.info(get_text("call_time_view_no_recovery_data"))

    if display_mode != get_text("call_time_view_display_mode_options")[2]:
        y_axis_mode = st.radio(get_text("call_time_view_y_axis_mode"), get_text("call_time_view_y_axis_options"), horizontal=True, key="call_time_y_axis_mode")
    else:
        y_axis_mode = get_text("call_time_view_y_axis_options")[0]
        st.caption(get_text("call_time_view_combined_chart_caption"))

    y_field, y_title, chart = None, None, None

    if display_mode == get_text("call_time_view_display_mode_options")[0]:
        if y_axis_mode == get_text("call_time_view_y_axis_options")[0]:
            y_field, y_title, y_format = 'Total_Outbound_Calls', get_text("call_time_view_y_outbound_count"), 's'
        else:
            y_field, y_title, y_format = 'Outbound_Call_Percentage', get_text("call_time_view_y_outbound_ratio"), '%'
        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title=get_text("call_time_view_x_axis"), axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_format)),
            tooltip=[alt.Tooltip('Time_Interval_Label', title=get_text("call_time_view_tooltip_time")),
                     alt.Tooltip('Total_Outbound_Calls', title=get_text("call_time_view_tooltip_outbound_count")),
                     alt.Tooltip('Outbound_Call_Percentage', title=get_text("call_time_view_tooltip_outbound_ratio"), format='.1%')]
        ).properties(title=get_text("call_time_view_chart_title_outbound").format(analysis_subject_name=analysis_subject_name, y_title=y_title, time_granularity=time_granularity_display))
    elif display_mode == get_text("call_time_view_display_mode_options")[1]:
        if y_axis_mode == get_text("call_time_view_y_axis_options")[0]:
            y_field, y_title, y_format = 'Total_Connected_Calls', get_text("call_time_view_y_connected_count"), 's'
        else:
            y_field, y_title, y_format = 'Connected_Call_Percentage', get_text("call_time_view_y_connected_ratio"), '%'
        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title=get_text("call_time_view_x_axis"), axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_format)),
            tooltip=[alt.Tooltip('Time_Interval_Label', title=get_text("call_time_view_tooltip_time")),
                     alt.Tooltip('Total_Connected_Calls', title=get_text("call_time_view_tooltip_connected_count")),
                     alt.Tooltip('Connected_Call_Percentage', title=get_text("call_time_view_tooltip_connected_ratio"), format='.1%')]
        ).properties(title=get_text("call_time_view_chart_title_connected").format(analysis_subject_name=analysis_subject_name, y_title=y_title, time_granularity=time_granularity_display))
    else: # 綜合分析
        y_field, y_title = 'Total_Outbound_Calls', get_text("call_time_view_y_outbound_count")

        color_field, color_title, color_scheme = None, None, None
        if heatmap_metric == get_text("call_time_view_heatmap_options")[0]: # 接通率
            color_field = 'Connection_Rate'
            color_title = get_text("call_time_view_color_legend_connection")
            color_scheme = 'blues'
            tooltip_metric = alt.Tooltip('Connection_Rate', title=get_text("call_time_view_tooltip_connection_rate"), format='.1%')
            metric_name = get_text("call_time_view_heatmap_options")[0]
        else: # 平均回收金額
            color_field = 'Avg_Amount_per_Call'
            color_title = get_text("call_time_view_color_legend_amount")
            color_scheme = 'oranges'
            tooltip_metric = alt.Tooltip('Avg_Amount_per_Call', title=get_text("call_time_view_tooltip_avg_amount"), format=",.0f")
            metric_name = get_text("call_time_view_heatmap_options")[1]

        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title=get_text("call_time_view_x_axis"), axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format='s')),
            color=alt.Color(color_field, scale=alt.Scale(scheme=color_scheme), title=color_title),
            tooltip=[alt.Tooltip('Time_Interval_Label', title=get_text("call_time_view_tooltip_time")),
                     alt.Tooltip('Total_Outbound_Calls', title=get_text("call_time_view_tooltip_outbound_count")),
                     tooltip_metric]
        ).properties(title=get_text("call_time_view_chart_title_combined").format(analysis_subject_name=analysis_subject_name, y_title=y_title, metric_name=metric_name, time_granularity=time_granularity_display))

    if chart:
        st.altair_chart(chart, use_container_width=True)

# --- 催員行為與高績效人員比較 ---
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

    if analysis_period == get_text("profiling_view_period_options")[0]: # 單日
        available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(get_text("profiling_view_no_date_warning"))
            return
        selected_date = st.selectbox(get_text("daily_view_date_selector"), available_dates, key="profiling_date_select")
        df_period = df[df['Date'].dt.date == selected_date]
    else: # 月份
        df['Month'] = df['Date'].dt.to_period('M')
        available_months = sorted(df['Month'].unique(), reverse=True)
        if not available_months:
            st.warning(get_text("profiling_view_no_month_warning"))
            return
        selected_month = st.selectbox(
            get_text("monthly_view_month_selector"),
            available_months,
            format_func=lambda p: p.strftime('%Y-%m'),
            key="profiling_month_select"
        )
        df_period = df[df['Month'] == selected_month]

    if df_period.empty:
        st.info(get_text("daily_view_no_records_for_date").format(selected_date="selected period"))
        return

    df_agent = df_period[df_period['Agent Name'] == selected_agent]
    df_benchmark = pd.DataFrame()
    if benchmark_agents:
        df_benchmark = df_period[df_period['Agent Name'].isin(benchmark_agents)]

    # --- 行為模式比較 ---
    st.subheader(get_text("profiling_view_behavior_subheader"))
    st.markdown(f"**{get_text('profiling_view_time_chart_title').format(selected_agent=selected_agent)}**")

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
    st.markdown(f"**{get_text('profiling_view_duration_chart_title').format(selected_agent=selected_agent)}**")
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

    # --- V16.0 績效指標比較 ---
    st.subheader(get_text("profiling_view_performance_subheader"))
    st.markdown(f"**{get_text('profiling_view_performance_chart_title').format(selected_agent=selected_agent)}**")

    def calculate_kpis(df_to_calc, is_benchmark=False):
        if df_to_calc.empty:
            return {
                get_text("profiling_metric_recovery_amount"): 0,
                get_text("profiling_metric_connected_coverage"): 0,
                get_text("profiling_metric_avg_talk_duration"): 0
            }

        num_agents = df_to_calc['Agent ID'].nunique() if is_benchmark else 1
        if num_agents == 0: num_agents = 1 # Avoid division by zero

        # 1. 回收總金額
        total_recovery = df_to_calc['Daily Received Amount'].sum()

        # 2. 接通案件覆蓋率
        if is_benchmark:
            cases_on_hand = df_to_calc.groupby(['Date', 'Agent ID'])['Cases on Hand'].first().sum()
        else:
             cases_on_hand = df_to_calc.groupby('Date')['Cases on Hand'].first().sum()

        connected_cases = df_to_calc[df_to_calc['Connected'] == 1]['Case No'].nunique()
        
        total_recovery_kpi = total_recovery / num_agents
        connected_coverage = (connected_cases / cases_on_hand) if cases_on_hand > 0 else 0

        # 3. 平均通話時長
        total_talk_seconds = df_to_calc['Talk Durations'].dt.total_seconds().sum()
        total_connected_calls = df_to_calc['Connected'].sum()
        avg_talk_duration = (total_talk_seconds / total_connected_calls) if total_connected_calls > 0 else 0

        return {
            get_text("profiling_metric_recovery_amount"): total_recovery_kpi,
            get_text("profiling_metric_connected_coverage"): connected_coverage,
            get_text("profiling_metric_avg_talk_duration"): avg_talk_duration
        }

    agent_kpis = calculate_kpis(df_agent)
    benchmark_kpis = calculate_kpis(df_benchmark, is_benchmark=True) if not df_benchmark.empty else agent_kpis

    if df_benchmark.empty:
         benchmark_kpis = {k: 0 for k in agent_kpis}


    kpi_data = []
    for metric in agent_kpis.keys():
        kpi_data.append({"Metric": metric, "Value": agent_kpis[metric], "Group": get_text("profiling_view_performance_agent")})
        if not df_benchmark.empty:
            kpi_data.append({"Metric": metric, "Value": benchmark_kpis[metric], "Group": get_text("profiling_view_performance_benchmark")})

    kpi_df = pd.DataFrame(kpi_data)

    if not kpi_df.empty:
        chart = alt.Chart(kpi_df).mark_bar().encode(
            x=alt.X('Group:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y('Value:Q', title=None),
            color=alt.Color('Group:N', title=get_text("profiling_view_performance_group")),
            tooltip=[
                alt.Tooltip('Group', title=get_text("profiling_view_performance_group")),
                alt.Tooltip('Value', title=get_text("profiling_view_performance_value"), format='.2f')
            ]
        ).properties(
            width=alt.Step(40)
        ).facet(
            column=alt.Column('Metric:N', title=get_text("profiling_view_performance_metric"), sort=list(agent_kpis.keys()), header=alt.Header(labelOrient='bottom'))
        ).resolve_scale(
            y='independent'
        )
        st.altair_chart(chart, use_container_width=True)

# --- V18.2 修改：覆蓋率與績效關聯分析視圖 ---
def display_coverage_performance_view(df, selected_group):
    st.header(get_text("coverage_view_header"))

    if selected_group != get_text("all_teams"):
        df = df[df['Group'] == selected_group].copy()

    # --- 過濾器 ---
    if 'coverage_benchmark_select' not in st.session_state:
        st.session_state.coverage_benchmark_select = []

    col1, col2, col3 = st.columns(3)
    with col1:
        available_months = sorted(df['Date'].dt.to_period('M').unique(), reverse=True)
        if not available_months:
            st.info(get_text("monthly_view_no_month_data"))
            return
        selected_month_period = st.selectbox(
            get_text("monthly_view_month_selector"),
            available_months,
            format_func=lambda p: p.strftime('%Y-%m'),
            key="coverage_month_select"
        )

    df_month = df[df['Date'].dt.to_period('M') == selected_month_period].copy()
    if df_month.empty:
        st.info(get_text("monthly_view_no_data_for_month"))
        return

    agent_list = sorted(df_month['Agent Name'].unique())
    if not agent_list:
        st.info(get_text("behavior_view_no_data_in_team").format(selected_group=selected_group))
        return

    with col2:
        selected_agent = st.selectbox(
            get_text("coverage_view_agent_selector"),
            agent_list,
            key="coverage_agent_select"
        )
    
    benchmark_options = [agent for agent in agent_list if agent != selected_agent]
    st.session_state.coverage_benchmark_select = [
        agent for agent in st.session_state.coverage_benchmark_select if agent in benchmark_options
    ]
    with col3:
        benchmark_agents = st.multiselect(
            get_text("profiling_view_benchmark_selector"),
            benchmark_options,
            key="coverage_benchmark_select"
        )

    # --- 數據準備 ---
    daily_summary = df_month.groupby(['Date', 'Group', 'Agent ID', 'Agent Name']).agg(
        Cases_on_Hand=('Cases on Hand', 'first'),
        Daily_Received_Amount=('Daily Received Amount', 'first')
    ).reset_index()

    success_cases = df_month[df_month['Connected'] == 1].groupby(['Date', 'Agent ID'])['Case No'].nunique().reset_index()
    success_cases.rename(columns={'Case No': 'Total_Success_Case'}, inplace=True)

    daily_summary = pd.merge(daily_summary, success_cases, on=['Date', 'Agent ID'], how='left')
    daily_summary['Total_Success_Case'] = daily_summary['Total_Success_Case'].fillna(0).astype(int)

    daily_summary['Connected_Coverage'] = np.where(
        daily_summary['Cases_on_Hand'] > 0,
        daily_summary['Total_Success_Case'] / daily_summary['Cases_on_Hand'],
        0
    )

    daily_summary.dropna(subset=['Daily_Received_Amount'], inplace=True)
    
    # --- V18.2 修改：只篩選被選中的人員 ---
    agents_to_display = [selected_agent] + benchmark_agents
    display_df = daily_summary[daily_summary['Agent Name'].isin(agents_to_display)]
    
    display_df = display_df[(display_df['Connected_Coverage'] > 0) | (display_df['Daily_Received_Amount'] > 0)]

    if display_df.empty:
        st.info(get_text("coverage_view_no_data"))
        return

    # --- 圖表繪製 ---
    st.subheader(get_text("coverage_view_chart_subheader"))

    # --- V18.2 修改：基於選定群組計算平均值 ---
    avg_coverage = display_df['Connected_Coverage'].mean()
    avg_amount = display_df['Daily_Received_Amount'].mean()

    # 為視覺化分類
    def classify_agent(agent_name):
        if agent_name == selected_agent:
            return get_text("profiling_view_performance_agent")
        else: # 所有其他被選中的都是標竿
            return get_text("profiling_view_performance_benchmark")
    display_df['Category'] = display_df['Agent Name'].apply(classify_agent)

    # 視覺化參數
    color_scale = alt.Scale(
        domain=[get_text("profiling_view_performance_agent"), get_text("profiling_view_performance_benchmark")],
        range=['#e45756', '#4c78a8']
    )
    size_scale = alt.Scale(
        domain=[get_text("profiling_view_performance_agent"), get_text("profiling_view_performance_benchmark")],
        range=[150, 80]
    )

    # --- V18.2 修改：altair 圖表設定，座標軸將自動適應 display_df 的範圍 ---
    base_chart = alt.Chart(display_df).encode(
        x=alt.X('Connected_Coverage:Q', title=get_text("coverage_view_x_axis"), axis=alt.Axis(format='%')),
        y=alt.Y('Daily_Received_Amount:Q', title=get_text("coverage_view_y_axis"), axis=alt.Axis(format='s')),
        tooltip=[
            alt.Tooltip('Date:T', title=get_text("monthly_view_tooltip_date")),
            alt.Tooltip('Agent Name:N', title=get_text("daily_view_columns")['姓名']),
            alt.Tooltip('Connected_Coverage:Q', title=get_text("coverage_view_x_axis"), format='.1%'),
            alt.Tooltip('Daily_Received_Amount:Q', title=get_text("coverage_view_y_axis"), format=',.0f')
        ]
    ).interactive()

    points = base_chart.mark_circle().encode(
        color=alt.Color('Category:N', scale=color_scale, legend=alt.Legend(title="群組")),
        size=alt.Size('Category:N', scale=size_scale, legend=None),
        opacity=alt.value(0.8)
    )
    
    vline = alt.Chart(pd.DataFrame({'x': [avg_coverage]})).mark_rule(strokeDash=[5,5], color='gray').encode(x='x:Q')
    hline = alt.Chart(pd.DataFrame({'y': [avg_amount]})).mark_rule(strokeDash=[5,5], color='gray').encode(y='y:Q')

    final_chart = (points + vline + hline).properties(
        title=get_text("coverage_view_chart_title").format(
            month=selected_month_period.strftime('%Y-%m'),
            agent=selected_agent
        )
    )
    st.altair_chart(final_chart, use_container_width=True)

    # --- KPI 比較 ---
    st.subheader(get_text("coverage_view_kpi_subheader"))
    agent_data = display_df[display_df['Agent Name'] == selected_agent]
    benchmark_data = display_df[display_df['Agent Name'].isin(benchmark_agents)] if benchmark_agents else pd.DataFrame()

    agent_avg_coverage = agent_data['Connected_Coverage'].mean() if not agent_data.empty else 0
    agent_avg_amount = agent_data['Daily_Received_Amount'].mean() if not agent_data.empty else 0
    agent_total_amount = agent_data['Daily_Received_Amount'].sum() if not agent_data.empty else 0

    if not benchmark_data.empty:
        benchmark_avg_coverage = benchmark_data['Connected_Coverage'].mean()
        benchmark_avg_amount = benchmark_data['Daily_Received_Amount'].mean()
        delta_coverage_text = f"{(agent_avg_coverage - benchmark_avg_coverage):.1%} vs. 標竿"
        delta_amount_text = f"${(agent_avg_amount - benchmark_avg_amount):,.0f} vs. 標竿"
    else:
        delta_coverage_text = "無標竿可比較"
        delta_amount_text = "無標竿可比較"

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label=get_text("coverage_kpi_avg_coverage"),
        value=f"{agent_avg_coverage:.1%}",
        delta=delta_coverage_text,
        delta_color="off" if not benchmark_agents else "normal"
    )
    col2.metric(
        label=get_text("coverage_kpi_avg_amount"),
        value=f"${agent_avg_amount:,.0f}",
        delta=delta_amount_text,
        delta_color="off" if not benchmark_agents else "normal"
    )
    col3.metric(
        label=get_text("coverage_kpi_total_amount"),
        value=f"${agent_total_amount:,.0f}"
    )

# --- 主應用程式 ---
def main():
    st.sidebar.header(get_text("lang_selector_label"))
    lang_choice = st.sidebar.radio(
        "",
        ["中文", "English"],
        index=0 if st.session_state.lang == 'zh_tw' else 1,
        label_visibility="collapsed"
    )

    new_lang = 'zh_tw' if lang_choice == '中文' else 'en'
    if st.session_state.lang != new_lang:
        st.session_state.lang = new_lang
        st.rerun()

    st.title(get_text("main_title"))

    try:
        creds_json = json.loads(st.secrets.gcp_service_account.credentials)
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
    except Exception as e:
        st.error(f"讀取 GCP 憑證時發生錯誤: {e}")
        st.stop()

    df = load_data(creds)
    thresholds = load_thresholds("各組每日撥通數上下限.xlsx")

    if df is not None:
        st.sidebar.header(get_text("sidebar_view_mode"))

        view_mode_options = get_text("view_modes")
        pending_view_mode = st.session_state.pop('pending_view_mode', None)
        if pending_view_mode and pending_view_mode in view_mode_options:
            st.session_state['view_mode_radio'] = pending_view_mode
        if "view_mode_radio" not in st.session_state:
            st.session_state["view_mode_radio"] = view_mode_options[0]

        view_mode = st.sidebar.radio(
            "",
            view_mode_options,
            label_visibility="collapsed",
            key="view_mode_radio"
        )

        view_functions = {
            view_mode_options[0]: display_daily_view,
            view_mode_options[1]: display_monthly_view,
            view_mode_options[2]: display_behavior_analysis_view,
            view_mode_options[3]: display_call_time_analysis_view,
            view_mode_options[4]: display_profiling_view,
            view_mode_options[5]: display_coverage_performance_view, # 新增視圖
        }

        st.sidebar.header(get_text("sidebar_filter_team"))
        if 'Group' in df.columns:
            df['Group'] = df['Group'].astype(str)
            all_groups = [get_text("all_teams")] + [g for g in CUSTOM_GROUP_ORDER if g in df['Group'].unique()]
        else:
            all_groups = [get_text("all_teams")]

        pending_group = st.session_state.pop('pending_group', None)
        current_group_state = st.session_state.get("group_select")
        if pending_group and pending_group in all_groups:
            st.session_state["group_select"] = pending_group
        elif current_group_state not in all_groups:
            st.session_state["group_select"] = all_groups[0]

        selected_group = st.sidebar.selectbox(
            "",
            all_groups,
            label_visibility="collapsed",
            key="group_select"
        )

        if view_mode in view_functions:
            if view_mode in [view_mode_options[0], view_mode_options[1]]:
                 view_functions[view_mode](df, selected_group, thresholds)
            else:
                 view_functions[view_mode](df, selected_group)

    else:
        st.warning(get_text("data_load_failed"))

if __name__ == "__main__":
    main()
