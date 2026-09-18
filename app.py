import streamlit as st
import pandas as pd
from datetime import date, timedelta
import math

# 페이지 설정
st.set_page_config(page_title="스마트 시험 D-Day 플래너", layout="wide")

st.title("📅 스마트 시험 D-Day & 공부 스케줄러")
st.caption("시험 날짜와 공부 범위를 설정하고, 달성도에 따라 스케줄을 자동으로 재조정하세요.")

# 세션 상태 초기화
if "schedule" not in st.session_state:
    st.session_state.schedule = None

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
        st.session_state.schedule = generate_initial_schedule(start_date, target_date, total_amount)
        st.sidebar.success("새 스케줄이 생성되었습니다!")

# --- 메인 화면 ---
if st.session_state.schedule is not None:
    df = st.session_state.schedule
    
    # 1. 요약 지표 (KPI)
    total_completed = df["실제 완료량"].sum()
    remaining_amount = max(0, total_amount - total_completed)
    progress_pct = min(100.0, (total_completed / total_amount) * 100)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 목표량", f"{total_amount}")
    col2.metric("현재 완료량", f"{total_completed}")
    col3.metric("남은 공부량", f"{remaining_amount}")
    col4.metric("전체 진행률", f"{progress_pct:.1f}%")
    
    st.progress(progress_pct / 100)
    
    st.divider()

    # 2. 공부 데이터 입력 및 스케줄 조정
    st.subheader("📋 일별 공부 기록 및 자동 스케줄 재조정")
    
    # 데이터 수정이 가능한 Data Editor 제공
    edited_df = st.data_editor(
        df,
        column_config={
            "날짜": st.column_config.DateColumn("날짜", disabled=True),
            "목표 범위": st.column_config.TextColumn("목표 범위", disabled=True),
            "목표량": st.column_config.NumberColumn("목표량", disabled=True),
            "실제 완료량": st.column_config.NumberColumn("실제 완료한 분량", min_value=0, max_value=total_amount),
            "완료여부": st.column_config.CheckboxColumn("완료 체크")
        },
        disabled=["날짜", "목표 범위", "목표량"],
        hide_index=True,
        use_container_width=True
    )
    
    # 동적 스케줄 재조정 버튼
    if st.button("🔄 남은 일정 다이나믹 재조정"):
        today = date.today()
        # 오늘 이후면서 아직 완료되지 않은 날짜 계산
        future_mask = (edited_df["날짜"] >= today) & (~edited_df["완료여부"])
        future_days_count = future_mask.sum()
        
        current_completed = edited_df["실제 완료량"].sum()
        new_remaining = total_amount - current_completed
        
        if new_remaining <= 0:
            st.balloons()
            st.success("🎉 이미 모든 공부 목표를 달성했습니다!")
        elif future_days_count <= 0:
            st.warning("⚠️ 남은 공부 기간이 없습니다. 시험 날짜를 변경하거나 기간을 늘려주세요.")
        else:
            # 남은 날짜들에 대해 목표량 균등 재배분
            new_daily_target = math.ceil(new_remaining / future_days_count)
            
            accumulated = current_completed
            for idx in edited_df[future_mask].index:
                p_start = accumulated + 1
                p_end = min(accumulated + new_daily_target, total_amount)
                
                edited_df.loc[idx, "목표 범위"] = f"{p_start} ~ {p_end}" if p_start <= total_amount else "완료"
                edited_df.loc[idx, "목표량"] = max(0, p_end - p_start + 1) if p_start <= total_amount else 0
                accumulated = p_end
                
            st.session_state.schedule = edited_df
            st.success(f"남은 {future_days_count}일 동안 일일 목표량이 {new_daily_target}개로 재조정되었습니다!")
            st.rerun()

else:
    st.info("👈 사이드바에서 시험 정보를 입력하고 '새로운 스케줄 생성' 버튼을 눌러주세요.")