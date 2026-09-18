import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import math
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# 페이지 기본 설정
st.set_page_config(page_title="스마트 시험 D-Day 플래너", layout="wide")

st.title("📅 스마트 시험 D-Day & 공부 스케줄러")
st.caption("시험 날짜와 공부 범위를 설정하고, 달성도에 따라 스케줄을 자동으로 재조정하세요. (Google Sheets 연동)")

# --- 구글 시트 클라우드 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_schedule_from_gsheets():
    """구글 시트에서 최신 스케줄 데이터를 불러옵니다."""
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df.empty:
            return None
        # 날짜 컬럼 타입 변환
        if "날짜" in df.columns:
            df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
        return df
    except Exception:
        return None

def save_schedule_to_gsheets(df):
    """스케줄 데이터를 구글 시트로 업데이트합니다 (로컬 파일 생성 X)."""
    save_df = df.copy()
    if "날짜" in save_df.columns:
        save_df["날짜"] = save_df["날짜"].astype(str)
    conn.update(worksheet="Sheet1", data=save_df)

# 세션 상태 초기화
if "schedule" not in st.session_state:
    st.session_state.schedule = load_schedule_from_gsheets()

if "current_view_date" not in st.session_state:
    st.session_state.current_view_date = date.today().replace(day=1)

# --- 사이드바: 입력 및 설정 ---
st.sidebar.header("⚙️ 시험 및 공부 설정")
exam_name = st.sidebar.text_input("시험 / 과목 이름", "정보처리기사")
start_date = st.sidebar.date_input("공부 시작일", date.today())
target_date = st.sidebar.date_input("시험 날짜", date.today() + timedelta(days=14))
total_amount = st.sidebar.number_input("총 공부 범위 (예: 페이지/강의 수)", min_value=1, value=300, step=10)

def generate_initial_schedule(start, target, total):
    """초기 일별 스케줄 생성 함수"""
    days = (target - start).days
    if days <= 0:
        return None
    
    daily_target = math.ceil(total / days)
    schedule_data = []
    
    current_page = 0
    for i in range(days):
        day_date = start + timedelta(days=i)
        page_start = current_page + 1
        page_end = min(current_page + daily_target, total)
        
        schedule_data.append({
            "날짜": day_date,
            "목표 범위": f"{page_start} ~ {page_end}",
            "목표량": page_end - page_start + 1 if page_start <= total else 0,
            "실제 완료량": 0,
            "완료여부": False
        })
        current_page = page_end
        
    return pd.DataFrame(schedule_data)

if st.sidebar.button("🗓️ 새로운 스케줄 생성"):
    if target_date <= start_date:
        st.sidebar.error("시험 날짜는 시작일 이후여야 합니다!")
    else:
        new_df = generate_initial_schedule(start_date, target_date, total_amount)
        if new_df is not None:
            st.session_state.schedule = new_df
            save_schedule_to_gsheets(new_df)
            st.sidebar.success("새 스케줄이 구글 시트에 저장되었습니다!")
            st.rerun()

# --- 메인 레이아웃 (좌: 달력 / 우: 탭뷰) ---
left_col, right_col = st.columns([1, 1], gap="large")

