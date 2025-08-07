import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
import io
import gdown
import json

# --- 頁面配置 ---
st.set_page_config(
    page_title="電話催收過程指標追蹤儀表板 (生產環境)",
    page_icon="☁️",
    layout="wide"
)

# --- 自定義組別排序 ---
CUSTOM_GROUP_ORDER = [
    "Motor M1 Team1", "Motor M1 Team2", "Motor M1 Team3", "Motor M1 Team4",
    "SR Team", "Vehicle M1", "Motor M2", "Vehicle M2", "M3", "Write off"
]

# --- 輔助函數 ---
def format_timedelta(td):
    """將 timedelta 物件格式化為 HH:MM:SS 字串。"""
    if pd.isnull(td) or not isinstance(td, pd.Timedelta):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# --- 【架構 V6.0】從雲端 Google Drive 載入數據 (生產環境專用) ---
@st.cache_data(ttl=600) # 快取 10 分鐘
def load_data():
    """
    使用 GCP 服務帳號憑證，安全地從 Google Drive 下載大型數據檔案。
    此函數專為 Streamlit Community Cloud 生產環境設計。
    """
    try:
        # 從 Streamlit Secrets 讀取 GCP 憑證
        if 'gcp_service_account' not in st.secrets or 'credentials' not in st.secrets.gcp_service_account:
            st.error("錯誤：找不到 GCP 服務帳號憑證。請確認已在 Streamlit Cloud 中設定 Secrets。")
            return None
            
        creds_json_str = st.secrets.gcp_service_account.credentials
        creds_dict = json.loads(creds_json_str)

        # Google Drive 檔案的 File ID
        file_id = "1O9Po49F7TkV4c_Q8Y0yaufhI15HFKGyT"

        # 使用 gdown 搭配服務帳號憑證下載檔案至記憶體
        output = io.BytesIO()
        gdown.download(id=file_id, output=output, use_cookies=False, quiet=True, fuzzy=True, credentials=creds_dict)
        output.seek(0)

        # 從記憶體中的 bytes 直接讀取 CSV
        df = pd.read_csv(output)
        
        # --- 後續資料預處理 ---
        df['Date'] = pd.to_datetime(df['Date'])
        df['Talk Durations'] = pd.to_timedelta(df['Talk Durations'].fillna('00:00:00'), errors='coerce')
        df['Call Assigned'] = pd.to_datetime(df['Call Assigned'])
        
        st.success("數據已從 Google Drive 安全載入。")
        return df

    except Exception as e:
        st.error(f"透過服務帳號載入 Google Drive 資料時發生錯誤：{e}")
        st.info("請確認：\n1. Streamlit Cloud Secrets 中的憑證是否正確。\n2. Google Drive 檔案是否已與服務帳號的 Email 分享（權限為'檢視者'）。\n3. 檔案 ID 是否正確。")
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

# --- 顯示模式 (所有 display_... 函數與本地版完全相同) ---
def display_daily_view(df, selected_group, thresholds):
    st.header("催員每日撥打狀況報告")
    
    if selected_group != "所有團隊":
        df = df[df['Group'] == selected_group].copy()

    available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
    if not available_dates:
        st.info("在選定的團隊中，沒有可用的資料。")
        return
    
    selected_date = st.selectbox("選擇日期", available_dates)

    if selected_date:
        df_daily = df[df['Date'].dt.date == selected_date].copy()

        if df_daily.empty:
            st.info(f"在 {selected_date} 沒有通話紀錄。")
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
        
        summary.rename(columns={
            'Group': '組別', 'Agent ID': 'ID', 'Agent Name': '姓名',
            'Total_Outbound_Call': '總撥打數', 'Total_Outbound_Call_Success': '總成功撥打數',
            'Total_Case_call': '總處理案件數', 'Total_Success_Case': '總成功案件數',
            'Repetition_rate': '重複撥打率', 'Total_Talk_Duration': '總通話時長',
            'Average_Talk_Duration': '平均通話時長'
        }, inplace=True)

        final_columns_order = [
            '組別', 'ID', '姓名', '總撥打數', '總成功撥打數', '總處理案件數',
            '總成功案件數', '重複撥打率', '總通話時長', '平均通話時長'
        ]
        summary = summary[final_columns_order]
        
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
                    styles['總成功撥打數'] = 'background-color: #FFCDD2'
                elif value_to_check >= upper_bound:
                    styles['總成功撥打數'] = 'background-color: #C8E6C9'
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

