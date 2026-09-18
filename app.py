import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import math
import calendar
import gspread
from google.oauth2.service_account import Credentials

# 페이지 기본 설정
st.set_page_config(page_title="스마트 시험 D-Day 플래너", layout="wide")

# --- Google Sheets 클라우드 연결 (gspread 활용) ---
@st.cache_resource
def get_gsheet_client():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        return client
    except Exception:
        return None

def load_schedule_from_gsheets():
    try:
        client = get_gsheet_client()
        if client is None:
            return None
        
        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(spreadsheet_url).sheet1
        records = sheet.get_all_records()
        
        if not records:
            return None
            
        df = pd.DataFrame(records)
        if "날짜" in df.columns:
            df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
        return df
    except Exception:
        return None

def save_schedule_to_gsheets(df):
    try:
        client = get_gsheet_client()
        if client is None:
            return
            
        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(spreadsheet_url).sheet1
        
        save_df = df.copy()
        if "날짜" in save_df.columns:
            save_df["날짜"] = save_df["날짜"].astype(str)
            
        sheet.clear()
        sheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")

# 세션 상태 초기화
if "schedule" not in st.session_state:
    st.session_state.schedule = load_schedule_from_gsheets()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# --- 사이드바: 내보내기 & 설정 ---
st.sidebar.title("⚙️ 설정 및 도구")

st.sidebar.subheader("📤 스케줄 데이터 내보내기")
if st.session_state.schedule is not None and not st.session_state.schedule.empty:
    export_df = st.session_state.schedule.copy()
    export_df["날짜"] = export_df["날짜"].astype(str)
    
    csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label="📥 CSV 파일로 내보내기",
        data=csv_data,
        file_name=f"study_schedule_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    json_data = export_df.to_json(orient="records", force_ascii=False)
    st.sidebar.download_button(
        label="📥 JSON 파일로 내보내기",
        data=json_data,
        file_name=f"study_schedule_{date.today()}.json",
        mime="application/json",
        use_container_width=True
    )
else:
    st.sidebar.info("내보낼 스케줄 데이터가 없습니다.")

st.sidebar.divider()

st.sidebar.subheader("🎨 화면 스타일 설정")
accent_color_option = st.sidebar.selectbox(
    "테마 색상",
    ["클래식 블루 (#1a73e8)", "에메랄드 그린 (#28a745)", "로열 퍼플 (#6f42c1)", "웜 오렌지 (#fd7e14)"],
    index=0
)
color_map = {
    "클래식 블루 (#1a73e8)": "#1a73e8",
    "에메랄드 그린 (#28a745)": "#28a745",
    "로열 퍼플 (#6f42c1)": "#6f42c1",
    "웜 오렌지 (#fd7e14)": "#fd7e14"
}
selected_accent = color_map[accent_color_option]

# --- Streamlit 자체 다크모드/라이트모드 자동 연동 Dynamic CSS ---
st.markdown(f"""
    <style>
        /* 버튼 스타일링 */
        div.stButton > button {{
            background-color: {selected_accent} !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: bold !important;
            transition: opacity 0.2s;
        }}
        div.stButton > button:hover {{
            opacity: 0.85 !important;
        }}

        /* 탭(Tabs) 선택 스타일링 */
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {selected_accent} !important;
            border-bottom-color: {selected_accent} !important;
            font-weight: bold !important;
        }}

        /* 라디오 버튼 선택 색상 */
        div[role="radiogroup"] label[data-baseweb="radio"] div[aria-checked="true"] {{
            background-color: {selected_accent} !important;
        }}

        /* Progress Bar 색상 */
        div.stProgress > div > div > div > div {{
            background-color: {selected_accent} !important;
        }}

        /* Streamlit 자체 테마 변수 활용 달력 CSS */
        .excel-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            border: 1px solid var(--gray-30, rgba(128, 128, 128, 0.3));
            background-color: var(--background-color);
        }}
        .excel-table th {{
            background-color: var(--secondary-background-color);
            border: 1px solid var(--gray-30, rgba(128, 128, 128, 0.3));
            padding: 8px 0;
            text-align: center;
            font-size: 13px;
            font-weight: bold;
            color: var(--text-color);
        }}
        .excel-table td {{
            border: 1px solid var(--gray-30, rgba(128, 128, 128, 0.3));
            height: 85px;
            vertical-align: top;
            padding: 6px;
            background-color: var(--background-color);
        }}
        .day-num {{
            font-size: 12px;
            font-weight: bold;
            color: var(--text-color);
            display: block;
            margin-bottom: 4px;
        }}
        .other-month {{
            opacity: 0.3;
            background-color: var(--secondary-background-color);
        }}
        .schedule-badge {{
            background-color: {selected_accent}22;
            color: {selected_accent};
            border: 1px solid {selected_accent};
            border-radius: 4px;
            padding: 2px 4px;
            font-size: 11px;
            margin-top: 2px;
            word-break: break-all;
            display: block;
        }}
    </style>
""", unsafe_allow_html=True)

