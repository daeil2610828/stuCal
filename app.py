import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import math
import calendar
import gspread
from google.oauth2.service_account import Credentials

# 페이지 기본 설정
st.set_page_config(page_title="스마트 시험 D-Day 플래너", layout="wide")

st.title("📅 스마트 시험 D-Day & 공부 스케줄러")
st.caption("시험 날짜와 공부 범위를 설정하고, 달성도에 따라 스케줄을 자동으로 재조정하세요. (Google Sheets 연동)")

# --- Google Sheets 클라우드 연결 (gspread 활용) ---
@st.cache_resource
def get_gsheet_client():
    """Streamlit secrets에서 인증 정보를 가져와 gspread 클라이언트를 생성합니다."""
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
    """구글 시트에서 최신 스케줄 데이터를 불러옵니다."""
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
    """스케줄 데이터를 구글 시트로 업데이트합니다."""
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

# --- 메인 레이아웃 (좌: 커스텀 달력 / 우: 탭뷰) ---
left_col, right_col = st.columns([1, 1], gap="large")

# ==========================================
# [왼쪽 칼럼] 커스텀 달력 및 날짜 이동 컨트롤
# ==========================================
with left_col:
    st.subheader("🗓️ 달력")
    
    # 상단 컨트롤: 이전 달 / 통합 날짜 선택기 (키보드 직접 입력 가능) / 다음 달
    nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])
    
    selected_dt = st.session_state.selected_date
    
    with nav_col1:
        if st.button("◀", key="prev_month_btn", use_container_width=True):
            # 이전 달의 1일로 이동
            first_curr = selected_dt.replace(day=1)
            prev_month_last = first_curr - timedelta(days=1)
            st.session_state.selected_date = prev_month_last.replace(day=min(selected_dt.day, prev_month_last.day))
            st.rerun()
            
    with nav_col2:
        # 통합된 날짜 입력기 (키보드 입력 가능, 달력 아이콘 및 선택 지원)
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
        if st.button("▶", key="next_month_btn", use_container_width=True):
            # 다음 달로 이동
            next_month = (selected_dt.replace(day=28) + timedelta(days=5)).replace(day=1)
            st.session_state.selected_date = next_month.replace(day=min(selected_dt.day, 28))
            st.rerun()

    # --- 커스텀 grid 캘린더 생성 ---
    year = selected_dt.year
    month = selected_dt.month
    
    # 스케줄 데이터를 날짜별 매핑
    schedule_dict = {}
    if st.session_state.schedule is not None and not st.session_state.schedule.empty:
        for _, row in st.session_state.schedule.iterrows():
            schedule_dict[row["날짜"]] = row

    # 요일 헤더
    days_header = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    hdr_cols = st.columns(7)
    for idx, day_name in enumerate(days_header):
        hdr_cols[idx].markdown(f"**<div style='text-align: center;'>{day_name}</div>**", unsafe_allow_html=True)

    # 해당 월의 달력 그리드 계산 (일요일 시작)
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)

    for week in month_days:
        week_cols = st.columns(7)
        for idx, day_date in enumerate(week):
            is_current_month = (day_date.month == month)
            is_selected = (day_date == selected_dt)
            
            # 날짜에 해당하는 공부 데이터 확인
            data = schedule_dict.get(day_date, None)
            
            # 텍스트 및 레이블 구성
            day_num_str = str(day_date.day)
            label = day_num_str
            
            if is_current_month and data is not None:
                is_done = data.get("완료여부", False)
                icon = "✅" if is_done else "📖"
                label = f"{day_num_str}\n{icon} {data['목표 범위']}"

            # 버튼 타입 (선택된 날짜인 경우 primary 강조)
            btn_type = "primary" if is_selected else "secondary"
            
            # 이전/다음 달 날짜 연하게 표시 처리용 키
            btn_key = f"cal_btn_{day_date.strftime('%Y_%m_%d')}"
            
            with week_cols[idx]:
                # 날짜 버튼 클릭 시 해당 날짜로 선택되며 상단 입력창에도 즉시 연동
                if st.button(
                    label,
                    key=btn_key,
                    use_container_width=True,
                    type=btn_type,
                    disabled=not is_current_month # 다른 달 날짜 비활성화 (필요 시 활성화 가능)
                ):
                    st.session_state.selected_date = day_date
                    st.rerun()

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
            calculated_total = int(df["목표량"].sum())

            total_completed = int(df["실제 완료량"].sum())
            remaining_amount = max(0, calculated_total - total_completed)
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
            st.info("오른쪽 탭 영역에 설정 메뉴가 구성되면 스케줄을 추가해 주세요.")

    # --------------------------------------
    # TAB 2: 임시 영역
    # --------------------------------------
    with tab2:
        st.subheader("📌 2번 영역")
        st.write("사이드바에 있던 설정을 이곳으로 옮기거나 추가 기능을 구성할 수 있습니다.")

    # --------------------------------------
    # TAB 3: 임시 영역
    # --------------------------------------
    with tab3:
        st.subheader("📌 3번 영역")
        st.write("여기에 추후 필요한 기능을 구현할 수 있습니다.")