# ==========================================
# [왼쪽 칼럼] 달력 및 날짜 이동 네비게이션
# ==========================================
with left_col:
    st.subheader("🗓️ 달력")
    
    # 상단 연/월 이동 컨트롤
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 3, 2, 1])
    
    curr_dt = st.session_state.current_view_date
    
    with nav_col1:
        if st.button("◀", key="prev_month"):
            # 이전 달로 이동
            first_of_curr = curr_dt.replace(day=1)
            prev_month_last = first_of_curr - timedelta(days=1)
            st.session_state.current_view_date = prev_month_last.replace(day=1)
            st.rerun()
            
    with nav_col2:
        # 2026-09 ▾ 형태의 버튼 (클릭 시 원하는 연월로 이동)
        formatted_date_str = curr_dt.strftime("%Y-%m ▾")
        st.button(f"📅 {formatted_date_str}", key="date_picker_btn", use_container_width=True)

    with nav_col3:
        # 연월 직접 지정 팝오버/스프레드
        selected_ym = st.date_input(
            "날짜 선택",
            value=curr_dt,
            label_visibility="collapsed",
            key="selector_date"
        )
        if selected_ym.replace(day=1) != curr_dt:
            st.session_state.current_view_date = selected_ym.replace(day=1)
            st.rerun()

    with nav_col4:
        if st.button("▶", key="next_month"):
            # 다음 달로 이동
            next_month = (curr_dt.replace(day=28) + timedelta(days=5)).replace(day=1)
            st.session_state.current_view_date = next_month
            st.rerun()

    # 달력 이벤트 생성 (스케줄 데이터 변환)
    calendar_events = []
    if st.session_state.schedule is not None and not st.session_state.schedule.empty:
        for _, row in st.session_state.schedule.iterrows():
            is_done = row.get("완료여부", False)
            color = "#28a745" if is_done else "#3174ad"
            title = f"{row['목표 범위']} ({row['실제 완료량']}/{row['목표량']})"
            
            calendar_events.append({
                "title": title,
                "start": str(row["날짜"]),
                "end": str(row["날짜"]),
                "color": color,
                "allDay": True
            })

    # Calendar 옵션 및 렌더링
    calendar_options = {
        "headerToolbar": False,  # 상단 커스텀 네비게이션 사용
        "initialDate": curr_dt.strftime("%Y-%m-%d"),
        "initialView": "dayGridMonth",
        "selectable": True,
        "editable": False
    }
    
    calendar(
        events=calendar_events,
        options=calendar_options,
        key=f"calendar_{curr_dt.strftime('%Y_%m')}"
    )

# ==========================================
# [오른쪽 칼럼] 탭뷰 (1, 2, 3)
# ==========================================
with right_col:
    tab1, tab2, tab3 = st.tabs(["1", "2", "3"])
    
    # --------------------------------------
    # TAB 1: 일별 공부 기록 및 스케줄 조정
    # --------------------------------------
    with tab1:
        st.subheader("📋 일별 공부 기록 및 자동 스케줄 재조정")
        
        if st.session_state.schedule is not None and not st.session_state.schedule.empty:
            df = st.session_state.schedule
            calculated_total = int(df["목표량"].sum()) if total_amount is None else total_amount

            # 요약 지표 (KPI)
            total_completed = int(df["실제 완료량"].sum())
            remaining_amount = max(0, calculated_total - total_completed)
            progress_pct = min(100.0, (total_completed / calculated_total) * 100) if calculated_total > 0 else 0
            
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            kpi_col1.metric("총 목표량", f"{calculated_total}")
            kpi_col2.metric("현재 완료량", f"{total_completed}")
            kpi_col3.metric("진행률", f"{progress_pct:.1f}%")
            
            st.progress(progress_pct / 100)
            st.divider()

            # 데이터 에디터
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
                if st.button("💾 구글 시트에 진도 저장", use_container_width=True):
                    st.session_state.schedule = edited_df
                    save_schedule_to_gsheets(edited_df)
                    st.success("구글 시트에 최신 저장 완료!")
                    st.rerun()

            with btn_col2:
                if st.button("🔄 다이나믹 일정 재조정", use_container_width=True):
                    today = date.today()
                    future_mask = (edited_df["날짜"] >= today) & (~edited_df["완료여부"])
                    future_days_count = future_mask.sum()
                    
                    current_completed = int(edited_df["실제 완료량"].sum())
                    new_remaining = calculated_total - current_completed
                    
                    if new_remaining <= 0:
                        st.balloons()
                        st.success("🎉 이미 모든 공부 목표를 달성했습니다!")
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
            st.info("👈 사이드바에서 시험 정보를 입력하고 '새로운 스케줄 생성' 버튼을 눌러주세요.")

    # --------------------------------------
    # TAB 2: 임시 영역
    # --------------------------------------
    with tab2:
        st.subheader("📌 2번 영역")
        st.write("여기에 추후 필요한 기능(예: 통계 차트, 상세 노트 등)을 구현할 수 있습니다.")

    # --------------------------------------
    # TAB 3: 임시 영역
    # --------------------------------------
    with tab3:
        st.subheader("📌 3번 영역")
        st.write("여기에 추후 필요한 기능(예: 설정, 모의고사 기록 등)을 구현할 수 있습니다.")