st.title("📅 스마트 시험 D-Day & 공부 스케줄러")
st.caption("시험 날짜와 공부 범위를 설정하고, 달성도에 따라 스케줄을 자동으로 재조정하세요.")

# --- 메인 레이아웃 (좌: 엑셀형 달력 표 / 우: 탭뷰) ---
left_col, right_col = st.columns([1.1, 0.9], gap="large")

# ==========================================
# [왼쪽 칼럼] 엑셀형 달력
# ==========================================
with left_col:
    st.subheader("🗓️ 달력 보기")
    
    nav_col1, nav_col2, nav_col3 = st.columns([0.8, 4.4, 0.8])
    selected_dt = st.session_state.selected_date
    
    with nav_col1:
        if st.button("◀", key="prev_m_btn"):
            first_curr = selected_dt.replace(day=1)
            prev_month_last = first_curr - timedelta(days=1)
            st.session_state.selected_date = prev_month_last.replace(day=min(selected_dt.day, prev_month_last.day))
            st.rerun()
            
    with nav_col2:
        picked_date = st.date_input(
            "선택 날짜",
            value=selected_dt,
            label_visibility="collapsed",
            key="main_date_picker"
        )
        if picked_date != selected_dt:
            st.session_state.selected_date = picked_date
            st.rerun()

    with nav_col3:
        if st.button("▶", key="next_m_btn"):
            next_month = (selected_dt.replace(day=28) + timedelta(days=5)).replace(day=1)
            st.session_state.selected_date = next_month.replace(day=min(selected_dt.day, 28))
            st.rerun()

    # --- HTML 엑셀 표 그리드 생성 ---
    year = selected_dt.year
    month = selected_dt.month
    
    schedule_dict = {}
    if st.session_state.schedule is not None and not st.session_state.schedule.empty:
        for _, row in st.session_state.schedule.iterrows():
            schedule_dict[row["날짜"]] = row

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)

    html_code = '<table class="excel-table"><thead><tr>'
    for day_name in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
        html_code += f'<th>{day_name}</th>'
    html_code += '</tr></thead><tbody>'

    for week in month_days:
        html_code += '<tr>'
        for day_date in week:
            is_current_month = (day_date.month == month)
            data = schedule_dict.get(day_date, None)
            
            td_class = "" if is_current_month else 'class="other-month"'
            
            content_html = ""
            if is_current_month and data is not None:
                is_done = data.get("완료여부", False)
                icon = "✅" if is_done else "📖"
                content_html = f'<div class="schedule-badge">{icon} {data["목표 범위"]}</div>'
                
            html_code += f'<td {td_class}>'
            html_code += f'<span class="day-num">{day_date.day}</span>'
            html_code += content_html
            html_code += '</td>'
        html_code += '</tr>'
    html_code += '</tbody></table>'
    
    st.markdown(html_code, unsafe_allow_html=True)

