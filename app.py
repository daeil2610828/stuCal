import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import math
import calendar
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 앱 내 전체 텍스트 모음 (중앙 관리)
# ==========================================
TEXTS = {
    "APP_TITLE": "📅 스마트 시험 D-Day & 공부 스케줄러",
    "APP_CAPTION": "시험 날짜와 공부 범위를 설정하고, 개인 일정 및 하루 루틴에 맞춰 학습 스케줄을 재조정하세요.",
    
    "SIDEBAR": {
        "TITLE": "📁 데이터 관리",
        "IMPORT_HEADER": "📥 데이터 불러오기",
        "IMPORT_LABEL": "CSV 또는 JSON 파일 업로드",
        "IMPORT_BTN": "불러온 데이터로 스케줄 적용",
        "IMPORT_SUCCESS": "데이터를 성공적으로 불러왔습니다!",
        "IMPORT_ERROR": "파일을 읽는 중 오류가 발생했습니다: ",
        "EXPORT_HEADER": "📤 데이터 내보내기",
        "EXPORT_CSV_BTN": "📥 CSV 파일로 다운로드",
        "EXPORT_JSON_BTN": "📥 JSON 파일로 다운로드",
        "NO_DATA": "내보낼 스케줄 데이터가 없습니다."
    },
    
    "CALENDAR": {
        "HEADER": "🗓️ 달력 보기",
        "DATE_PICKER_LABEL": "선택 날짜",
        "WEEKDAYS": ["일", "월", "화", "수", "목", "금", "토"]
    },
    
    "TABS": {
        "TAB1_NAME": "1. 공부 기록",
        "TAB2_NAME": "2. 학습 일정 추가",
        "TAB3_NAME": "3. 개인 일정 추가",
        "TAB4_NAME": "4. 일상 루틴 설정",
        "TAB5_NAME": "5. 일정 확인/수정",
        "TAB6_NAME": "6. 설정"
    },
    
    "STUDY_RECORD": {
        "HEADER": "📋 공부 기록 및 스케줄 조정",
        "KPI_TOTAL": "총 목표량",
        "KPI_COMPLETED": "현재 완료량",
        "KPI_PROGRESS": "진행률",
        "SAVE_GSHEET_BTN": "💾 구글 시트에 저장",
        "SAVE_SUCCESS": "구글 시트에 저장 완료!",
        "READJUST_BTN": "🔄 일정 자동 재조정",
        "READJUST_SUCCESS": "재조정이 완료되었습니다!",
        "ALL_DONE": "🎉 모든 공부 목표를 달성했습니다!",
        "NO_FUTURE_DAYS": "⚠️ 남은 공부 기간이 없습니다.",
        "NO_SCHEDULE_INFO": "등록된 스케줄 데이터가 없습니다. 상단 탭에서 학습 일정을 추가해주세요."
    },

    "ADD_STUDY": {
        "HEADER": "📚 학습 일정 세부 설정 & 생성",
        "SUBJECT_LABEL": "과목명",
        "SUBJECT_PLACEHOLDER": "예: 일반생물학, 토익, 수능 수학",
        "RANGE_TYPE_LABEL": "목표 단위",
        "TOTAL_AMOUNT_LABEL": "총 목표량 (페이지/강 수 등)",
        "START_DATE_LABEL": "공부 시작일",
        "EXAM_DATE_LABEL": "시험/목표 완료일",
        "CREATE_BTN": "🚀 새로운 학습 스케줄 생성",
        "SUCCESS": "학습 스케줄이 성공적으로 생성되어 달성에 반영되었습니다!"
    },

    "ADD_PERSONAL": {
        "HEADER": "🗓️ 개인 일정 추가 (공부 불가 시간/일정)",
        "TITLE_LABEL": "일정 이름",
        "TITLE_PLACEHOLDER": "예: 병원 방문, 가족 모임, 알바",
        "DATE_LABEL": "일정 날짜",
        "TIME_LABEL": "예상 소요 시간 (시간 단위)",
        "MEMO_LABEL": "메모 / 상세 내용",
        "ADD_BTN": "📌 개인 일정 등록",
        "SUCCESS": "개인 일정이 등록되었습니다!"
    },

    "ROUTINE": {
        "HEADER": "⏰ 일상 루틴 & 순공 시간 설정",
        "SLEEP_LABEL": "하루 평균 취침 시간",
        "MEAL_LABEL": "하루 식사 및 준비 시간",
        "REST_LABEL": "기타 휴식 및 이동 시간",
        "CALC_INFO": "💡 하루 24시간 중 학업에 투자할 수 있는 최대 시간:",
        "SAVE_BTN": "💾 루틴 설정 저장",
        "SAVE_SUCCESS": "일상 루틴 설정이 저장되었습니다!"
    },
    
    "SCHEDULE_EDIT": {
        "HEADER": "📌 등록된 일정 개별 선택 및 수정",
        "SELECT_LABEL": "수정할 일정을 선택하세요",
        "SELECTED_DATE_PREFIX": "📅 **선택된 날짜**: ",
        "RANGE_LABEL": "목표 범위",
        "AMOUNT_LABEL": "목표량",
        "DONE_LABEL": "완료 여부",
        "UPDATE_BTN": "일정 업데이트",
        "UPDATE_SUCCESS": "일정이 업데이트되었습니다!",
        "NO_DATA_INFO": "선택할 수 있는 일정 데이터가 없습니다."
    },
    
    "SETTINGS": {
        "HEADER": "📌 기타 설정",
        "INFO": "구글 시트 연동 상태 및 기타 시스템 옵션을 확인할 수 있습니다."
    },
    
    "MESSAGES": {
        "GSHEET_SAVE_ERROR": "구글 시트 저장 실패: "
    }
}

