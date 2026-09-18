import streamlit as st
import pandas as pd
from datetime import date, datetime, time, timedelta
import math
import calendar
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 앱 내 전체 텍스트 모음
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
        "NO_DATA": "내보낼 스케줄 데이터가 없습니다."
    },
    "CALENDAR": {
        "HEADER": "🗓️ 달력 보기",
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

st.set_page_config(page_title=TEXTS["APP_TITLE"].replace("📅 ", ""), layout="wide")

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

# ==========================================
# 세션 상태 초기화
# ==========================================
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
        "max_pages_per_day": 5  # 기본값을 5로 설정
    }

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "current_year_month" not in st.session_state:
    today = date.today()
    st.session_state.current_year_month = (today.year, today.month)

# 기본 과목을 비워둔 초기화 (1개 빈 입력폼)
if "exam_subjects" not in st.session_state:
    st.session_state.exam_subjects = [
        {
            "name": "", "day": 1,
            "tb_start": 1, "tb_end": 30,
            "has_sub": False, "sub_start": 1, "sub_end": 10
        }
    ]

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
# 사이드바
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

left_col, right_col = st.columns([1.2, 0.8], gap="large")

# ------------------------------------------
# [왼쪽 칼럼] 달력 Grid & 상세 일정
# ------------------------------------------
with left_col:
    st.subheader(TEXTS["CALENDAR"]["HEADER"])

    year, month = st.session_state.current_year_month
    
    # 1. 월 이동 네비게이션
    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("◀ 이전달", key="btn_prev_month", use_container_width=True):
            if month == 1:
                st.session_state.current_year_month = (year - 1, 12)
            else:
                st.session_state.current_year_month = (year, month - 1)
            st.rerun()

    with nav2:
        st.markdown(f"<h3 style='text-align: center; margin: 0;'>{year}년 {month}월</h3>", unsafe_allow_html=True)

    with nav3:
        if st.button("다음달 ▶", key="btn_next_month", use_container_width=True):
            if month == 12:
                st.session_state.current_year_month = (year + 1, 1)
            else:
                st.session_state.current_year_month = (year, month + 1)
            st.rerun()

    # 2. 요일 헤더 표시
    cols = st.columns(7)
    for i, w in enumerate(TEXTS["CALENDAR"]["WEEKDAYS"]):
        cols[i].markdown(f"**{w}**")

    # 3. 달력 날짜 그리드 생성
    cal = calendar.monthcalendar(year, month)
    
    # 해당 월의 일정 데이터 사전 추출
    month_schedules = {}
    if not st.session_state.schedule.empty:
        for _, r in st.session_state.schedule.iterrows():
            d = r["날짜"]
            if isinstance(d, date) and d.year == year and d.month == month:
                month_schedules.setdefault(d.day, []).append(r["종류"])

    if not st.session_state.personal_schedule.empty:
        for _, r in st.session_state.personal_schedule.iterrows():
            d = r["날짜"]
            if isinstance(d, date) and d.year == year and d.month == month:
                month_schedules.setdefault(d.day, []).append("개인")

    for week in cal:
        w_cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                w_cols[i].write("")
            else:
                curr_d = date(year, month, day)
                is_selected = (curr_d == st.session_state.selected_date)
                
                # 배지/아이콘 생성
                badges = month_schedules.get(day, [])
                badge_str = ""
                if any("⭐" in str(b) or "시험" in str(b) for b in badges):
                    badge_str += "⭐"
                if any("🔥" in str(b) for b in badges):
                    badge_str += "🔥"
                if any("📖" in str(b) for b in badges):
                    badge_str += "📖"
                if "개인" in badges:
                    badge_str += "📌"

                label = f"{day} {badge_str}"
                btn_type = "primary" if is_selected else "secondary"

                if w_cols[i].button(label, key=f"cal_day_{year}_{month}_{day}", use_container_width=True, type=btn_type):
                    st.session_state.selected_date = curr_d
                    st.rerun()

    st.divider()

    # 4. 선택 날짜 상세 일정 표시
    selected_dt = st.session_state.selected_date
    st.markdown(f"### 📅 {selected_dt.strftime('%Y년 %m월 %d일')} 일정 상세")

    day_personals = st.session_state.personal_schedule[st.session_state.personal_schedule["날짜"] == selected_dt]
    day_studies = st.session_state.schedule[st.session_state.schedule["날짜"] == selected_dt]

    if day_personals.empty and day_studies.empty:
        st.info("해당 날짜에 등록된 일정이 없습니다. 달력 날짜를 누르거나 오른쪽에서 일정을 추가하세요.")
    else:
        for idx, row in day_personals.iterrows():
            with st.expander(f"🛑 [개인] {row['이름']} ({row['시작 시간']} ~ {row['종료 시간']})"):
                st.write(f"**이동시간:** {row['이동 시간']} | **태그:** {row['태그']}")
                st.write(f"**메모:** {row['메모']}")
                c1, c2 = st.columns(2)
                if c1.button("✏️ 수정", key=f"edit_p_{idx}"):
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
                if c1.button("✏️ 수정", key=f"edit_s_{idx}"):
                    st.session_state.editing_event = {"type": "study", "data": row.to_dict(), "index": idx}
                    st.rerun()
                if c2.button("🗑️ 삭제", key=f"del_s_{idx}"):
                    st.session_state.schedule = st.session_state.schedule.drop(idx).reset_index(drop=True)
                    save_schedule_to_gsheets(st.session_state.schedule)
                    st.success("삭제되었습니다.")
                    st.rerun()

    # 일정 수정 폼
    if st.session_state.editing_event:
        st.divider()
        st.markdown("### ✏️ 일정 내용 수정")
        ev = st.session_state.editing_event
        
        if ev["type"] == "personal":
            with st.form("edit_personal_form"):
                e_name = st.text_input("일정 이름", value=ev["data"].get("이름", ""))
                e_date = st.date_input("날짜", value=ev["data"].get("날짜", date.today()))
                e_memo = st.text_area("메모", value=ev["data"].get("메모", ""))
                if st.form_submit_button("💾 저장"):
                    st.session_state.personal_schedule.loc[ev["index"], ["이름", "날짜", "메모"]] = [e_name, e_date, e_memo]
                    st.session_state.editing_event = None
                    st.rerun()
        else:
            with st.form("edit_study_form"):
                e_title = st.text_input("학습 제목", value=ev["data"].get("제목", ""))
                e_range = st.text_input("목표 범위", value=ev["data"].get("목표 범위", ""))
                e_amount = st.text_input("목표량", value=ev["data"].get("목표량", ""))
                e_done = st.checkbox("완료 여부", value=ev["data"].get("완료여부", False))
                if st.form_submit_button("💾 저장"):
                    st.session_state.schedule.loc[ev["index"], ["제목", "목표 범위", "목표량", "완료여부"]] = [e_title, e_range, e_amount, e_done]
                    save_schedule_to_gsheets(st.session_state.schedule)
                    st.session_state.editing_event = None
                    st.rerun()

        if st.button("❌ 취소"):
            st.session_state.editing_event = None
            st.rerun()

