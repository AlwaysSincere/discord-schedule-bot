def parse_schedule_time(self, schedule):
    """일정 시간 정보를 파싱하여 datetime 객체 생성 (완전 수정 버전)"""
    when_text = schedule.get('extracted_info', {}).get('when', '').lower().strip()
    created_at = schedule.get('created_at')
    
    # 작성 시간 정규화
    if isinstance(created_at, str):
        base_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        base_time = base_time.astimezone(self.kst)
    else:
        base_time = created_at.astimezone(self.kst) if created_at else datetime.now(self.kst)
    
    print(f"      📝 원본: '{when_text}'")
    print(f"      🕐 작성: {base_time.strftime('%Y-%m-%d %H:%M')}")
    
    # 🚨 핵심 수정: 절대적으로 간단한 날짜 로직
    target_date = None
    
    # 1순위: 구체적 날짜 (예: 8월 8일) - 가장 명확함
    date_match = re.search(r'(\d{1,2})월\s*(\d{1,2})일', when_text)
    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        try:
            target_date = datetime(base_time.year, month, day).date()
            print(f"      ✅ 구체적 날짜: {target_date}")
        except ValueError:
            pass
    
    # 2순위: 상대적 날짜 (💡 핵심: 작성일 기준으로 절대 계산)
    if not target_date:
        # 작성일 기준으로 정확히 계산
        creation_date = base_time.date()
        
        if '오늘' in when_text:
            target_date = creation_date  # 🚨 작성일 그 자체
            print(f"      ✅ 오늘 = {target_date} (작성일 기준)")
            
        elif '내일' in when_text:
            target_date = creation_date + timedelta(days=1)  # 🚨 작성일 + 1일
            print(f"      ✅ 내일 = {target_date} (작성일+1)")
            
        elif '모레' in when_text:
            target_date = creation_date + timedelta(days=2)  # 🚨 작성일 + 2일
            print(f"      ✅ 모레 = {target_date} (작성일+2)")
            
        elif '낼모래' in when_text:
            target_date = creation_date + timedelta(days=2)  # 🚨 모레와 같음
            print(f"      ✅ 낼모래 = {target_date} (작성일+2)")
            
        elif '다음주' in when_text or '담주' in when_text:
            # 다음주 월요일로 계산
            days_until_next_monday = (7 - creation_date.weekday()) % 7
            if days_until_next_monday == 0:  # 월요일에 "다음주"라고 하면
                days_until_next_monday = 7   # 다다음주 월요일
            target_date = creation_date + timedelta(days=days_until_next_monday)
            print(f"      ✅ 다음주 = {target_date} (다음주 월요일)")
            
        else:
            # 요일 체크
            weekdays = {
                '월요': 0, '월욜': 0, '월요일': 0,
                '화요': 1, '화욜': 1, '화요일': 1,
                '수요': 2, '수욜': 2, '수요일': 2,
                '목요': 3, '목욜': 3, '목요일': 3,
                '금요': 4, '금욜': 4, '금요일': 4,
                '토요': 5, '토욜': 5, '토요일': 5,
                '일요': 6, '일욜': 6, '일요일': 6,
            }
            
            found_weekday = None
            for day_name, day_num in weekdays.items():
                if day_name in when_text:
                    found_weekday = day_num
                    break
            
            if found_weekday is not None:
                current_weekday = creation_date.weekday()
                days_ahead = found_weekday - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7  # 다음 주 해당 요일
                target_date = creation_date + timedelta(days=days_ahead)
                print(f"      ✅ 요일 계산 = {target_date}")
            else:
                # 기본값: 내일
                target_date = creation_date + timedelta(days=1)
                print(f"      ✅ 기본값(내일) = {target_date}")
    
    # 시간 추출
    extracted_hour, extracted_minute = self.extract_time_from_text(when_text)
    
    if extracted_hour is not None:
        final_hour = extracted_hour
        final_minute = extracted_minute
        print(f"      ✅ 시간 추출: {final_hour:02d}:{final_minute:02d}")
    else:
        final_hour = 18  # 기본값: 오후 6시
        final_minute = 0
        print(f"      ✅ 기본 시간: {final_hour:02d}:{final_minute:02d}")
    
    # 최종 datetime 생성
    try:
        start_time = datetime.combine(target_date, datetime.min.time().replace(
            hour=final_hour, minute=final_minute
        ))
        start_time = self.kst.localize(start_time)
        end_time = start_time + timedelta(hours=1)
        
        print(f"      🎯 최종: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%H:%M')}")
        return start_time, end_time
        
    except ValueError as e:
        print(f"      ❌ 오류: {e}")
        return None, None
