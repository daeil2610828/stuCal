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
