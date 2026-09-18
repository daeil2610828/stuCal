import streamlit as st
import pandas as pd
import json
from datetime import date, datetime, time, timedelta
import calendar

# ==========================================
# 앱 내 전체 텍스트 모음
# ==========================================
TEXTS = {
    "APP_TITLE": "📅 스마트 시험 D-Day & 공부 스케줄러",
    "APP_CAPTION": "개인 일정, 학교 시간표, 학습지 유동 조절을 반영한 맞춤형 학습 스케줄링 서비스",
    "SIDEBAR": {
        "TITLE": "📁 데이터 & 백업 관리",
        "BACKUP_HEADER": "📦 전체 설정/데이터 백업",
        "EXPORT_LABEL": "📤 전체 설정 백업 (JSON)",
        "IMPORT_HEADER": "📥 데이터 불러오기",
        "IMPORT_LABEL": "JSON 백업 파일 선택",
        "IMPORT_MODE": "불러오기 방식 선택",
        "IMPORT_BTN": "데이터 적용하기",
        "IMPORT_SUCCESS": "성공적으로 데이터를 불러왔습니다!",
        "IMPORT_ERROR": "파일을 읽는 중 오류가 발생했습니다: ",
        "RESET_HEADER": "⚠️ 일정 데이터 초기화",
        "RESET_BTN": "🚨 모든 일정 리셋",
        "RESET_CONFIRM_TITLE": "⚠️ 정말로 모든 일정을 리셋하시겠습니까?",
        "RESET_CONFIRM_BTN": "네, 모든 일정을 삭제합니다",
        "RESET_CANCEL_BTN": "취소",
        "RESET_SUCCESS": "모든 일정 데이터가 성공적으로 리셋되었습니다!"
    },
    "CALENDAR": {
        "HEADER": "🗓️ 달력 보기",
        "WEEKDAYS": ["일", "월", "화", "수", "목", "금", "토"]
    },
    "TABS": {
        "TAB1_NAME": "1. 개인 일정 추가",
        "TAB2_NAME": "2. 정기고사/학습 등록",
        "TAB3_NAME": "3. 학습 방식 & 시간표",
        "TAB4_NAME": "4. 일상 루틴 설정"
    },
    "ROUTINE": {
        "HEADER": "⏰ 일상 루틴 (취침 & 식사 시간)",
        "SAVE_BTN": "💾 루틴 설정 저장",
        "SAVE_SUCCESS": "일상 루틴 설정이 저장되었습니다!"
    }
}

st.set_page_config(page_title=TEXTS["APP_TITLE"].replace("📅 ", ""), layout="wide")

# ==========================================
# 기본 데이터프레임 스키마 정의
# ==========================================
STUDY_COLUMNS = ["id", "날짜", "종류", "제목", "목표 범위", "목표량", "완료여부", "메모"]
PERSONAL_COLUMNS = ["id", "날짜", "시작 시간", "종료 시간", "이름", "이동 시간", "태그", "메모"]

def create_empty_study_df():
    return pd.DataFrame(columns=STUDY_COLUMNS)

def create_empty_personal_df():
    return pd.DataFrame(columns=PERSONAL_COLUMNS)

def create_empty_subject():
    return {
        "name": "",
        "day": 1,
        "tb_ranges": [{"start": 1, "end": 20}],
        "has_sub": False,
        "sub_ranges": [{"start": 1, "end": 10}],
        "has_sheets": False,
        "sheets": [{"name": "학습지 1", "related_page": 5}]
    }

# ==========================================
# 세션 상태 초기화
# ==========================================
if "schedule" not in st.session_state or st.session_state.schedule is None or st.session_state.schedule.empty:
    st.session_state.schedule = create_empty_study_df()

if "personal_schedule" not in st.session_state or st.session_state.personal_schedule is None or st.session_state.personal_schedule.empty:
    st.session_state.personal_schedule = create_empty_personal_df()

if "routine" not in st.session_state or not isinstance(st.session_state.routine, dict):
    st.session_state.routine = {
        "sleep": {"start": time(23, 0), "end": time(7, 0)},
        "meals": [
            {"name": "아침", "start": time(7, 30), "duration": 30},
            {"name": "점심", "start": time(12, 30), "duration": 60},
            {"name": "저녁", "start": time(19, 0), "duration": 60}
        ]
    }