# ==========================================
# [오른쪽 칼럼] 탭뷰 (1, 2, 3)
# ==========================================
with right_col:
    tab1, tab2, tab3 = st.tabs(["1. 공부 기록", "2. 일정 확인/수정", "3. 설정"])
    
    # --------------------------------------
    # TAB 1: 일별 공부 기록 및 자동 스케줄 재조정
    # --------------------------------------
    with tab1:
        st.subheader("📋 공부 기록 및 스케줄 조정")
        
        if st.session_state.schedule is not None and not st.session_state.schedule.empty:
            df = st.session_state.schedule
            calculated_total = int(df["목표량"].sum())
            total_completed = int(df["실제 완료량"].sum())
            progress_pct = min(100.0, (total_completed / calculated_total) * 100) if calculated_total > 0 else 0
            
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            kpi_col1.metric("총 목표량", f"{calculated_total}")
            kpi_col2.metric("현재 완료량", f"{total_completed}")
            kpi_col3.metric("진행률", f"{progress_pct:.1f}%")
            
            st.progress(progress_pct / 100)
            st.divider()

            edited_df = st.data_editor(
                df,
                column_config={
                    "날짜": st.column_config.DateColumn("날짜", disabled=True),
                    "목표 범위": st.column_config.TextColumn("목표 범위", disabled=True),
                    "목표량": st.column_config.NumberColumn("목표량", disabled=True),
                    "실제 완료량": st.column_config.NumberColumn("실제 완료량", min_value=0, max_value=calculated_total),
                    "완료여부": st.column_config.CheckboxColumn("완료 체크")
                },
                disabled=["날짜", "목표 범위", "목표량"],
                hide_index=True,
                use_container_width=True
            )
            
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.button("💾 구글 시트에 저장", use_container_width=True):
                    st.session_state.schedule = edited_df
                    save_schedule_to_gsheets(edited_df)
                    st.success("구글 시트에 최신 저장 완료!")
                    st.rerun()

            with btn_col2:
                if st.button("🔄 일정 자동 재조정", use_container_width=True):
                    today = date.today()
                    future_mask = (edited_df["날짜"] >= today) & (~edited_df["완료여부"])
                    future_days_count = future_mask.sum()
                    
                    current_completed = int(edited_df["실제 완료량"].sum())
                    new_remaining = calculated_total - current_completed
                    
                    if new_remaining <= 0:
                        st.balloons()
                        st.success("🎉 모든 공부 목표를 달성했습니다!")
                    elif future_days_count <= 0:
                        st.warning("⚠️ 남은 공부 기간이 없습니다.")
                    else:
                        new_daily_target = math.ceil(new_remaining / future_days_count)
                        accumulated = current_completed
                        
                        for idx in edited_df[future_mask].index:
                            p_start = accumulated + 1
                            p_end = min(accumulated + new_daily_target, calculated_total)
                            
                            edited_df.loc[idx, "목표 범위"] = f"{p_start} ~ {p_end}" if p_start <= calculated_total else "완료"
                            edited_df.loc[idx, "목표량"] = max(0, p_end - p_start + 1) if p_start <= calculated_total else 0
                            accumulated = p_end
                            
                        st.session_state.schedule = edited_df
                        save_schedule_to_gsheets(edited_df)
                        st.success("재조정이 완료되었습니다!")
                        st.rerun()
        else:
            st.info("등록된 스케줄 데이터가 없습니다. 구글 시트를 연동해 주세요.")

    # --------------------------------------
    # TAB 2: 일정 클릭 & 직접 수정
    # --------------------------------------
    with tab2:
        st.subheader("📌 등록된 일정 개별 선택 및 수정")
        if st.session_state.schedule is not None and not st.session_state.schedule.empty:
            df = st.session_state.schedule
            schedule_dates = df["날짜"].tolist()
            
            selected_item_date = st.selectbox("수정할 일정을 선택하세요", options=schedule_dates, index=0)
            target_row = df[df["날짜"] == selected_item_date].iloc[0]
            
            with st.form("edit_schedule_form"):
                st.write(f"📅 **선택된 날짜**: {selected_item_date}")
                new_range = st.text_input("목표 범위", value=target_row["목표 범위"])
                new_amount = st.number_input("목표량", value=int(target_row["목표량"]))
                new_done = st.checkbox("완료 여부", value=bool(target_row["완료여부"]))
                
                if st.form_submit_button("일정 업데이트"):
                    idx = df[df["날짜"] == selected_item_date].index[0]
                    df.loc[idx, "목표 범위"] = new_range
                    df.loc[idx, "목표량"] = new_amount
                    df.loc[idx, "완료여부"] = new_done
                    st.session_state.schedule = df
                    save_schedule_to_gsheets(df)
                    st.success("일정이 업데이트되었습니다!")
                    st.rerun()
        else:
            st.info("선택할 수 있는 일정 데이터가 없습니다.")

    # --------------------------------------
    # TAB 3: 기타 설정
    # --------------------------------------
    with tab3:
        st.subheader("📌 설정 메뉴")
        st.write("앱 환경설정 및 구글 시트 상태를 점검할 수 있습니다.")
