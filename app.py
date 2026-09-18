import streamlit as st
import pandas as pd
from datetime import date, datetime, time, timedelta
import math
import calendar
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 앱 내 전체 텍스트 모음 (중앙 관리)
# ==========================================
TEXTS = {
    "APP_TITLE": "📅 스마트 시험 D-Day & 공부 스케줄러",
    "APP_CAPTION": "시험 날짜와 공부 범위를 설정하고, 개인 일정 및 하루 루틴에 맞춰 자동 스케줄링을 경험하세요.",
    
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
        "TAB2_NAME": "2. 정기고사/학습 등록",
        "TAB3_NAME": "3. 학습 방식 설정",
        "TAB4_NAME": "4. 일상 루틴 설정"
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

# Google Sheets 연결 생략 가능
@st.cache_resource
def get_gsheet_client():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(credentials)
    except Exception:
        return None

def load_schedule_from_gsheets():
    try:
        client = get_gsheet_client()
        if client is None: return None
        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(spreadsheet_url).sheet1
        records = sheet.get_all_records()
        if not records: return None
        df = pd.DataFrame(records)
        if "날짜" in df.columns:
            df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
        return df
    except Exception:
        return None

def save_schedule_to_gsheets(df):
    try:
        client = get_gsheet_client()
        if client is None: return
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
if "schedule" not in st.session_state or st.session_state.schedule is None:
    st.session_state.schedule = pd.DataFrame(
        columns=["id", "날짜", "종류", "제목", "목표 범위", "목표량", "완료여부", "메모"]
    )

if "personal_schedule" not in st.session_state:
    st.session_state.personal_schedule = pd.DataFrame(
        columns=["id", "날짜", "시작 시간", "종료 시간", "이름", "이동 시간", "태그", "메모"]
    )

if "routine" not in st.session_state:
    st.session_state.routine = {"취침": 7, "식사": 3, "휴식": 2}

if "study_style" not in st.session_state:
    st.session_state.study_style = {
        "max_subjects_per_day": 2,
        "max_pages_per_day": 30
    }

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# 기본 과목 데이터 정의
default_subjects = [
    {
        "name": "국어", "day": 1,
        "tb_start": 1, "tb_end": 40,
        "has_sub": True, "sub_start": 1, "sub_end": 20
    },
    {
        "name": "수학", "day": 1,
        "tb_start": 1, "tb_end": 50,
        "has_sub": False, "sub_start": 1, "sub_end": 20
    }
]

if "exam_subjects" not in st.session_state:
    st.session_state.exam_subjects = default_subjects
else:
    # 기존 세션 데이터에 새로운 키가 없을 경우 보장해주는 안전장치
    for sub in st.session_state.exam_subjects:
        sub.setdefault("name", "")
        sub.setdefault("day", 1)
        sub.setdefault("tb_start", 1)
        sub.setdefault("tb_end", 30)
        sub.setdefault("has_sub", False)
        sub.setdefault("sub_start", 1)
        sub.setdefault("sub_end", 10)

if "editing_event" not in st.session_state:
    st.session_state.editing_event = None

def add_subject():
    st.session_state.exam_subjects.append(
        {
            "name": "", "day": 1,
            "tb_start": 1, "tb_end": 30,
            "has_sub": False, "sub_start": 1, "sub_end": 10
        }
    )

def remove_subject(index):
    if len(st.session_state.exam_subjects) > 1:
        st.session_state.exam_subjects.pop(index)

# ==========================================
# 사이드바: 데이터 관리
# ==========================================
st.sidebar.title(TEXTS["SIDEBAR"]["TITLE"])

st.sidebar.subheader(TEXTS["SIDEBAR"]["IMPORT_HEADER"])
uploaded_file = st.sidebar.file_uploader(TEXTS["SIDEBAR"]["IMPORT_LABEL"], type=["csv", "json"])

if uploaded_file is not None:
    try:
        imported_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_json(uploaded_file)
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

st.sidebar.subheader(TEXTS["SIDEBAR"]["EXPORT_HEADER"])
if not st.session_state.schedule.empty:
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
else:
    st.sidebar.info(TEXTS["SIDEBAR"]["NO_DATA"])

# ==========================================
# 메인 화면
# ==========================================
st.title(TEXTS["APP_TITLE"])
st.caption(TEXTS["APP_CAPTION"])

left_col, right_col = st.columns([1.1, 0.9], gap="large")

# ------------------------------------------
# [왼쪽 칼럼] 달력 및 일정 표시
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

    st.markdown(f"#### 📅 {selected_dt.strftime('%Y년 %m월 %d일')} 일정 상세")
    
    day_personals = st.session_state.personal_schedule[st.session_state.personal_schedule["날짜"] == selected_dt]
    day_studies = st.session_state.schedule[st.session_state.schedule["날짜"] == selected_dt]
    
    if day_personals.empty and day_studies.empty:
        st.info("해당 날짜에 등록된 일정이 없습니다.")
    else:
        for idx, row in day_personals.iterrows():
            with st.expander(f"🛑 [개인] {row['이름']} ({row['시작 시간']} ~ {row['종료 시간']})"):
                st.write(f"**이동시간:** {row['이동 시간']} | **태그:** {row['태그']}")
                st.write(f"**메모:** {row['메모']}")
                c1, c2 = st.columns(2)
                if c1.button("✏️ 개인일정 수정", key=f"edit_p_{idx}"):
                    st.session_state.editing_event = {"type": "personal", "data": row.to_dict(), "index": idx}
                    st.rerun()
                if c2.button("🗑️ 삭제", key=f"del_p_{idx}"):
                    st.session_state.personal_schedule = st.session_state.personal_schedule.drop(idx).reset_index(drop=True)
                    st.success("삭제되었습니다.")
                    st.rerun()
                    
        for idx, row in day_studies.iterrows():
            is_exam = "⭐" in str(row["종류"]) or "시험" in str(row["종류"])
            icon = "⭐" if is_exam else ("✅" if row["완료여부"] else "📖")
            with st.expander(f"{icon} [{row['종류']}] {row['제목']} - {row['목표 범위']}"):
                st.write(f"**목표량:** {row['목표량']}")
                st.write(f"**메모:** {row['메모']}")
                c1, c2 = st.columns(2)
                if c1.button("✏️ 학습일정 수정", key=f"edit_s_{idx}"):
                    st.session_state.editing_event = {"type": "study", "data": row.to_dict(), "index": idx}
                    st.rerun()
                if c2.button("🗑️ 삭제", key=f"del_s_{idx}"):
                    st.session_state.schedule = st.session_state.schedule.drop(idx).reset_index(drop=True)
                    save_schedule_to_gsheets(st.session_state.schedule)
                    st.success("삭제되었습니다.")
                    st.rerun()

    if st.session_state.editing_event:
        st.divider()
        st.markdown("### ✏️ 선택 일정 수정")
        ev = st.session_state.editing_event
        
        if ev["type"] == "personal":
            with st.form("edit_personal_form"):
                e_name = st.text_input("일정 이름", value=ev["data"].get("이름", ""))
                e_date = st.date_input("날짜", value=ev["data"].get("날짜", date.today()))
                e_memo = st.text_area("메모", value=ev["data"].get("메모", ""))
                
                if st.form_submit_button("💾 수정사항 저장"):
                    st.session_state.personal_schedule.loc[ev["index"], ["이름", "날짜", "메모"]] = [e_name, e_date, e_memo]
                    st.session_state.editing_event = None
                    st.success("수정 완료되었습니다!")
                    st.rerun()
        else:
            with st.form("edit_study_form"):
                e_title = st.text_input("학습 제목", value=ev["data"].get("제목", ""))
                e_range = st.text_input("목표 범위", value=ev["data"].get("목표 범위", ""))
                e_amount = st.text_input("목표량", value=ev["data"].get("목표량", ""))
                e_done = st.checkbox("완료 여부", value=ev["data"].get("완료여부", False))
                
                if st.form_submit_button("💾 수정사항 저장"):
                    st.session_state.schedule.loc[ev["index"], ["제목", "목표 범위", "목표량", "완료여부"]] = [e_title, e_range, e_amount, e_done]
                    save_schedule_to_gsheets(st.session_state.schedule)
                    st.session_state.editing_event = None
                    st.success("수정 완료되었습니다!")
                    st.rerun()
                    
        if st.button("❌ 수정 취소"):
            st.session_state.editing_event = None
            st.rerun()

# ------------------------------------------
# [오른쪽 칼럼] 탭 관리
# ------------------------------------------
with right_col:
    tab1, tab2, tab3, tab4 = st.tabs([
        TEXTS["TABS"]["TAB1_NAME"], 
        TEXTS["TABS"]["TAB2_NAME"], 
        TEXTS["TABS"]["TAB3_NAME"],
        TEXTS["TABS"]["TAB4_NAME"]
    ])
    
    with tab1:
        st.subheader("🗓️ 개인 일정 추가")
        with st.form("add_personal_form"):
            p_title = st.text_input("이름", placeholder="예: 병원 방문, 약속")
            p_date = st.date_input("날짜", value=date.today())
            
            p_col1, p_col2 = st.columns(2)
            p_start_time = p_col1.time_input("시작 시간", value=time(9, 0))
            p_end_time = p_col2.time_input("종료 시간", value=time(10, 0))
            
            travel_col, tag_col = st.columns(2)
            travel_time = travel_col.selectbox("이동 시간", options=["없음", "15분", "30분", "1시간", "2시간 이상"])
            p_tag = tag_col.text_input("태그", placeholder="예: 개인, 건강")
            p_memo = st.text_area("메모")
            
            if st.form_submit_button("➕ 개인 일정 등록", use_container_width=True):
                new_event = pd.DataFrame([{
                    "id": len(st.session_state.personal_schedule) + 1,
                    "날짜": p_date,
                    "시작 시간": p_start_time.strftime("%H:%M"),
                    "종료 시간": p_end_time.strftime("%H:%M"),
                    "이름": p_title,
                    "이동 시간": travel_time,
                    "태그": p_tag,
                    "메모": p_memo
                }])
                st.session_state.personal_schedule = pd.concat([st.session_state.personal_schedule, new_event], ignore_index=True)
                st.success("개인 일정이 등록되었습니다!")
                st.rerun()

    with tab2:
        st.subheader("📚 정기고사 & 학습 일정 세부 생성")
        
        schedule_type = st.selectbox("학습 일정 종류", options=["정기고사", "수행평가", "기타"])
        
        if schedule_type == "정기고사":
            st.markdown("#### 📝 정기고사 기본 설정")
            exam_name = st.text_input("시험명", value="1학기 중간고사")
            
            col1, col2 = st.columns(2)
            exam_start_date = col1.date_input("시험 시작일", value=date.today() + timedelta(days=14))
            exam_duration = col2.number_input("시험 기간(일)", min_value=1, max_value=10, value=3)
            
            exam_repeat = st.number_input("🔁 반복 회독 수 (N회독)", min_value=1, max_value=5, value=2, help="전체 범위를 시험 전까지 총 몇 번 반복 공부할지 설정합니다.")
            
            st.divider()
            
            head_col1, head_col2 = st.columns([3, 1])
            head_col1.markdown("#### 📚 과목별 고사 일차 & 범위 설정")
            head_col2.button("➕ 과목 추가", on_click=add_subject, use_container_width=True)

            for idx, sub in enumerate(st.session_state.exam_subjects):
                # .get()을 사용하여 KeyError 예방
                s_name = sub.get("name", "")
                s_day = sub.get("day", 1)
                s_tb_start = sub.get("tb_start", 1)
                s_tb_end = sub.get("tb_end", 30)
                s_has_sub = sub.get("has_sub", False)
                s_sub_start = sub.get("sub_start", 1)
                s_sub_end = sub.get("sub_end", 10)

                with st.expander(f"📌 과목 {idx + 1} : {s_name if s_name else '미입력'}", expanded=True):
                    c_name, c_day = st.columns([2, 1])
                    sub["name"] = c_name.text_input(f"과목명 #{idx+1}", value=s_name, key=f"sub_name_{idx}")
                    sub["day"] = c_day.number_input(f"시험 몇일차", min_value=1, max_value=int(exam_duration), value=int(s_day), key=f"sub_day_{idx}")
                    
                    st.caption("📘 **교과서 범위 (페이지)**")
                    tb_c1, tb_c2 = st.columns(2)
                    sub["tb_start"] = tb_c1.number_input("시작", min_value=1, value=int(s_tb_start), key=f"tb_s_{idx}")
                    sub["tb_end"] = tb_c2.number_input("종료", min_value=1, value=int(s_tb_end), key=f"tb_e_{idx}")

                    has_sub = st.checkbox("부교재 포함", value=s_has_sub, key=f"sub_chk_{idx}")
                    sub["has_sub"] = has_sub
                    if has_sub:
                        sub_c1, sub_c2 = st.columns(2)
                        sub["sub_start"] = sub_c1.number_input("부교재 시작", min_value=1, value=int(s_sub_start), key=f"sub_s_{idx}")
                        # 수정 완료: f-string 적용 (sub_e_{idx})
                        sub["sub_end"] = sub_c2.number_input("부교재 종료", min_value=1, value=int(s_sub_end), key=f"sub_e_{idx}")

                    if len(st.session_state.exam_subjects) > 1 and st.button(f"🗑️ 과목 {idx+1} 삭제", key=f"del_sub_{idx}"):
                        remove_subject(idx)
                        st.rerun()

            st.divider()
            
            if st.button("🚀 자동 공부 스케줄 생성", type="primary", use_container_width=True):
                new_schedules = []
                
                # 1. 시험 당일 별표(⭐) 등록
                for day_idx in range(int(exam_duration)):
                    cur_exam_date = exam_start_date + timedelta(days=day_idx)
                    day_num = day_idx + 1
                    day_subs = [s.get("name", "") for s in st.session_state.exam_subjects if s.get("day", 1) == day_num]
                    sub_str = ", ".join(day_subs) if day_subs else "시험"
                    
                    new_schedules.append({
                        "id": len(new_schedules) + 1,
                        "날짜": cur_exam_date,
                        "종류": "⭐ 정기고사",
                        "제목": f"[{exam_name}] {day_num}일차 시험",
                        "목표 범위": sub_str,
                        "목표량": "시험 응시",
                        "완료여부": False,
                        "메모": f"{day_num}일차 시험 과목: {sub_str}"
                    })

                # 2. 직전 대비 (1회독 차)
                for day_num in range(1, int(exam_duration) + 1):
                    prep_date = exam_start_date - timedelta(days=(int(exam_duration) - day_num + 1))
                    day_subs = [s for s in st.session_state.exam_subjects if s.get("day", 1) == day_num]
                    
                    for s in day_subs:
                        tb_pages = s.get("tb_end", 0) - s.get("tb_start", 0) + 1
                        sub_pages = (s.get("sub_end", 0) - s.get("sub_start", 0) + 1) if s.get("has_sub", False) else 0
                        
                        new_schedules.append({
                            "id": len(new_schedules) + 1,
                            "날짜": prep_date,
                            "종류": "🔥 직전대비",
                            "제목": f"[{s.get('name', '')}] 직전 총복습",
                            "목표 범위": f"교과서 p.{s.get('tb_start')}~{s.get('tb_end')}" + (f", 부교재 p.{s.get('sub_start')}~{s.get('sub_end')}" if s.get("has_sub") else ""),
                            "목표량": f"전체 범위 ({tb_pages + sub_pages}p) 1회독",
                            "완료여부": False,
                            "메모": f"{day_num}일차 시험 대비 최종 점검"
                        })

                # 3. N회독 기본 배치
                max_daily_pages = st.session_state.study_style["max_pages_per_day"]
                start_prep_date = exam_start_date - timedelta(days=int(exam_duration) + 1)
                curr_date = start_prep_date
                
                for r in range(int(exam_repeat) - 1, 0, -1):
                    for s in st.session_state.exam_subjects:
                        tb_start = s.get("tb_start", 1)
                        tb_end = s.get("tb_end", 1)
                        tb_pages = tb_end - tb_start + 1
                        days_needed = math.ceil(tb_pages / max_daily_pages) if max_daily_pages > 0 else 1
                        
                        for p in range(days_needed):
                            p_start = tb_start + p * max_daily_pages
                            p_end = min(tb_end, p_start + max_daily_pages - 1)
                            
                            new_schedules.append({
                                "id": len(new_schedules) + 1,
                                "날짜": curr_date,
                                "종류": f"📖 {r+1}회독 학습",
                                "제목": f"[{s.get('name', '')}] N회독 분량 학습",
                                "목표 범위": f"교과서 p.{p_start}~{p_end}",
                                "목표량": f"{p_end - p_start + 1} 페이지 공부",
                                "완료여부": False,
                                "메모": f"{r+1}회독 계획에 따른 자동 분배"
                            })
                            curr_date -= timedelta(days=1)

                new_df = pd.DataFrame(new_schedules)
                st.session_state.schedule = pd.concat([st.session_state.schedule, new_df], ignore_index=True)
                save_schedule_to_gsheets(st.session_state.schedule)
                
                st.success("시험 일정 및 자동 학습 스케줄이 성공적으로 생성되었습니다!")
                st.rerun()

    with tab3:
        st.subheader("⚙️ 학습 방식 설정")
        st.caption("개인의 학습 가능 스피드와 목표 수준을 설정합니다.")
        
        m_subs = st.number_input("하루 최대 학습 과목 수", min_value=1, max_value=6, value=st.session_state.study_style["max_subjects_per_day"])
        m_pages = st.number_input("하루 과목당 목표 학습 페이지 수", min_value=5, max_value=100, value=st.session_state.study_style["max_pages_per_day"], step=5)
        
        if st.button("💾 학습 방식 설정 저장", use_container_width=True):
            st.session_state.study_style["max_subjects_per_day"] = m_subs
            st.session_state.study_style["max_pages_per_day"] = m_pages
            st.success("학습 방식 설정이 저장되었습니다!")

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
