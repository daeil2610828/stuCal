# --------------------------------------
    # TAB 1: 개인 일정 추가
    # --------------------------------------
    with tab1:
        st.subheader(TEXTS["ADD_PERSONAL"]["HEADER"])
        with st.form("add_personal_form"):
            p_title = st.text_input("일정 이름", placeholder="예: 병원 방문, 미팅, 운동")
            
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