def display_behavior_analysis_view(df, selected_group):
    """催員催收行為分析視圖"""
    st.header("催員催收行為分析")

    if selected_group != "所有團隊":
        df = df[df['Group'] == selected_group].copy()

    agent_list = ["全體"] + sorted(df['Agent Name'].unique())
    if len(agent_list) == 1:
        st.info(f"團隊 '{selected_group}' 中沒有可用的資料。")
        return
    
    selected_agent = st.selectbox("選擇催員或全體", agent_list, key="behavior_agent_select")

    if selected_agent == "全體":
        df_to_analyze = df.copy()
        analysis_subject_name = f"{selected_group} 全體" if selected_group != "所有團隊" else "所有團隊 全體"
    else:
        df_to_analyze = df[df['Agent Name'] == selected_agent].copy()
        analysis_subject_name = selected_agent

    analysis_period = st.radio("選擇分析區間", ["單日分析", "月份分析"], horizontal=True, key="behavior_period")

    if analysis_period == "單日分析":
        available_dates = sorted(df_to_analyze['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(f"{analysis_subject_name} 在選定的時間範圍內沒有通話紀錄。")
            return
        selected_date = st.selectbox("選擇日期", available_dates, key="behavior_date_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.date == selected_date]
    else:
        available_months = sorted(df_to_analyze['Date'].dt.month.unique())
        if not available_months:
            st.warning(f"{analysis_subject_name} 在選定的時間範圍內沒有通話紀錄。")
            return
        selected_month = st.selectbox("選擇月份", available_months, format_func=lambda x: f"2025-{x:02d}", key="behavior_month_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.month == selected_month]

    if df_filtered.empty:
        st.info("在選定的時間範圍內，沒有通話紀錄。")
        return

    df_filtered = df_filtered[df_filtered['Talk Durations'].dt.total_seconds() > 0].copy()
    if df_filtered.empty:
        st.info("在選定的時間範圍內，沒有有效通話時長紀錄。")
        return

    def categorize_talk_duration(seconds):
        if seconds <= 5: return "~5秒"
        elif 5 < seconds <= 10: return "5秒 - 10秒"
        elif 10 < seconds <= 30: return "10秒 - 30秒"
        elif 30 < seconds <= 60: return "30秒 - 1分鐘"
        elif 60 < seconds <= 120: return "1分鐘 - 2分鐘"
        elif 120 < seconds <= 180: return "2分鐘 - 3分鐘"
        else: return "3分鐘以上"

    df_filtered['Talk_Duration_Category'] = df_filtered['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)

    category_counts = df_filtered['Talk_Duration_Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']

    category_order = ["~5秒", "5秒 - 10秒", "10秒 - 30秒", "30秒 - 1分鐘", "1分鐘 - 2分鐘", "2分鐘 - 3分鐘", "3分鐘以上"]
    category_counts['Category'] = pd.Categorical(category_counts['Category'], categories=category_order, ordered=True)
    category_counts = category_counts.sort_values('Category')

    total_calls = category_counts['Count'].sum()
    category_counts['Percentage'] = (category_counts['Count'] / total_calls) if total_calls > 0 else 0

    y_axis_option = st.radio("選擇 Y 軸顯示方式", ["通話筆數", "通話比例"], horizontal=True, key="behavior_y_axis_option")

    if y_axis_option == "通話筆數":
        y_field, y_title, y_axis_format = 'Count', '通話筆數', 's'
    else:
        y_field, y_title, y_axis_format = 'Percentage', '通話比例', '%'

    chart = alt.Chart(category_counts).mark_bar().encode(
        x=alt.X('Category', sort=category_order, title="通話時長區間", axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_axis_format)),
        tooltip=[
            alt.Tooltip('Category', title='時長區間'),
            alt.Tooltip('Count', title='通話筆數'),
            alt.Tooltip('Percentage', title='通話比例', format='.1%')
        ]
    ).properties(title=f"{analysis_subject_name} 通話時長分佈")
    st.altair_chart(chart, use_container_width=True)

    st.subheader("詳細數據")
    st.dataframe(category_counts.style.format({'Percentage': '{:.1%}'}), use_container_width=True, hide_index=True)

def display_call_time_analysis_view(df, selected_group):
    """催員時點撥打與接通分析視圖"""
    st.header("催員時點撥打與接通分析")

    if selected_group != "所有團隊":
        df = df[df['Group'] == selected_group].copy()

    agent_list = ["全體"] + sorted(df['Agent Name'].unique())
    if len(agent_list) == 1:
        st.info(f"團隊 '{selected_group}' 中沒有可用的資料。")
        return
        
    selected_agent = st.selectbox("選擇催員或全體", agent_list, key="call_time_agent_select")

    if selected_agent == "全體":
        df_to_analyze = df.copy()
        analysis_subject_name = f"{selected_group} 全體" if selected_group != "所有團隊" else "所有團隊 全體"
    else:
        df_to_analyze = df[df['Agent Name'] == selected_agent].copy()
        analysis_subject_name = selected_agent

    analysis_period = st.radio("選擇分析區間", ["單日分析", "月份分析"], horizontal=True, key="call_time_period")

    if analysis_period == "單日分析":
        available_dates = sorted(df_to_analyze['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning(f"{analysis_subject_name} 在選定的時間範圍內沒有通話紀錄。")
            return
        selected_date = st.selectbox("選擇日期", available_dates, key="call_time_date_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.date == selected_date]
    else:
        available_months = sorted(df_to_analyze['Date'].dt.month.unique())
        if not available_months:
            st.warning(f"{analysis_subject_name} 在選定的時間範圍內沒有通話紀錄。")
            return
        selected_month = st.selectbox("選擇月份", available_months, format_func=lambda x: f"2025-{x:02d}", key="call_time_month_select")
        df_filtered = df_to_analyze[df_to_analyze['Date'].dt.month == selected_month]

    if df_filtered.empty:
        st.info("在選定的時間範圍內，沒有通話紀錄。")
        return

    time_granularity = st.selectbox("選擇時間粒度", ["小時", "30分鐘", "15分鐘"], key="time_granularity")

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

    hourly_stats['Connection_Rate'] = np.where(
        hourly_stats['Total_Outbound_Calls'] > 0,
        hourly_stats['Total_Connected_Calls'] / hourly_stats['Total_Outbound_Calls'], 0
    )
    
    total_outbound = hourly_stats['Total_Outbound_Calls'].sum()
    total_connected = hourly_stats['Total_Connected_Calls'].sum()
    hourly_stats['Outbound_Call_Percentage'] = (hourly_stats['Total_Outbound_Calls'] / total_outbound) if total_outbound > 0 else 0
    hourly_stats['Connected_Call_Percentage'] = (hourly_stats['Total_Connected_Calls'] / total_connected) if total_connected > 0 else 0
    
    display_mode = st.radio("選擇顯示模式", ["總撥出電話數", "總接通電話數", "綜合分析 (撥出數 + 接通率熱力圖)"], horizontal=True, key="call_time_display_mode")

    if display_mode != "綜合分析 (撥出數 + 接通率熱力圖)":
        y_axis_mode = st.radio(
            "選擇 Y 軸顯示方式",
            ["數量", "比例"],
            horizontal=True,
            key="call_time_y_axis_mode"
        )
    else:
        y_axis_mode = "數量"
        st.caption("註：為清晰呈現投入量與接通效率的關係，綜合分析圖 Y 軸固定為「數量」。")

    st.subheader(f"{analysis_subject_name} 的通話時點分佈 ({time_granularity})")

    y_field, y_title, chart = None, None, None

    if display_mode == "總撥出電話數":
        if y_axis_mode == "數量":
            y_field, y_title, y_format = 'Total_Outbound_Calls', '總撥出電話數', 's'
        else:
            y_field, y_title, y_format = 'Outbound_Call_Percentage', '撥出電話比例', '%'
        
        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title="時間區間", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_format)),
            tooltip=[alt.Tooltip('Time_Interval_Label', title='時間區間'),
                     alt.Tooltip('Total_Outbound_Calls', title='總撥出數'),
                     alt.Tooltip('Outbound_Call_Percentage', title='撥出比例', format='.1%')]
        ).properties(title=f"{analysis_subject_name} {y_title} ({time_granularity})")

    elif display_mode == "總接通電話數":
        if y_axis_mode == "數量":
            y_field, y_title, y_format = 'Total_Connected_Calls', '總接通電話數', 's'
        else:
            y_field, y_title, y_format = 'Connected_Call_Percentage', '接通電話比例', '%'
        
        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title="時間區間", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format=y_format)),
            tooltip=[alt.Tooltip('Time_Interval_Label', title='時間區間'),
                     alt.Tooltip('Total_Connected_Calls', title='總接通數'),
                     alt.Tooltip('Connected_Call_Percentage', title='接通比例', format='.1%')]
        ).properties(title=f"{analysis_subject_name} {y_title} ({time_granularity})")

    else: # 綜合分析
        y_field, y_title = 'Total_Outbound_Calls', '總撥出電話數'

        chart = alt.Chart(hourly_stats).mark_bar().encode(
            x=alt.X('Time_Interval_Label', sort=None, title="時間區間", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(y_field, title=y_title, axis=alt.Axis(format='s')),
            color=alt.Color('Connection_Rate', scale=alt.Scale(scheme='blues', domain=[0, 0.50]), title="接通率"),
            tooltip=[alt.Tooltip('Time_Interval_Label', title='時間區間'),
                     alt.Tooltip('Total_Outbound_Calls', title='總撥出數'),
                     alt.Tooltip('Outbound_Call_Percentage', title='撥出比例', format='.1%'),
                     alt.Tooltip('Total_Connected_Calls', title='總接通數'),
                     alt.Tooltip('Connection_Rate', title='接通率', format='.1%')]
        ).properties(title=f"{analysis_subject_name} {y_title}與接通率 ({time_granularity})")
    
    st.altair_chart(chart, use_container_width=True)

    st.subheader("詳細數據")
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
    st.header("催員行為與高績效人員比較 (Agent vs. Benchmark)")

    if selected_group != "所有團隊":
        df = df[df['Group'] == selected_group].copy()
    
    agent_list = sorted(df['Agent Name'].unique())
    if not agent_list:
        st.info(f"團隊 '{selected_group}' 中沒有可用的資料。")
        return
        
    if 'profiling_benchmark_select' not in st.session_state:
        st.session_state.profiling_benchmark_select = []

    col1, col2, col3 = st.columns([2, 2, 1.5])
    with col1:
        selected_agent = st.selectbox("選擇要分析的催員", agent_list, key="profiling_agent_select")
    
    benchmark_options = [agent for agent in agent_list if agent != selected_agent]
    st.session_state.profiling_benchmark_select = [
        agent for agent in st.session_state.profiling_benchmark_select if agent in benchmark_options
    ]

    with col2:
        benchmark_agents = st.multiselect(
            "選擇績效標竿群組 (可多選)", 
            benchmark_options, 
            key="profiling_benchmark_select"
        )
    with col3:
        analysis_period = st.radio("選擇分析區間", ["單日", "月份"], horizontal=True, key="profiling_period")

    if analysis_period == "單日":
        available_dates = sorted(df['Date'].dt.date.unique(), reverse=True)
        if not available_dates:
            st.warning("資料中沒有可用的日期。")
            return
        selected_date = st.selectbox("選擇日期", available_dates, key="profiling_date_select")
        df_period = df[df['Date'].dt.date == selected_date]
    else:
        available_months = sorted(df['Date'].dt.month.unique())
        if not available_months:
            st.warning("資料中沒有可用的月份。")
            return
        selected_month = st.selectbox("選擇月份", available_months, format_func=lambda x: f"2025-{x:02d}", key="profiling_month_select")
        df_period = df[df['Date'].dt.month == selected_month]

    if df_period.empty:
        st.info("在選定的時間範圍內，沒有通話紀錄。")
        return

    df_agent = df_period[df_period['Agent Name'] == selected_agent]
    
    df_benchmark = pd.DataFrame()
    if benchmark_agents:
        df_benchmark = df_period[df_period['Agent Name'].isin(benchmark_agents)]

    st.subheader(f"通話時點模式分析：{selected_agent} vs. 標竿群組")

    df_agent['Time_Interval'] = df_agent['Call Assigned'].dt.floor('H').dt.strftime('%H:00')
    agent_time_stats = df_agent['Time_Interval'].value_counts().reset_index()
    agent_time_stats.columns = ['Time_Interval', '個人撥打數']

    if not df_benchmark.empty:
        df_benchmark['Time_Interval'] = df_benchmark['Call Assigned'].dt.floor('H').dt.strftime('%H:00')
        benchmark_time_stats = df_benchmark.groupby('Time_Interval')['Case No'].count()
        num_benchmark_agents = df_benchmark['Agent ID'].nunique()
        benchmark_avg_time_stats = (benchmark_time_stats / num_benchmark_agents).reset_index()
        benchmark_avg_time_stats.columns = ['Time_Interval', '標竿群組平均撥打數']
        
        comparison_df = pd.merge(agent_time_stats, benchmark_avg_time_stats, on='Time_Interval', how='outer').fillna(0)
    else:
        comparison_df = agent_time_stats
        comparison_df['標竿群組平均撥打數'] = 0

    comparison_df = comparison_df.sort_values('Time_Interval')

    base = alt.Chart(comparison_df).encode(x=alt.X('Time_Interval', title="時間區間", sort=None, axis=alt.Axis(labelAngle=0)))
    bar = base.mark_bar().encode(
        y=alt.Y('個人撥打數', title='撥打數'),
        tooltip=[alt.Tooltip('Time_Interval', title='時間'), alt.Tooltip('個人撥打數', title='個人撥打數')]
    )
    
    chart_layers = [bar]
    if not df_benchmark.empty:
        line = base.mark_line(color='red', strokeDash=[5,5]).encode(
            y=alt.Y('標竿群組平均撥打數', title='撥打數'),
        )
        points = base.mark_point(color='red', filled=True, size=60).encode(
            y=alt.Y('標竿群組平均撥打數'),
            tooltip=[alt.Tooltip('Time_Interval', title='時間'), alt.Tooltip('標竿群組平均撥打數', title='標竿平均', format='.1f')]
        )
        chart_layers.extend([line, points])

    st.altair_chart(
        alt.layer(*chart_layers).resolve_scale(y='shared'),
        use_container_width=True
    )

    st.subheader(f"通話時長模式分析：{selected_agent} vs. 標竿群組")

    def categorize_talk_duration(seconds):
        if seconds <= 5: return "~5秒"
        elif 5 < seconds <= 10: return "5秒 - 10秒"
        elif 10 < seconds <= 30: return "10秒 - 30秒"
        elif 30 < seconds <= 60: return "30秒 - 1分鐘"
        elif 60 < seconds <= 120: return "1分鐘 - 2分鐘"
        elif 120 < seconds <= 180: return "2分鐘 - 3分鐘"
        else: return "3分鐘以上"
    
    category_order = ["~5秒", "5秒 - 10秒", "10秒 - 30秒", "30秒 - 1分鐘", "1分鐘 - 2分鐘", "2分鐘 - 3分鐘", "3分鐘以上"]

    df_agent_valid_talk = df_agent[df_agent['Talk Durations'].dt.total_seconds() > 0]
    if not df_agent_valid_talk.empty:
        df_agent_valid_talk['Category'] = df_agent_valid_talk['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)
        agent_duration_dist = df_agent_valid_talk['Category'].value_counts(normalize=True).reset_index()
        agent_duration_dist.columns = ['Category', '個人比例']
    else:
        agent_duration_dist = pd.DataFrame(columns=['Category', '個人比例'])

    if not df_benchmark.empty:
        df_benchmark_valid_talk = df_benchmark[df_benchmark['Talk Durations'].dt.total_seconds() > 0]
        if not df_benchmark_valid_talk.empty:
            df_benchmark_valid_talk['Category'] = df_benchmark_valid_talk['Talk Durations'].dt.total_seconds().apply(categorize_talk_duration)
            benchmark_duration_dist = df_benchmark_valid_talk['Category'].value_counts(normalize=True).reset_index()
            benchmark_duration_dist.columns = ['Category', '標竿群組平均比例']
            duration_comparison_df = pd.merge(agent_duration_dist, benchmark_duration_dist, on='Category', how='outer').fillna(0)
        else:
            duration_comparison_df = agent_duration_dist
            duration_comparison_df['標竿群組平均比例'] = 0
    else:
        duration_comparison_df = agent_duration_dist
        duration_comparison_df['標竿群組平均比例'] = 0

    base_dur = alt.Chart(duration_comparison_df).encode(x=alt.X('Category', title="通話時長區間", sort=category_order, axis=alt.Axis(labelAngle=0)))
    bar_dur = base_dur.mark_bar().encode(
        y=alt.Y('個人比例', title='比例', axis=alt.Axis(format='%')),
        tooltip=[alt.Tooltip('Category', title='時長區間'), alt.Tooltip('個人比例', title='個人比例', format='.1%')]
    )
    
    chart_dur_layers = [bar_dur]
    if not df_benchmark.empty:
        line_dur = base_dur.mark_line(color='red', strokeDash=[5,5]).encode(
            y=alt.Y('標竿群組平均比例', title='比例', axis=alt.Axis(format='%')),
        )
        points_dur = base_dur.mark_point(color='red', filled=True, size=60).encode(
            y=alt.Y('標竿群組平均比例'),
            tooltip=[alt.Tooltip('Category', title='時長區間'), alt.Tooltip('標竿群組平均比例', title='標竿平均', format='.1%')]
        )
        chart_dur_layers.extend([line_dur, points_dur])

    st.altair_chart(
        alt.layer(*chart_dur_layers).resolve_scale(y='shared'),
        use_container_width=True
    )


# --- 主應用程式 ---
def main():
    st.title("電話催收過程指標追蹤儀表板")
    
    # --- 【V6.1 修正】確保以無參數方式呼叫雲端專用函數 ---
    df = load_data()
    thresholds = load_thresholds("各組每日撥通數上下限.xlsx")

    if df is not None:
        st.sidebar.header("選擇檢視模式")
        view_mode = st.sidebar.radio(
            "",
            ["催員每日撥打狀況報告", "月度催員接通數儀表板", "催員催收行為分析", "催員時點撥打與接通分析", "催員行為與高績效人員比較"],
            label_visibility="collapsed"
        )

        st.sidebar.header("篩選團隊")
        if 'Group' in df.columns:
            df['Group'] = df['Group'].astype(str)
            all_groups = ["所有團隊"] + [g for g in CUSTOM_GROUP_ORDER if g in df['Group'].unique()]
        else:
            all_groups = ["所有團隊"]
        
        selected_group = st.sidebar.selectbox("", all_groups, label_visibility="collapsed")

        if view_mode == "催員每日撥打狀況報告":
            display_daily_view(df, selected_group, thresholds)
        elif view_mode == "月度催員接通數儀表板":
            display_monthly_view(df, selected_group, thresholds)
        elif view_mode == "催員催收行為分析":
            display_behavior_analysis_view(df, selected_group)
        elif view_mode == "催員時點撥打與接通分析":
            display_call_time_analysis_view(df, selected_group)
        elif view_mode == "催員行為與高績效人員比較":
            display_profiling_view(df, selected_group)
        
    else:
        st.warning("資料未能成功載入，請根據上方的錯誤訊息檢查您的設定。")

if __name__ == "__main__":
    main()