if "study_style" not in st.session_state or not isinstance(st.session_state.study_style, dict):
    st.session_state.study_style = {
        "target_hours": 4.0,
        "max_pages_per_day": 10,
        "weekday_start_time": {day: time(18, 0) for day in ["월", "화", "수", "목", "금", "토", "일"]},
        "school": {
            "go_time": time(8, 20),
            "leave_time": time(16, 30),
            "periods": {
                p: {"active": True, "start": time(9 + (p-1)//2, 0 if p%2!=0 else 50), "end": time(9 + (p-1)//2, 45 if p%2!=0 else 35)}
                for p in range(1, 9)
            }
        }
    }

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "current_year_month" not in st.session_state:
    today = date.today()
    st.session_state.current_year_month = (today.year, today.month)

if "show_reset_confirm" not in st.session_state:
    st.session_state.show_reset_confirm = False

if "exam_subjects" not in st.session_state or not st.session_state.exam_subjects:
    st.session_state.exam_subjects = [create_empty_subject()]

if "editing_event" not in st.session_state:
    st.session_state.editing_event = None

def add_subject():
    st.session_state.exam_subjects.append(create_empty_subject())

def remove_subject(index):
    if len(st.session_state.exam_subjects) > 1:
        st.session_state.exam_subjects.pop(index)

# ==========================================
# 직렬화 / 역직렬화 헬퍼 함수
# ==========================================
def serialize_state():
    state_dict = {
        "schedule": st.session_state.schedule.to_dict(orient="records"),
        "personal_schedule": st.session_state.personal_schedule.to_dict(orient="records"),
        "exam_subjects": st.session_state.exam_subjects,
        "routine": {
            "sleep": {
                "start": st.session_state.routine["sleep"]["start"].strftime("%H:%M"),
                "end": st.session_state.routine["sleep"]["end"].strftime("%H:%M")
            },
            "meals": [
                {
                    "name": m["name"],
                    "start": m["start"].strftime("%H:%M"),
                    "duration": m["duration"]
                } for m in st.session_state.routine["meals"]
            ]
        },
        "study_style": {
            "target_hours": st.session_state.study_style["target_hours"],
            "max_pages_per_day": st.session_state.study_style["max_pages_per_day"],
            "weekday_start_time": {
                k: v.strftime("%H:%M") for k, v in st.session_state.study_style["weekday_start_time"].items()
            },
            "school": {
                "go_time": st.session_state.study_style["school"]["go_time"].strftime("%H:%M"),
                "leave_time": st.session_state.study_style["school"]["leave_time"].strftime("%H:%M"),
                "periods": {
                    k: {
                        "active": v["active"],
                        "start": v["start"].strftime("%H:%M"),
                        "end": v["end"].strftime("%H:%M")
                    } for k, v in st.session_state.study_style["school"]["periods"].items()
                }
            }
        }
    }
    return json.dumps(state_dict, default=str, ensure_ascii=False, indent=2)

def deserialize_state(data_json, mode="replace"):
    data = json.loads(data_json)
    
    # 1. 학습 스케줄 복원
    s_records = data.get("schedule", [])
    if s_records:
        new_s_df = pd.DataFrame(s_records)
        if "날짜" in new_s_df.columns:
            new_s_df["날짜"] = pd.to_datetime(new_s_df["날짜"]).dt.date
    else:
        new_s_df = create_empty_study_df()

    for col in STUDY_COLUMNS:
        if col not in new_s_df.columns:
            new_s_df[col] = None

    if mode == "merge" and not st.session_state.schedule.empty:
        st.session_state.schedule = pd.concat([st.session_state.schedule, new_s_df], ignore_index=True).drop_duplicates()
    else:
        st.session_state.schedule = new_s_df[STUDY_COLUMNS]

    # 2. 개인 일정 복원
    p_records = data.get("personal_schedule", [])
    if p_records:
        new_p_df = pd.DataFrame(p_records)
        if "날짜" in new_p_df.columns:
            new_p_df["날짜"] = pd.to_datetime(new_p_df["날짜"]).dt.date
    else:
        new_p_df = create_empty_personal_df()

    for col in PERSONAL_COLUMNS:
        if col not in new_p_df.columns:
            new_p_df[col] = None

    if mode == "merge" and not st.session_state.personal_schedule.empty:
        st.session_state.personal_schedule = pd.concat([st.session_state.personal_schedule, new_p_df], ignore_index=True).drop_duplicates()
    else:
        st.session_state.personal_schedule = new_p_df[PERSONAL_COLUMNS]

    # 3. 과목 복원
    if "exam_subjects" in data:
        if mode == "merge":
            st.session_state.exam_subjects.extend(data["exam_subjects"])
        else:
            st.session_state.exam_subjects = data["exam_subjects"]

    # 4. 루틴 복원
    if "routine" in data:
        r_data = data["routine"]
        st.session_state.routine["sleep"]["start"] = datetime.strptime(r_data["sleep"]["start"], "%H:%M").time()
        st.session_state.routine["sleep"]["end"] = datetime.strptime(r_data["sleep"]["end"], "%H:%M").time()
        st.session_state.routine["meals"] = [
            {
                "name": m["name"],
                "start": datetime.strptime(m["start"], "%H:%M").time(),
                "duration": m["duration"]
            } for m in r_data.get("meals", [])
        ]

    # 5. 학습 방식 복원
    if "study_style" in data:
        ss_data = data["study_style"]
        st.session_state.study_style["target_hours"] = float(ss_data.get("target_hours", 4.0))
        st.session_state.study_style["max_pages_per_day"] = int(ss_data.get("max_pages_per_day", 10))
        
        if "weekday_start_time" in ss_data:
            st.session_state.study_style["weekday_start_time"] = {
                k: datetime.strptime(v, "%H:%M").time() for k, v in ss_data["weekday_start_time"].items()
            }
            
        if "school" in ss_data:
            sch = ss_data["school"]
            st.session_state.study_style["school"]["go_time"] = datetime.strptime(sch["go_time"], "%H:%M").time()
            st.session_state.study_style["school"]["leave_time"] = datetime.strptime(sch["leave_time"], "%H:%M").time()
            if "periods" in sch:
                st.session_state.study_style["school"]["periods"] = {
                    int(k): {
                        "active": v["active"],
                        "start": datetime.strptime(v["start"], "%H:%M").time(),
                        "end": datetime.strptime(v["end"], "%H:%M").time()
                    } for k, v in sch["periods"].items()
                }

# ==========================================
# 사이드바
# ==========================================
st.sidebar.title(TEXTS["SIDEBAR"]["TITLE"])

st.sidebar.subheader(TEXTS["SIDEBAR"]["BACKUP_HEADER"])
backup_json = serialize_state()
st.sidebar.download_button(
    label=TEXTS["SIDEBAR"]["EXPORT_LABEL"],
    data=backup_json,
    file_name=f"stucal_backup_{date.today()}.json",
    mime="application/json",
    use_container_width=True
)

st.sidebar.divider()
st.sidebar.subheader(TEXTS["SIDEBAR"]["IMPORT_HEADER"])
import_file = st.sidebar.file_uploader(TEXTS["SIDEBAR"]["IMPORT_LABEL"], type=["json"])
import_mode = st.sidebar.radio(
    TEXTS["SIDEBAR"]["IMPORT_MODE"],
    options=["대치 (덮어쓰기)", "병합 (기존 데이터에 추가)"],
    index=0
)

if import_file is not None:
    if st.sidebar.button(TEXTS["SIDEBAR"]["IMPORT_BTN"], use_container_width=True):
        try:
            mode_code = "replace" if "대치" in import_mode else "merge"
            deserialize_state(import_file.read().decode("utf-8"), mode=mode_code)
            st.sidebar.success(TEXTS["SIDEBAR"]["IMPORT_SUCCESS"])
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"{TEXTS['SIDEBAR']['IMPORT_ERROR']}{e}")

st.sidebar.divider()

st.sidebar.subheader(TEXTS["SIDEBAR"]["RESET_HEADER"])

if not st.session_state.show_reset_confirm:
    if st.sidebar.button(TEXTS["SIDEBAR"]["RESET_BTN"], use_container_width=True):
        st.session_state.show_reset_confirm = True
        st.rerun()
else:
    st.sidebar.warning(TEXTS["SIDEBAR"]["RESET_CONFIRM_TITLE"])
    rc_col1, rc_col2 = st.sidebar.columns(2)
    
    if rc_col1.button(TEXTS["SIDEBAR"]["RESET_CONFIRM_BTN"], type="primary", use_container_width=True):
        st.session_state.schedule = create_empty_study_df()
        st.session_state.personal_schedule = create_empty_personal_df()
        st.session_state.show_reset_confirm = False
        st.sidebar.success(TEXTS["SIDEBAR"]["RESET_SUCCESS"])
        st.rerun()
        
    if rc_col2.button(TEXTS["SIDEBAR"]["RESET_CANCEL_BTN"], use_container_width=True):
        st.session_state.show_reset_confirm = False
        st.rerun()

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

    cols = st.columns(7)
    for i, w in enumerate(TEXTS["CALENDAR"]["WEEKDAYS"]):
        cols[i].markdown(f"**{w}**")

    cal = calendar.monthcalendar(year, month)
    
    month_schedules = {}
    if not st.session_state.schedule.empty and "날짜" in st.session_state.schedule.columns:
        for _, r in st.session_state.schedule.iterrows():
            d = r["날짜"]
            if isinstance(d, date) and d.year == year and d.month == month:
                month_schedules.setdefault(d.day, []).append(r["종류"])

    if not st.session_state.personal_schedule.empty and "날짜" in st.session_state.personal_schedule.columns:
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
                
                badges = month_schedules.get(day, [])
                badge_str = ""
                if any("⭐" in str(b) or "시험" in str(b) or "수행" in str(b) for b in badges):
                    badge_str += "⭐"
                if any("🔥" in str(b) for b in badges):
                    badge_str += "🔥"
                if any("📖" in str(b) or "준비" in str(b) for b in badges):
                    badge_str += "📖"
                if "개인" in badges:
                    badge_str += "📌"

                label = f"{day} {badge_str}"
                btn_type = "primary" if is_selected else "secondary"

                if w_cols[i].button(label, key=f"cal_day_{year}_{month}_{day}", use_container_width=True, type=btn_type):
                    st.session_state.selected_date = curr_d
                    st.rerun()

    st.divider()

    selected_dt = st.session_state.selected_date
    st.markdown(f"### 📅 {selected_dt.strftime('%Y년 %m월 %d일')} 일정 상세")

    day_personals = st.session_state.personal_schedule[st.session_state.personal_schedule["날짜"] == selected_dt] if not st.session_state.personal_schedule.empty and "날짜" in st.session_state.personal_schedule.columns else create_empty_personal_df()
    day_studies = st.session_state.schedule[st.session_state.schedule["날짜"] == selected_dt] if not st.session_state.schedule.empty and "날짜" in st.session_state.schedule.columns else create_empty_study_df()

    if day_personals.empty and day_studies.empty:
        st.info("해당 날짜에 등록된 일정이 없습니다.")
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
            is_exam = "⭐" in str(row["종류"]) or "시험" in str(row["종류"]) or "수행평가" in str(row["종류"])
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
                    st.success("삭제되었습니다.")
                    st.rerun()

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

    # --------------------------------------
    # TAB 1: 개인 일정 추가
    # --------------------------------------
    with tab1:
        st.subheader("🗓️ 개인 일정 추가")
        with st.form("add_personal_form"):
            p_title = st.text_input("이름", placeholder="예: 병원 방문, 학원 수업")
            p_date = st.date_input("시작 날짜", value=st.session_state.selected_date)
            
            p_col1, p_col2 = st.columns(2)
            p_start_time = p_col1.time_input("시작 시간", value=time(9, 0))
            p_end_time = p_col2.time_input("종료 시간", value=time(10, 0))
            
            travel_col, tag_col = st.columns(2)
            travel_time = travel_col.selectbox("이동 시간", options=["없음", "15분", "30분", "1시간", "2시간 이상"])
            p_tag = tag_col.text_input("태그", placeholder="예: 개인, 건강, 학원")
            
            st.markdown("🔄 **반복 설정**")
            repeat_type = st.selectbox("반복 방식", options=["반복 없음", "횟수 지정 (N회)", "종료일 지정"])
            
            rep_count = 1
            rep_end_date = p_date
            if repeat_type == "횟수 지정 (N회)":
                rep_count = st.number_input("반복 횟수", min_value=1, max_value=52, value=4)
            elif repeat_type == "종료일 지정":
                rep_end_date = st.date_input("반복 종료일", value=p_date + timedelta(days=30))
                
            p_memo = st.text_area("메모")
            
            if st.form_submit_button("➕ 개인 일정 등록", use_container_width=True):
                new_events = []
                cur_dt = p_date
                idx_step = 0
                
                while True:
                    if repeat_type == "반복 없음" and idx_step >= 1: break
                    if repeat_type == "횟수 지정 (N회)" and idx_step >= rep_count: break
                    if repeat_type == "종료일 지정" and cur_dt > rep_end_date: break
                        
                    new_events.append({
                        "id": len(st.session_state.personal_schedule) + len(new_events) + 1,
                        "날짜": cur_dt,
                        "시작 시간": p_start_time.strftime("%H:%M"),
                        "종료 시간": p_end_time.strftime("%H:%M"),
                        "이름": p_title,
                        "이동 시간": travel_time,
                        "태그": p_tag,
                        "메모": p_memo
                    })
                    cur_dt += timedelta(days=7)
                    idx_step += 1
                    
                st.session_state.personal_schedule = pd.concat([st.session_state.personal_schedule, pd.DataFrame(new_events)], ignore_index=True)
                st.success(f"{len(new_events)}개의 개인 일정이 등록되었습니다!")
                st.rerun()

    # --------------------------------------
    # TAB 2: 정기고사/학습/수행평가 등록
    # --------------------------------------
    with tab2:
        st.subheader("📚 정기고사 & 수행평가 학습 일정 등록")
        
        schedule_type = st.selectbox("학습 일정 종류", options=["정기고사", "수행평가", "기타"])
        
        # ----------------------------------
        # 1. 정기고사
        # ----------------------------------
        if schedule_type == "정기고사":
            st.markdown("#### 📝 정기고사 기본 설정")
            exam_name = st.text_input("시험명", value="1학기 중간고사")
            
            col1, col2 = st.columns(2)
            exam_start_date = col1.date_input("시험 시작일", value=date.today() + timedelta(days=14))
            exam_duration = col2.number_input("시험 기간(일)", min_value=1, max_value=10, value=3)
            
            exam_repeat = st.number_input("🔁 반복 회독 수 (N회독)", min_value=1, max_value=5, value=2)
            
            st.divider()
            head_col1, head_col2 = st.columns([3, 1])
            head_col1.markdown("#### 📚 과목별 고사 일차 & 상세 범위")
            head_col2.button("➕ 과목 추가", on_click=add_subject, use_container_width=True)

            for idx, sub in enumerate(st.session_state.exam_subjects):
                s_name = sub.get("name", "")
                s_day = sub.get("day", 1)

                with st.expander(f"📌 과목 {idx + 1} : {s_name if s_name else '과목명을 입력하세요'}", expanded=True):
                    c_name, c_day = st.columns([2, 1])
                    sub["name"] = c_name.text_input(f"과목명 #{idx+1}", value=s_name, key=f"sub_name_{idx}", placeholder="예: 국어, 수학")
                    sub["day"] = c_day.number_input(f"시험 몇일차", min_value=1, max_value=int(exam_duration), value=int(s_day), key=f"sub_day_{idx}")
                    
                    st.caption("📘 **교과서 범위 설정**")
                    tb_ranges = sub.get("tb_ranges", [{"start": 1, "end": 20}])
                    for r_idx, r_val in enumerate(tb_ranges):
                        rc1, rc2, rc3 = st.columns([2, 2, 1])
                        r_val["start"] = rc1.number_input(f"시작 p", min_value=1, value=int(r_val["start"]), key=f"tb_s_{idx}_{r_idx}")
                        r_val["end"] = rc2.number_input(f"종료 p", min_value=1, value=int(r_val["end"]), key=f"tb_e_{idx}_{r_idx}")
                        if len(tb_ranges) > 1 and rc3.button("🗑️", key=f"del_tb_r_{idx}_{r_idx}"):
                            tb_ranges.pop(r_idx)
                            st.rerun()
                    if st.button("➕ 교과서 범위 추가", key=f"add_tb_r_{idx}"):
                        tb_ranges.append({"start": 1, "end": 10})
                        st.rerun()
                    sub["tb_ranges"] = tb_ranges

                    st.divider()
                    has_sub = st.checkbox("부교재 포함", value=sub.get("has_sub", False), key=f"sub_chk_{idx}")
                    sub["has_sub"] = has_sub
                    if has_sub:
                        sub_ranges = sub.get("sub_ranges", [{"start": 1, "end": 10}])
                        for sr_idx, sr_val in enumerate(sub_ranges):
                            src1, src2, src3 = st.columns([2, 2, 1])
                            sr_val["start"] = src1.number_input(f"부교재 시작 p", min_value=1, value=int(sr_val["start"]), key=f"sub_s_{idx}_{sr_idx}")
                            sr_val["end"] = src2.number_input(f"부교재 종료 p", min_value=1, value=int(sr_val["end"]), key=f"sub_e_{idx}_{sr_idx}")
                            if len(sub_ranges) > 1 and src3.button("🗑️", key=f"del_sub_r_{idx}_{sr_idx}"):
                                sub_ranges.pop(sr_idx)
                                st.rerun()
                        if st.button("➕ 부교재 범위 추가", key=f"add_sub_r_{idx}"):
                            sub_ranges.append({"start": 1, "end": 10})
                            st.rerun()
                        sub["sub_ranges"] = sub_ranges

                    st.divider()
                    has_sheets = st.checkbox("학습지 포함", value=sub.get("has_sheets", False), key=f"sheet_chk_{idx}")
                    sub["has_sheets"] = has_sheets
                    if has_sheets:
                        sheets = sub.get("sheets", [{"name": "학습지 1", "related_page": 5}])
                        for sh_idx, sh_val in enumerate(sheets):
                            shc1, shc2, shc3 = st.columns([2, 2, 1])
                            sh_val["name"] = shc1.text_input("학습지 이름", value=sh_val["name"], key=f"sh_n_{idx}_{sh_idx}")
                            sh_val["related_page"] = shc2.number_input("연관 교과서 페이지", min_value=1, value=int(sh_val["related_page"]), key=f"sh_p_{idx}_{sh_idx}")
                            if len(sheets) > 1 and shc3.button("🗑️", key=f"del_sh_{idx}_{sh_idx}"):
                                sheets.pop(sh_idx)
                                st.rerun()
                        if st.button("➕ 학습지 추가", key=f"add_sh_{idx}"):
                            sheets.append({"name": f"학습지 {len(sheets)+1}", "related_page": 5})
                            st.rerun()
                        sub["sheets"] = sheets

                    if len(st.session_state.exam_subjects) > 1 and st.button(f"🗑️ 과목 {idx+1} 삭제", key=f"del_sub_{idx}"):
                        remove_subject(idx)
                        st.rerun()

            st.divider()

            if st.button("🚀 순행적 & 학습지 유동 스케줄 생성", type="primary", use_container_width=True):
                valid_subjects = [s for s in st.session_state.exam_subjects if s.get("name", "").strip() != ""]
                
                if not valid_subjects:
                    st.error("최소 한 개 이상의 과목명을 입력해주세요.")
                else:
                    new_schedules = []

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

                        if day_num > 1:
                            prev_exam_date = exam_start_date + timedelta(days=day_idx - 1)
                            for s in day_subs:
                                new_schedules.append({
                                    "id": len(new_schedules) + len(day_subs) + 1,
                                    "날짜": prev_exam_date,
                                    "종류": "🔥 총정리",
                                    "제목": f"[{s.get('name')}] 총정리 공부",
                                    "목표 범위": "전체 범위 핵심 복습",
                                    "목표량": "오후/저녁 집중 총정리",
                                    "완료여부": False,
                                    "메모": f"{day_num-1}일차 시험 종료 후 {day_num}일차 과목 총정리"
                                })

                    day1_subs = [s for s in valid_subjects if s.get("day") == 1]
                    for s in day1_subs:
                        new_schedules.append({
                            "id": len(new_schedules) + 1,
                            "날짜": exam_start_date - timedelta(days=1),
                            "종류": "🔥 총정리",
                            "제목": f"[{s.get('name')}] 총정리 공부",
                            "목표 범위": "전체 범위 핵심 복습",
                            "목표량": "1일차 시험 전날 총정리",
                            "완료여부": False,
                            "메모": "1일차 시험 전날 집중 총정리"
                        })

                    max_daily_pages = max(1, int(st.session_state.study_style.get("max_pages_per_day", 10)))
                    chunk_queue = []
                    
                    for r in range(1, int(exam_repeat)):
                        for s in valid_subjects:
                            s_name = s.get("name")
                            tb_pages = []
                            for tr in s.get("tb_ranges", []):
                                tb_pages.extend(list(range(tr["start"], tr["end"] + 1)))

                            sheet_map = {}
                            if s.get("has_sheets"):
                                for sh in s.get("sheets", []):
                                    sheet_map.setdefault(sh["related_page"], []).append(sh["name"])

                            p_idx = 0
                            while p_idx < len(tb_pages):
                                cur_p = tb_pages[p_idx]
                                sheets_today = sheet_map.get(cur_p, [])
                                actual_max_p = max(1, max_daily_pages - (len(sheets_today) * 2)) if sheets_today else max_daily_pages
                                end_p_idx = min(len(tb_pages) - 1, p_idx + actual_max_p - 1)
                                page_range_str = f"p.{tb_pages[p_idx]}~{tb_pages[end_p_idx]}"
                                
                                if sheets_today:
                                    page_range_str += f" + 학습지({', '.join(sheets_today)})"

                                chunk_queue.append({
                                    "name": s_name,
                                    "range": page_range_str,
                                    "pages": (end_p_idx - p_idx + 1) + (len(sheets_today) * 2),
                                    "repeat": r
                                })
                                p_idx = end_p_idx + 1

                    total_days_needed = len(chunk_queue)
                    start_study_date = exam_start_date - timedelta(days=total_days_needed + 2)
                    
                    for idx, chunk in enumerate(chunk_queue):
                        curr_date = start_study_date + timedelta(days=idx)
                        new_schedules.append({
                            "id": len(new_schedules) + 1,
                            "날짜": curr_date,
                            "종류": f"📖 {chunk['repeat']}회독 학습",
                            "제목": f"[{chunk['name']}] 순행적 단원 공부",
                            "목표 범위": chunk["range"],
                            "목표량": f"{chunk['pages']}p 분량 (학습지 반영)",
                            "완료여부": False,
                            "메모": f"{chunk['repeat']}회독 순행 학습"
                        })

                    new_df = pd.DataFrame(new_schedules)
                    st.session_state.schedule = pd.concat([st.session_state.schedule, new_df], ignore_index=True)
                    st.success("스케줄 생성이 완료되었습니다!")
                    st.rerun()

        # ----------------------------------
        # 2. 수행평가 (새로 추가)
        # ----------------------------------
        elif schedule_type == "수행평가":
            st.markdown("#### 📝 수행평가 등록 및 D-Day 스케줄 생성")
            
            with st.form("add_perf_eval_form"):
                eval_title = st.text_input("수행평가명", placeholder="예: 국어 발표 수행평가, 과학 실험 보고서")
                
                c_sub, c_period = st.columns(2)
                eval_subject = c_sub.text_input("과목명", placeholder="예: 국어, 통합과학")
                eval_period = c_period.number_input("평가 교시", min_value=1, max_value=8, value=3)
                
                c_date, c_prep = st.columns(2)
                eval_date = c_date.date_input("수행평가 날짜 (D-Day)", value=date.today() + timedelta(days=7))
                prep_days = c_prep.number_input("준비 기간 (일)", min_value=1, max_value=30, value=3, help="D-Day 몇 일 전부터 준비 일정을 등록할지 선택합니다.")
                
                eval_range_text = st.text_area("상세 범위 및 준비 내용", placeholder="예: 교과서 45~60p 읽기, 피피티 자료조사 및 스크립트 작성")
                
                if st.form_submit_button("🚀 수행평가 D-Day 스케줄 등록", use_container_width=True):
                    if not eval_title.strip() or not eval_subject.strip():
                        st.error("수행평가명과 과목명을 모두 입력해주세요.")
                    else:
                        new_perf_schedules = []
                        
                        # 1) D-Day 수행평가 본 일정 추가
                        new_perf_schedules.append({
                            "id": len(st.session_state.schedule) + 1,
                            "날짜": eval_date,
                            "종류": "⭐ 수행평가",
                            "제목": f"[{eval_subject}] {eval_title}",
                            "목표 범위": f"{eval_period}교시 진행",
                            "목표량": "수행평가 응시/제출",
                            "완료여부": False,
                            "메모": f"평가 범위: {eval_range_text}"
                        })
                        
                        # 2) D-준비일 ~ D-1 준비 일정 생성
                        for d_offset in range(prep_days, 0, -1):
                            prep_date = eval_date - timedelta(days=d_offset)
                            new_perf_schedules.append({
                                "id": len(st.session_state.schedule) + len(new_perf_schedules) + 1,
                                "날짜": prep_date,
                                "종류": "📖 수행준비",
                                "제목": f"[{eval_subject}] {eval_title} 준비 (D-{d_offset})",
                                "목표 범위": f"D-{d_offset} 준비 및 복습",
                                "목표량": "준비 분량 작성",
                                "완료여부": False,
                                "메모": f"준비 내용: {eval_range_text}"
                            })
                            
                        new_perf_df = pd.DataFrame(new_perf_schedules)
                        st.session_state.schedule = pd.concat([st.session_state.schedule, new_perf_df], ignore_index=True)
                        st.success(f"{eval_title} 수행평가 및 D-{prep_days}부터의 준비 스케줄이 등록되었습니다!")
                        st.rerun()

        # ----------------------------------
        # 3. 기타
        # ----------------------------------
        else:
            st.markdown("#### 📝 기타 학습 일정 등록")
            with st.form("add_other_study_form"):
                o_title = st.text_input("학습 제목", placeholder="예: 수능 특강 영어 독해 1강")
                o_date = st.date_input("학습 날짜", value=st.session_state.selected_date)
                o_range = st.text_input("목표 범위", placeholder="예: 1~5페이지")
                o_amount = st.text_input("목표량", placeholder="예: 3문제 풀기")
                o_memo = st.text_area("메모")
                
                if st.form_submit_button("➕ 기타 학습 등록", use_container_width=True):
                    new_item = pd.DataFrame([{
                        "id": len(st.session_state.schedule) + 1,
                        "날짜": o_date,
                        "종류": "📖 기타학습",
                        "제목": o_title,
                        "목표 범위": o_range,
                        "목표량": o_amount,
                        "완료여부": False,
                        "메모": o_memo
                    }])
                    st.session_state.schedule = pd.concat([st.session_state.schedule, new_item], ignore_index=True)
                    st.success("학습 일정이 등록되었습니다!")
                    st.rerun()

    # --------------------------------------
    # TAB 3: 학습 방식 & 시간표
    # --------------------------------------
    with tab3:
        st.subheader("⚙️ 학습 방식 & 시간표 설정")
        
        st.markdown("#### 🎯 목표 공부 분량")
        
        try:
            curr_target_h = float(st.session_state.study_style.get("target_hours", 4.0))
        except (ValueError, TypeError):
            curr_target_h = 4.0

        st.session_state.study_style["target_hours"] = st.number_input(
            "하루 목표 순공 시간 (시간)", 
            min_value=1.0, 
            max_value=16.0, 
            value=curr_target_h, 
            step=0.5
        )
        
        try:
            curr_max_p = int(st.session_state.study_style.get("max_pages_per_day", 10))
        except (ValueError, TypeError):
            curr_max_p = 10

        st.session_state.study_style["max_pages_per_day"] = st.number_input(
            "하루 과목당 목표 학습 페이지 수", 
            min_value=1, 
            max_value=100, 
            value=curr_max_p, 
            step=1
        )
        
        st.divider()
        st.markdown("#### 📅 요일별 공부 시작 가능 시간")
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        
        if "weekday_start_time" not in st.session_state.study_style:
            st.session_state.study_style["weekday_start_time"] = {day: time(18, 0) for day in weekdays}

        for w in weekdays:
            st.session_state.study_style["weekday_start_time"][w] = st.time_input(
                f"{w}요일 공부 시작 시간", 
                value=st.session_state.study_style["weekday_start_time"].get(w, time(18, 0)), 
                key=f"w_start_{w}"
            )

        st.divider()
        st.markdown("#### 🏫 월~금 학교 시간표 설정")
        
        if "school" not in st.session_state.study_style:
            st.session_state.study_style["school"] = {
                "go_time": time(8, 20),
                "leave_time": time(16, 30),
                "periods": {p: {"active": True, "start": time(9, 0), "end": time(9, 45)} for p in range(1, 9)}
            }

        col_g, col_l = st.columns(2)
        st.session_state.study_style["school"]["go_time"] = col_g.time_input("등교 시간", value=st.session_state.study_style["school"].get("go_time", time(8, 20)))
        st.session_state.study_style["school"]["leave_time"] = col_l.time_input("하교 시간", value=st.session_state.study_style["school"].get("leave_time", time(16, 30)))

        st.caption("1~8교시 세부 시간 및 교시 존재 여부")
        for p in range(1, 9):
            p_data = st.session_state.study_style["school"]["periods"].get(p, {"active": True, "start": time(9, 0), "end": time(9, 45)})
            p_col1, p_col2, p_col3 = st.columns([1.5, 2, 2])
            p_data["active"] = p_col1.checkbox(f"{p}교시 존재", value=p_data.get("active", True), key=f"p_act_{p}")
            p_data["start"] = p_col2.time_input(f"{p}교시 시작", value=p_data.get("start", time(9, 0)), key=f"p_st_{p}")
            p_data["end"] = p_col3.time_input(f"{p}교시 종료", value=p_data.get("end", time(9, 45)), key=f"p_en_{p}")
            st.session_state.study_style["school"]["periods"][p] = p_data

        if st.button("💾 학습 방식 및 시간표 저장", use_container_width=True):
            st.success("학습 방식 및 시간표 설정이 저장되었습니다!")

    # --------------------------------------
    # TAB 4: 일상 루틴 설정
    # --------------------------------------
    with tab4:
        st.subheader("⏰ 일상 루틴 설정")
        
        if "routine" not in st.session_state or not isinstance(st.session_state.routine, dict):
            st.session_state.routine = {
                "sleep": {"start": time(23, 0), "end": time(7, 0)},
                "meals": [
                    {"name": "아침", "start": time(7, 30), "duration": 30},
                    {"name": "점심", "start": time(12, 30), "duration": 60},
                    {"name": "저녁", "start": time(19, 0), "duration": 60}
                ]
            }

        st.markdown("#### 🌙 취침 & 기상 시간")
        col_s, col_e = st.columns(2)
        
        sleep_data = st.session_state.routine.get("sleep", {"start": time(23, 0), "end": time(7, 0)})
        st.session_state.routine["sleep"]["start"] = col_s.time_input("취침 시작 시간", value=sleep_data.get("start", time(23, 0)))
        st.session_state.routine["sleep"]["end"] = col_e.time_input("기상 시간", value=sleep_data.get("end", time(7, 0)))

        st.divider()
        st.markdown("#### 🍽️ 식사 시간 동적 설정")
        
        if st.button("➕ 식사 항목 추가"):
            st.session_state.routine["meals"].append({"name": f"식사 {len(st.session_state.routine['meals'])+1}", "start": time(12, 0), "duration": 30})
            st.rerun()

        del_idx = None
        meals_list = st.session_state.routine.get("meals", [])
        for m_idx, meal in enumerate(meals_list):
            mc1, mc2, mc3, mc4 = st.columns([2, 2, 2, 1])
            meal["name"] = mc1.text_input(f"식사 이름 #{m_idx+1}", value=meal.get("name", ""), key=f"meal_n_{m_idx}")
            meal["start"] = mc2.time_input(f"시작 시간 #{m_idx+1}", value=meal.get("start", time(12, 0)), key=f"meal_s_{m_idx}")
            meal["duration"] = mc3.number_input(f"소요 시간(분) #{m_idx+1}", min_value=10, max_value=180, value=int(meal.get("duration", 30)), key=f"meal_d_{m_idx}")
            
            if len(meals_list) > 1:
                if mc4.button("🗑️", key=f"del_meal_{m_idx}"):
                    del_idx = m_idx

        if del_idx is not None:
            st.session_state.routine["meals"].pop(del_idx)
            st.rerun()

        st.divider()
        if st.button(TEXTS["ROUTINE"]["SAVE_BTN"], use_container_width=True):
            st.success(TEXTS["ROUTINE"]["SAVE_SUCCESS"])
