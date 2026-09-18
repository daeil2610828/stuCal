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
    "APP_CAPTION": "시험 날짜와 공부 범위를 설정하고, 개인 일정 및 하루 루틴에 맞춰 학습 스케줄을 계획하세요.",
    
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
        "TAB1_NAME": "1. 개인 일정 추가",
        "TAB2_NAME": "2. 학습 일정 추가",
        "TAB3_NAME": "3. 일상 루틴 설정"
    },

    "ADD_PERSONAL": {
        "HEADER": "🗓️ 개인 일정 추가 (공부 불가 시간/일정)"
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
        "SUCCESS": "학습 스케줄이 성공적으로 생성되었습니다!"
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
    st.session_state.personal_schedule = pd.DataFrame(columns=["날짜", "시간", "이름", "이동 시간", "태그", "메모"])

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
# [왼쪽 칼럼] 기본 달력 표 (팝업 버그 수정 및 종류 표기)
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

    # 달력 데이터 준비
    year = selected_dt.year
    month = selected_dt.month
    
    schedule_dict = {}
    if st.session_state.schedule is not None and not st.session_state.schedule.empty:
        for _, row in st.session_state.schedule.iterrows():
            schedule_dict[row["날짜"]] = row

    personal_dict = {}
    if not st.session_state.personal_schedule.empty:
        for _, row in st.session_state.personal_schedule.iterrows():
            p_date = row["날짜"]
            if p_date not in personal_dict:
                personal_dict[p_date] = []
            personal_dict[p_date].append(row)

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
            position: relative;
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
            height: 85px;
            vertical-align: top;
            padding: 4px;
            background-color: transparent;
            color: var(--text-color, inherit);
            position: relative;
        }}
        .other-m {{
            opacity: 0.35;
        }}
        
        /* 팝업 스타일 */
        .event-details {{
            position: relative;
            margin-top: 3px;
        }}
        .event-details summary {{
            list-style: none;
            cursor: pointer;
            outline: none;
        }}
        .event-details summary::-webkit-details-marker {{
            display: none;
        }}
        
        .badge {{
            background-color: rgba(26, 115, 232, 0.15);
            color: var(--text-color, inherit);
            border: 1px solid rgba(26, 115, 232, 0.4);
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 11px;
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
            display: block;
            word-break: break-all;
        }}
        
        /* 레이어 팝업 박스 */
        .popup-box {{
            position: absolute;
            top: 25px;
            left: 0;
            z-index: 999;
            width: 190px;
            background-color: #ffffff;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
            font-size: 11px;
            color: #24292f;
            line-height: 1.5;
        }}
        .popup-header {{
            font-weight: bold;
            font-size: 12px;
            margin-bottom: 6px;
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 4px;
            color: #d9381e;
        }}
        .popup-header-study {{
            font-weight: bold;
            font-size: 12px;
            margin-bottom: 6px;
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 4px;
            color: #1a73e8;
        }}
        .popup-item {{
            margin-bottom: 2px;
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
            study_data = schedule_dict.get(day_date, None)
            personal_events = personal_dict.get(day_date, [])
            
            td_class = "" if is_current_month else 'class="other-m"'
            content_html = ""
            
            if is_current_month:
                # 1. 학습 일정 팝업
                if study_data is not None:
                    is_done = study_data.get("완료여부", False)
                    icon = "✅" if is_done else "📖"
                    range_txt = study_data["목표 범위"]
                    target_amt = study_data["목표량"]
                    
                    content_html += (
                        f'<details class="event-details">'
                        f'<summary><div class="badge">{icon} {range_txt}</div></summary>'
                        f'<div class="popup-box">'
                        f'<div class="popup-header-study">📌 학습 일정</div>'
                        f'<div class="popup-item"><b>종류:</b> 학습 일정</div>'
                        f'<div class="popup-item"><b>범위:</b> {range_txt}</div>'
                        f'<div class="popup-item"><b>목표량:</b> {target_amt}</div>'
                        f'<div class="popup-item"><b>상태:</b> {"완료" if is_done else "진행 중"}</div>'
                        f'</div></details>'
                    )
                
                # 2. 개인 일정 팝업
                for p_ev in personal_events:
                    p_name = p_ev["이름"]
                    p_time = p_ev["시간"]
                    p_travel = p_ev["이동 시간"]
                    p_tag = p_ev["태그"]
                    p_memo = p_ev["메모"]
                    
                    tag_html = f'<div class="popup-item"><b>태그:</b> {p_tag}</div>' if p_tag else ''
                    memo_html = f'<div class="popup-item"><b>메모:</b> {p_memo}</div>' if p_memo else ''
                    
                    content_html += (
                        f'<details class="event-details">'
                        f'<summary><div class="badge-personal">🛑 {p_name}</div></summary>'
                        f'<div class="popup-box">'
                        f'<div class="popup-header">🛑 {p_name}</div>'
                        f'<div class="popup-item"><b>종류:</b> 개인 일정</div>'
                        f'<div class="popup-item"><b>시간:</b> {p_time}</div>'
                        f'<div class="popup-item"><b>이동 시간:</b> {p_travel}</div>'
                        f'{tag_html}'
                        f'{memo_html}'
                        f'</div></details>'
                    )
                
            html_code += f'<td {td_class}><b>{day_date.day}</b>{content_html}</td>'
        html_code += "</tr>"
    html_code += "</tbody></table>"
    
    st.markdown(html_code, unsafe_allow_html=True)

# ------------------------------------------
# [오른쪽 칼럼] 탭뷰
# ------------------------------------------
with right_col:
    tab1, tab2, tab3 = st.tabs([
        TEXTS["TABS"]["TAB1_NAME"], 
        TEXTS["TABS"]["TAB2_NAME"], 
        TEXTS["TABS"]["TAB3_NAME"]
    ])
    
    # --------------------------------------
    # TAB 1: 개인 일정 추가
    # --------------------------------------
    with tab1:
        st.subheader(TEXTS["ADD_PERSONAL"]["HEADER"])
        with st.form("add_personal_form"):
            p_title = st.text_input("이름", placeholder="예: 병원 방문, 미팅, 운동")
            
            p_col1, p_col2 = st.columns(2)
            p_date = p_col1.date_input("날짜", value=date.today())
            p_time = p_col2.time_input("시간", value=datetime.now().time())
            
            travel_col, tag_col = st.columns(2)
            travel_time = travel_col.selectbox(
                "이동 시간", 
                options=["없음", "5분", "10분", "15분", "30분", "45분", "1시간", "1시간 30분", "2시간 이상"]
            )
            p_tag = tag_col.text_input("태그", placeholder="예: 약속, 건강, 학업")
            
            p_memo = st.text_area("메모", placeholder="세부 내용을 입력하세요.")
            
            if st.form_submit_button("➕ 개인 일정 등록", use_container_width=True):
                new_event = pd.DataFrame([{
                    "날짜": p_date,
                    "시간": p_time.strftime("%H:%M"),
                    "이름": p_title,
                    "이동 시간": travel_time,
                    "태그": p_tag,
                    "메모": p_memo
                }])
                st.session_state.personal_schedule = pd.concat([st.session_state.personal_schedule, new_event], ignore_index=True)
                st.success("개인 일정이 등록되었습니다!")
                st.rerun()
                
        if not st.session_state.personal_schedule.empty:
            st.divider()
            st.write("📋 **등록된 개인 일정 목록**")
            st.dataframe(st.session_state.personal_schedule, use_container_width=True, hide_index=True)

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
    # TAB 3: 일상 루틴 설정
    # --------------------------------------
    with tab3:
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