# 페이지 기본 설정
st.set_page_config(page_title=TEXTS["APP_TITLE"].replace("📅 ", ""), layout="wide")

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
        st.error(f"{TEXTS['MESSAGES']['GSHEET_SAVE_ERROR']}{e}")

# 세션 상태 초기화
if "schedule" not in st.session_state:
    st.session_state.schedule = load_schedule_from_gsheets()

if "personal_schedule" not in st.session_state:
    st.session_state.personal_schedule = pd.DataFrame(columns=["날짜", "일정명", "소요시간", "메모"])

if "routine" not in st.session_state:
    st.session_state.routine = {"취침": 7, "식사": 3, "휴식": 2}

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# ==========================================
# 사이드바: 데이터 관리
# ==========================================
st.sidebar.title(TEXTS["SIDEBAR"]["TITLE"])

# 1. 데이터 불러오기
st.sidebar.subheader(TEXTS["SIDEBAR"]["IMPORT_HEADER"])
uploaded_file = st.sidebar.file_uploader(TEXTS["SIDEBAR"]["IMPORT_LABEL"], type=["csv", "json"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            imported_df = pd.read_csv(uploaded_file)
        else:
            imported_df = pd.read_json(uploaded_file)
            
        if "날짜" in imported_df.columns:
            imported_df["날짜"] = pd.to_datetime(imported_df["날짜"]).dt.date
            
        if st.sidebar.button(TEXTS["SIDEBAR"]["IMPORT_BTN"]):
            st.session_state.schedule = imported_df
            save_schedule_to_gsheets(imported_df)
            st.sidebar.success(TEXTS["SIDEBAR"]["IMPORT_SUCCESS"])
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"{TEXTS['SIDEBAR']['IMPORT_ERROR']}{e}")

st.sidebar.divider()

# 2. 데이터 내보내기
st.sidebar.subheader(TEXTS["SIDEBAR"]["EXPORT_HEADER"])
if st.session_state.schedule is not None and not st.session_state.schedule.empty:
    export_df = st.session_state.schedule.copy()
    export_df["날짜"] = export_df["날짜"].astype(str)
    
    csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label=TEXTS["SIDEBAR"]["EXPORT_CSV_BTN"],
        data=csv_data,
        file_name=f"study_schedule_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    json_data = export_df.to_json(orient="records", force_ascii=False)
    st.sidebar.download_button(
        label=TEXTS["SIDEBAR"]["EXPORT_JSON_BTN"],
        data=json_data,
        file_name=f"study_schedule_{date.today()}.json",
        mime="application/json",
        use_container_width=True
    )
else:
    st.sidebar.info(TEXTS["SIDEBAR"]["NO_DATA"])

# ==========================================
# 메인 화면
# ==========================================
st.title(TEXTS["APP_TITLE"])
st.caption(TEXTS["APP_CAPTION"])

left_col, right_col = st.columns([1.1, 0.9], gap="large")

# ------------------------------------------
# [왼쪽 칼럼] 기본 달력 표
# ------------------------------------------
with left_col:
    st.subheader(TEXTS["CALENDAR"]["HEADER"])
    
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
            TEXTS["CALENDAR"]["DATE_PICKER_LABEL"],
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

    # 달력 표 생성
    year = selected_dt.year
    month = selected_dt.month
    
    schedule_dict = {}
    if st.session_state.schedule is not None and not st.session_state.schedule.empty:
        for _, row in st.session_state.schedule.iterrows():
            schedule_dict[row["날짜"]] = row

    personal_dict = {}
    if not st.session_state.personal_schedule.empty:
        for _, row in st.session_state.personal_schedule.iterrows():
            personal_dict[row["날짜"]] = row["일정명"]

    cal = calendar.Calendar(firstweekday=6) # 일요일 시작
    month_days = cal.monthdatescalendar(year, month)

    weekdays_html = "".join([f"<th>{day}</th>" for day in TEXTS["CALENDAR"]["WEEKDAYS"]])

    html_code = f"""
    <style>
        .simple-cal {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            border: 1px solid rgba(128, 128, 128, 0.3);
        }}
        .simple-cal th {{
            border: 1px solid rgba(128, 128, 128, 0.3);
            padding: 8px;
            text-align: center;
            background-color: rgba(128, 128, 128, 0.15);
            color: var(--text-color, inherit) !important;
            font-weight: bold;
        }}
        .simple-cal td {{
            border: 1px solid rgba(128, 128, 128, 0.3);
            height: 75px;
            vertical-align: top;
            padding: 6px;
            background-color: transparent;
            color: var(--text-color, inherit);
        }}
        .other-m {{
            opacity: 0.35;
        }}
        .badge {{
            background-color: rgba(26, 115, 232, 0.15);
            color: var(--text-color, inherit);
            border: 1px solid rgba(26, 115, 232, 0.4);
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 11px;
            margin-top: 4px;
            display: block;
            word-break: break-all;
        }}
        .badge-personal {{
            background-color: rgba(234, 67, 53, 0.15);
            color: var(--text-color, inherit);
            border: 1px solid rgba(234, 67, 53, 0.4);
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 11px;
            margin-top: 2px;
            display: block;
            word-break: break-all;
        }}
    </style>
    <table class="simple-cal"><thead><tr>
        {weekdays_html}
    </tr></thead><tbody>
    """

    for week in month_days:
        html_code += "<tr>"
        for day_date in week:
            is_current_month = (day_date.month == month)
            data = schedule_dict.get(day_date, None)
            personal_event = personal_dict.get(day_date, None)
            
            td_class = "" if is_current_month else 'class="other-m"'
            content_html = ""
            
            if is_current_month:
                if data is not None:
                    is_done = data.get("완료여부", False)
                    icon = "✅" if is_done else "📖"
                    content_html += f'<div class="badge">{icon} {data["목표 범위"]}</div>'
                if personal_event:
                    content_html += f'<div class="badge-personal">🛑 {personal_event}</div>'
                
            html_code += f'<td {td_class}><b>{day_date.day}</b>{content_html}</td>'
        html_code += "</tr>"
    html_code += "</tbody></table>"
    
    st.markdown(html_code, unsafe_allow_html=True)

# ------------------------------------------
# [오른쪽 칼럼] 탭뷰
# ------------------------------------------
with right_col:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        TEXTS["TABS"]["TAB1_NAME"], 
        TEXTS["TABS"]["TAB2_NAME"], 
        TEXTS["TABS"]["TAB3_NAME"], 
        TEXTS["TABS"]["TAB4_NAME"], 
        TEXTS["TABS"]["TAB5_NAME"], 
        TEXTS["TABS"]["TAB6_NAME"]
    ])
    
    # --------------------------------------
    # TAB 1: 일별 공부 기록 및 스케줄 조정
    # --------------------------------------
    with tab1:
        st.subheader(TEXTS["STUDY_RECORD"]["HEADER"])
        
        if st.session_state.schedule is not None and not st.session_state.schedule.empty:
            df = st.session_state.schedule
            calculated_total = int(df["목표량"].sum())
            total_completed = int(df["실제 완료량"].sum())
            progress_pct = min(100.0, (total_completed / calculated_total) * 100) if calculated_total > 0 else 0
            
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            kpi_col1.metric(TEXTS["STUDY_RECORD"]["KPI_TOTAL"], f"{calculated_total}")
            kpi_col2.metric(TEXTS["STUDY_RECORD"]["KPI_COMPLETED"], f"{total_completed}")
            kpi_col3.metric(TEXTS["STUDY_RECORD"]["KPI_PROGRESS"], f"{progress_pct:.1f}%")
            
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
                if st.button(TEXTS["STUDY_RECORD"]["SAVE_GSHEET_BTN"], use_container_width=True):
                    st.session_state.schedule = edited_df
                    save_schedule_to_gsheets(edited_df)
                    st.success(TEXTS["STUDY_RECORD"]["SAVE_SUCCESS"])
                    st.rerun()

            with btn_col2:
                if st.button(TEXTS["STUDY_RECORD"]["READJUST_BTN"], use_container_width=True):
                    today = date.today()
                    future_mask = (edited_df["날짜"] >= today) & (~edited_df["완료여부"])
                    future_days_count = future_mask.sum()
                    
                    current_completed = int(edited_df["실제 완료량"].sum())
                    new_remaining = calculated_total - current_completed
                    
                    if new_remaining <= 0:
                        st.balloons()
                        st.success(TEXTS["STUDY_RECORD"]["ALL_DONE"])
                    elif future_days_count <= 0:
                        st.warning(TEXTS["STUDY_RECORD"]["NO_FUTURE_DAYS"])
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
                        st.success(TEXTS["STUDY_RECORD"]["READJUST_SUCCESS"])
                        st.rerun()
        else:
            st.info(TEXTS["STUDY_RECORD"]["NO_SCHEDULE_INFO"])

    # --------------------------------------
    # TAB 2: 학습 일정 추가
    # --------------------------------------
    with tab2:
        st.subheader(TEXTS["ADD_STUDY"]["HEADER"])
        with st.form("add_study_form"):
            subject_name = st.text_input(TEXTS["ADD_STUDY"]["SUBJECT_LABEL"], placeholder=TEXTS["ADD_STUDY"]["SUBJECT_PLACEHOLDER"])
            unit_type = st.selectbox(TEXTS["ADD_STUDY"]["RANGE_TYPE_LABEL"], options=["페이지", "강 (인강)", "문제 (개)"])
            total_amount = st.number_input(TEXTS["ADD_STUDY"]["TOTAL_AMOUNT_LABEL"], min_value=1, value=100)
            
            st_col1, st_col2 = st.columns(2)
            start_date = st_col1.date_input(TEXTS["ADD_STUDY"]["START_DATE_LABEL"], value=date.today())
            exam_date = st_col2.date_input(TEXTS["ADD_STUDY"]["EXAM_DATE_LABEL"], value=date.today() + timedelta(days=14))
            
            if st.form_submit_button(TEXTS["ADD_STUDY"]["CREATE_BTN"], use_container_width=True):
                total_days = (exam_date - start_date).days + 1
                if total_days <= 0:
                    st.error("시험 날짜는 시작일 이후여야 합니다.")
                else:
                    daily_target = math.ceil(total_amount / total_days)
                    new_rows = []
                    accumulated = 0
                    
                    for i in range(total_days):
                        current_day = start_date + timedelta(days=i)
                        p_start = accumulated + 1
                        p_end = min(accumulated + daily_target, total_amount)
                        
                        range_str = f"{subject_name} {p_start}~{p_end}{unit_type}" if p_start <= total_amount else "완료"
                        amount = max(0, p_end - p_start + 1) if p_start <= total_amount else 0
                        
                        new_rows.append({
                            "날짜": current_day,
                            "목표 범위": range_str,
                            "목표량": amount,
                            "실제 완료량": 0,
                            "완료여부": False
                        })
                        accumulated = p_end
                    
                    new_df = pd.DataFrame(new_rows)
                    st.session_state.schedule = new_df
                    save_schedule_to_gsheets(new_df)
                    st.success(TEXTS["ADD_STUDY"]["SUCCESS"])
                    st.rerun()

    # --------------------------------------
    # TAB 3: 개인 일정 추가
    # --------------------------------------
    with tab3:
        st.subheader(TEXTS["ADD_PERSONAL"]["HEADER"])
        with st.form("add_personal_form"):
            p_title = st.text_input(TEXTS["ADD_PERSONAL"]["TITLE_LABEL"], placeholder=TEXTS["ADD_PERSONAL"]["TITLE_PLACEHOLDER"])
            p_date = st.date_input(TEXTS["ADD_PERSONAL"]["DATE_LABEL"], value=date.today())
            p_hours = st.number_input(TEXTS["ADD_PERSONAL"]["TIME_LABEL"], min_value=0.5, max_value=24.0, value=2.0, step=0.5)
            p_memo = st.text_area(TEXTS["ADD_PERSONAL"]["MEMO_LABEL"])
            
            if st.form_submit_button(TEXTS["ADD_PERSONAL"]["ADD_BTN"], use_container_width=True):
                new_event = pd.DataFrame([{
                    "날짜": p_date,
                    "일정명": p_title,
                    "소요시간": p_hours,
                    "메모": p_memo
                }])
                st.session_state.personal_schedule = pd.concat([st.session_state.personal_schedule, new_event], ignore_index=True)
                st.success(TEXTS["ADD_PERSONAL"]["SUCCESS"])
                st.rerun()
                
        if not st.session_state.personal_schedule.empty:
            st.divider()
            st.write("📋 **등록된 개인 일정 목록**")
            st.dataframe(st.session_state.personal_schedule, use_container_width=True, hide_index=True)

    # --------------------------------------
    # TAB 4: 일상 루틴 설정
    # --------------------------------------
    with tab4:
        st.subheader(TEXTS["ROUTINE"]["HEADER"])
        
        sleep_t = st.number_input(TEXTS["ROUTINE"]["SLEEP_LABEL"], min_value=0, max_value=24, value=st.session_state.routine["취침"])
        meal_t = st.number_input(TEXTS["ROUTINE"]["MEAL_LABEL"], min_value=0, max_value=24, value=st.session_state.routine["식사"])
        rest_t = st.number_input(TEXTS["ROUTINE"]["REST_LABEL"], min_value=0, max_value=24, value=st.session_state.routine["휴식"])
        
        total_routine = sleep_t + meal_t + rest_t
        avail_study = max(0, 24 - total_routine)
        
        st.info(f"{TEXTS['ROUTINE']['CALC_INFO']} **{avail_study}시간** / 하루")
        
        if st.button(TEXTS["ROUTINE"]["SAVE_BTN"], use_container_width=True):
            st.session_state.routine = {"취침": sleep_t, "식사": meal_t, "휴식": rest_t}
            st.success(TEXTS["ROUTINE"]["SAVE_SUCCESS"])

    # --------------------------------------
    # TAB 5: 일정 확인/수정
    # --------------------------------------
    with tab5:
        st.subheader(TEXTS["SCHEDULE_EDIT"]["HEADER"])
        if st.session_state.schedule is not None and not st.session_state.schedule.empty:
            df = st.session_state.schedule
            schedule_dates = df["날짜"].tolist()
            
            selected_item_date = st.selectbox(TEXTS["SCHEDULE_EDIT"]["SELECT_LABEL"], options=schedule_dates, index=0)
            target_row = df[df["날짜"] == selected_item_date].iloc[0]
            
            with st.form("edit_schedule_form"):
                st.write(f"{TEXTS['SCHEDULE_EDIT']['SELECTED_DATE_PREFIX']}{selected_item_date}")
                new_range = st.text_input(TEXTS["SCHEDULE_EDIT"]["RANGE_LABEL"], value=target_row["목표 범위"])
                new_amount = st.number_input(TEXTS["SCHEDULE_EDIT"]["AMOUNT_LABEL"], value=int(target_row["목표량"]))
                new_done = st.checkbox(TEXTS["SCHEDULE_EDIT"]["DONE_LABEL"], value=bool(target_row["완료여부"]))
                
                if st.form_submit_button(TEXTS["SCHEDULE_EDIT"]["UPDATE_BTN"]):
                    idx = df[df["날짜"] == selected_item_date].index[0]
                    df.loc[idx, "목표 범위"] = new_range
                    df.loc[idx, "목표량"] = new_amount
                    df.loc[idx, "완료여부"] = new_done
                    st.session_state.schedule = df
                    save_schedule_to_gsheets(df)
                    st.success(TEXTS["SCHEDULE_EDIT"]["UPDATE_SUCCESS"])
                    st.rerun()
        else:
            st.info(TEXTS["SCHEDULE_EDIT"]["NO_DATA_INFO"])

    # --------------------------------------
    # TAB 6: 기타 설정
    # --------------------------------------
    with tab6:
        st.subheader(TEXTS["SETTINGS"]["HEADER"])
        st.write(TEXTS["SETTINGS"]["INFO"])
