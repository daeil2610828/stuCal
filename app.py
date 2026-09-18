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
accent_color = st.sidebar.selectbox(
    "액센트 테마 컬러",
    ["클래식 블루 (#1a73e8)", "에메랄드 그린 (#28a745)", "로열 퍼플 (#6f42c1)", "웜 오렌지 (#fd7e14)"],
    index=0
)
color_map = {
    "클래식 블루 (#1a73e8)": "#1a73e8",
    "에메랄드 그린 (#28a745)": "#28a745",
    "로열 퍼플 (#6f42c1)": "#6f42c1",
    "웜 오렌지 (#fd7e14)": "#fd7e14"
}
selected_accent = color_map[accent_color]

theme_mode = st.sidebar.radio("모드 설정", ["라이트 모드", "다크 모드"], index=0)

# --- 엑셀 스타일 CSS 및 전용 달력 클래스 고유 적용 ---
st.markdown(f"""
    <style>
        /* 엑셀 느낌의 달력 전용 버튼 스타일 */
        .excel-cal-cell > button {{
            min-height: 90px !important;
            height: 90px !important;
            width: 100% !important;
            border: 1px solid #dadce0 !important;
            border-radius: 0px !important; /* 엑셀 사각 셀 느낌 */
            background-color: #ffffff !important;
            color: #3c4043 !important;
            padding: 4px 6px !important;
            margin: 0px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            align-items: flex-start !important;
            text-align: left !important;
            font-size: 13px !important;
            box-sizing: border-box !important;
        }}
        
        .excel-cal-cell > button:hover {{
            background-color: #f1f3f4 !important;
            border-color: #bdc1c6 !important;
        }}

        /* 선택된 엑셀 셀 (연파랑 하이라이트) */
        .excel-cal-cell-selected > button {{
            background-color: #e8f0fe !important;
            border: 2px solid {selected_accent} !important;
            color: {selected_accent} !important;
            font-weight: bold !important;
        }}

        /* 다른 달 날짜 엑셀 셀 */
        .excel-cal-cell-other > button {{
            background-color: #f8f9fa !important;
            color: #c0c4cc !important;
            border: 1px solid #f1f3f4 !important;
        }}
        
        /* 엑셀 날짜 숫자 (좌상단 정렬) */
        .day-num {{
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 4px;
            text-align: left;
            width: 100%;
        }}
        
        /* 엑셀 셀 내용 */
        .cell-content {{
            font-size: 11px;
            line-height: 1.2;
            word-break: break-all;
            text-align: left;
            width: 100%;
        }}
    </style>
""", unsafe_allow_html=True)

st.title("📅 스마트 시험 D-Day & 공부 스케줄러")
st.caption("시험 날짜와 공부 범위를 설정하고, 달성도에 따라 스케줄을 자동으로 재조정하세요.")

# --- 메인 레이아웃 (좌: 엑셀 커스텀 달력 / 우: 탭뷰) ---
left_col, right_col = st.columns([1.1, 0.9], gap="large")

# ==========================================
# [왼쪽 칼럼] 엑셀형 커스텀 달력
# ==========================================
with left_col:
    st.subheader("🗓️ 달력")
    
    # 상단 컨트롤: 작고 정돈된 이전/다음 달 버튼 및 통합 날짜 선택기
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

    # --- 엑셀 스타일 grid 캘린더 생성 ---
    year = selected_dt.year
    month = selected_dt.month
    
    schedule_dict = {}
    if st.session_state.schedule is not None and not st.session_state.schedule.empty:
        for _, row in st.session_state.schedule.iterrows():
            schedule_dict[row["날짜"]] = row

    # 요일 헤더 (엑셀 시트 헤더 느낌)
    days_header = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    hdr_cols = st.columns(7)
    for idx, day_name in enumerate(days_header):
        hdr_cols[idx].markdown(
            f"<div style='text-align: center; font-weight: bold; background-color: #f1f3f4; "
            f"border: 1px solid #dadce0; padding: 4px 0px; font-size: 12px; color: #5f6368;'>{day_name}</div>",
            unsafe_allow_html=True
        )

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)

    for week in month_days:
        week_cols = st.columns(7)
        for idx, day_date in enumerate(week):
            is_current_month = (day_date.month == month)
            is_selected = (day_date == selected_dt)
            
            data = schedule_dict.get(day_date, None)
            
            # 셀 라벨 (좌상단 숫자 + 하단 내용)
            day_num = str(day_date.day)
            content_str = ""
            
            if is_current_month and data is not None:
                is_done = data.get("완료여부", False)
                icon = "✅" if is_done else "📖"
                content_str = f"\n{icon} {data['목표 범위']}"
            
            display_label = f"{day_num}{content_str}"
            btn_key = f"excel_cell_{day_date.strftime('%Y_%m_%d')}"
            
            # 셀 CSS 클래스 분기
            cell_class = "excel-cal-cell"
            if is_selected and is_current_month:
                cell_class = "excel-cal-cell excel-cal-cell-selected"
            elif not is_current_month:
                cell_class = "excel-cal-cell excel-cal-cell-other"
                
            with week_cols[idx]:
                st.markdown(f'<div class="{cell_class}">', unsafe_allow_html=True)
                if st.button(
                    display_label,
                    key=btn_key,
                    use_container_width=True,
                    disabled=not is_current_month
                ):
                    st.session_state.selected_date = day_date
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

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
        st.write("사이드바에 있던 시험 설정 메뉴나 분석 그래프 등을 이곳에 배치할 수 있습니다.")

    # --------------------------------------
    # TAB 3: 임시 영역
    # --------------------------------------
    with tab3:
        st.subheader("📌 3번 영역")
        st.write("여기에 추후 필요한 기능을 구현할 수 있습니다.")