# ------------------------------------------
# [오른쪽 칼럼] 탭 관리 (4개 탭)
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
            p_date = st.date_input("날짜", value=st.session_state.selected_date)
            
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
            
            exam_repeat = st.number_input("🔁 반복 회독 수 (N회독)", min_value=1, max_value=5, value=2, help="시험 전까지 전체 범위를 총 몇 번 반복 공부할지 지정합니다.")
            
            st.divider()
            
            head_col1, head_col2 = st.columns([3, 1])
            head_col1.markdown("#### 📚 과목별 고사 일차 & 범위 설정")
            head_col2.button("➕ 과목 추가", on_click=add_subject, use_container_width=True)

            for idx, sub in enumerate(st.session_state.exam_subjects):
                s_name = sub.get("name", "")
                s_day = sub.get("day", 1)
                s_tb_start = sub.get("tb_start", 1)
                s_tb_end = sub.get("tb_end", 30)
                s_has_sub = sub.get("has_sub", False)
                s_sub_start = sub.get("sub_start", 1)
                s_sub_end = sub.get("sub_end", 10)

                with st.expander(f"📌 과목 {idx + 1} : {s_name if s_name else '과목명을 입력하세요'}", expanded=True):
                    c_name, c_day = st.columns([2, 1])
                    sub["name"] = c_name.text_input(f"과목명 #{idx+1}", value=s_name, key=f"sub_name_{idx}", placeholder="예: 국어, 수학")
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
                        sub["sub_end"] = sub_c2.number_input("부교재 종료", min_value=1, value=int(s_sub_end), key=f"sub_e_{idx}")

                    if len(st.session_state.exam_subjects) > 1 and st.button(f"🗑️ 과목 {idx+1} 삭제", key=f"del_sub_{idx}"):
                        remove_subject(idx)
                        st.rerun()

            st.divider()

            if st.button("🚀 스마트 과목 공부 스케줄 생성", type="primary", use_container_width=True):
                valid_subjects = [s for s in st.session_state.exam_subjects if s.get("name", "").strip() != ""]
                
                if not valid_subjects:
                    st.error("최소 한 개 이상의 과목명을 입력해주세요.")
                else:
                    new_schedules = []

                    # 1. 시험 당일 일정 (⭐ 표시)
                    for day_idx in range(int(exam_duration)):
                        cur_exam_date = exam_start_date + timedelta(days=day_idx)
                        day_num = day_idx + 1
                        day_subs = [s.get("name") for s in valid_subjects if s.get("day") == day_num]
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

                    # 2. 직전 대비 스케줄 (D-1 ~ D-N)
                    # 시험 1일차 과목 -> D-1 공부, 2일차 과목 -> D-2 공부...
                    for day_num in range(1, int(exam_duration) + 1):
                        prep_date = exam_start_date - timedelta(days=day_num)
                        day_subs = [s for s in valid_subjects if s.get("day") == day_num]

                        for s in day_subs:
                            tb_pages = s.get("tb_end", 0) - s.get("tb_start", 0) + 1
                            sub_pages = (s.get("sub_end", 0) - s.get("sub_start", 0) + 1) if s.get("has_sub") else 0
                            
                            new_schedules.append({
                                "id": len(new_schedules) + 1,
                                "날짜": prep_date,
                                "종류": "🔥 직전대비",
                                "제목": f"[{s.get('name')}] 시험 직전 총복습 (D-{day_num})",
                                "목표 범위": f"교과서 p.{s.get('tb_start')}~{s.get('tb_end')}" + (f", 부교재 p.{s.get('sub_start')}~{s.get('sub_end')}" if s.get("has_sub") else ""),
                                "목표량": f"전체 범위 ({tb_pages + sub_pages}p) 직전 점검",
                                "완료여부": False,
                                "메모": f"{day_num}일차 시험 대비 전날 집중 공부"
                            })

                    # 3. N회독 공부 일정 (D-(시험기간+1) 부터 역순 배치)
                    # 하루 목표 페이지 수 설정값 반영
                    max_pages = max(1, st.session_state.study_style["max_pages_per_day"])
                    
                    # 과목별 단원/분할 큐 생성
                    study_chunks = []
                    for r in range(int(exam_repeat) - 1, 0, -1):
                        for s in valid_subjects:
                            tb_s, tb_e = s.get("tb_start", 1), s.get("tb_end", 1)
                            total_p = tb_e - tb_s + 1
                            num_chunks = math.ceil(total_p / max_pages)

                            for c in range(num_chunks):
                                chunk_start = tb_s + (c * max_pages)
                                chunk_end = min(tb_e, chunk_start + max_pages - 1)
                                study_chunks.append({
                                    "name": s.get("name"),
                                    "range": f"p.{chunk_start}~{chunk_end}",
                                    "pages": chunk_end - chunk_start + 1,
                                    "repeat": r + 1
                                })

                    # 직전 대비 시작 직전 날짜부터 차례대로 교대 배치
                    start_prep_date = exam_start_date - timedelta(days=int(exam_duration) + 1)
                    curr_date = start_prep_date

                    for chunk in study_chunks:
                        new_schedules.append({
                            "id": len(new_schedules) + 1,
                            "날짜": curr_date,
                            "종류": f"📖 {chunk['repeat']}회독 학습",
                            "제목": f"[{chunk['name']}] 단원 분할 공부",
                            "목표 범위": chunk["range"],
                            "목표량": f"{chunk['pages']} 페이지 학습",
                            "완료여부": False,
                            "메모": f"{chunk['repeat']}회독 계획에 따라 자동 생성됨"
                        })
                        curr_date -= timedelta(days=1)

                    new_df = pd.DataFrame(new_schedules)
                    st.session_state.schedule = pd.concat([st.session_state.schedule, new_df], ignore_index=True)
                    save_schedule_to_gsheets(st.session_state.schedule)

                    st.success("요청하신 규칙에 따라 D-Day 및 과목별 자동 공부 일정이 성공적으로 생성되었습니다!")
                    st.rerun()

    with tab3:
        st.subheader("⚙️ 학습 방식 설정")
        st.caption("하루에 소화할 공부 목표량을 설정합니다.")

        m_subs = st.number_input("하루 최대 학습 과목 수", min_value=1, max_value=6, value=st.session_state.study_style["max_subjects_per_day"])
        m_pages = st.number_input("하루 과목당 목표 학습 페이지 수", min_value=1, max_value=100, value=st.session_state.study_style["max_pages_per_day"], step=1)

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
