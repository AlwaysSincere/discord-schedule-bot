import os
import json
import pytz
import re
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class CalendarManager:
    def __init__(self):
        """Google Calendar 연동 관리자 초기화"""
        self.service = None
        self.calendar_id = os.getenv('CALENDAR_ID')
        self.kst = pytz.timezone('Asia/Seoul')
        self.added_events = set()  # 중복 방지용 세트
        
        # Google 서비스 계정 인증
        self.authenticate()
    
    def authenticate(self):
        """Google Calendar API 인증"""
        try:
            # 환경변수에서 서비스 계정 정보 가져오기
            credentials_json = os.getenv('GOOGLE_CREDENTIALS')
            if not credentials_json:
                raise ValueError("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
            
            # JSON 파싱
            credentials_info = json.loads(credentials_json)
            
            # 서비스 계정 인증 정보 생성
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            # Calendar API 서비스 빌드
            self.service = build('calendar', 'v3', credentials=credentials)
            
            print("✅ Google Calendar API 인증 완료")
            
        except json.JSONDecodeError as e:
            print(f"❌ Google 인증 정보 JSON 파싱 오류: {e}")
            raise
        except Exception as e:
            print(f"❌ Google Calendar 인증 실패: {e}")
            raise
    
    def extract_time_from_text(self, when_text):
        """텍스트에서 시간 정보 추출 (간소화된 버전)"""
        when_text = when_text.lower().strip()
        
        # 시간 패턴들
        time_patterns = [
            (r'(\d{1,2})시\s*(\d{1,2})분', 'hour_minute'),    # "2시 20분"
            (r'(\d{1,2})시', 'hour_only'),                    # "8시"
            (r'(\d{1,2}):(\d{2})', 'colon_format'),           # "14:30"
            (r'오전\s*(\d{1,2})시?', 'morning'),              # "오전 9시"
            (r'오후\s*(\d{1,2})시?', 'afternoon'),            # "오후 3시"
        ]
        
        for pattern, pattern_type in time_patterns:
            match = re.search(pattern, when_text)
            if match:
                if pattern_type == 'hour_minute':
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                elif pattern_type == 'colon_format':
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                elif pattern_type == 'morning':
                    hour = int(match.group(1))
                    minute = 0
                elif pattern_type == 'afternoon':
                    hour = int(match.group(1)) + 12
                    minute = 0
                else:  # hour_only
                    hour = int(match.group(1))
                    minute = 0
                    
                    # 🚨 중요: 시간 추론 개선
                    if hour >= 1 and hour <= 12:
                        # 1-12시인 경우 맥락으로 판단
                        if any(word in when_text for word in ['오전', 'am']):
                            pass  # 오전 그대로
                        elif any(word in when_text for word in ['오후', 'pm', '밤', '저녁']):
                            if hour != 12:
                                hour += 12
                        elif hour >= 6 and hour <= 12:
                            # 6-12시는 보통 오후 (합주/리허설 시간대)
                            if hour != 12:
                                hour += 12
                        # 1-5시는 오전으로 유지 (새벽/아침)
                
                return hour, minute
        
        return None, None
    
    def parse_schedule_time(self, schedule):
        """일정 시간 정보를 파싱하여 datetime 객체 생성 (완전 재작성)"""
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
        
        # 🚨 핵심 수정: 매우 간단한 날짜 로직
        target_date = None
        
        # 1순위: 구체적 날짜 (예: 8월 8일)
        date_match = re.search(r'(\d{1,2})월\s*(\d{1,2})일', when_text)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            try:
                target_date = datetime(base_time.year, month, day).date()
                print(f"      ✅ 구체적 날짜: {target_date}")
            except ValueError:
                pass
        
        # 2순위: 상대적 날짜 (절대적으로 간단하게)
        if not target_date:
            if '오늘' in when_text:
                target_date = base_time.date()  # 작성일 그대로
                print(f"      ✅ 오늘 = {target_date}")
                
            elif '내일' in when_text:
                target_date = base_time.date() + timedelta(days=1)  # 작성일 + 1
                print(f"      ✅ 내일 = {target_date}")
                
            elif '모레' in when_text:
                target_date = base_time.date() + timedelta(days=2)  # 작성일 + 2
                print(f"      ✅ 모레 = {target_date}")
                
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
                    current_weekday = base_time.weekday()
                    days_ahead = found_weekday - current_weekday
                    if days_ahead <= 0:
                        days_ahead += 7
                    target_date = base_time.date() + timedelta(days=days_ahead)
                    print(f"      ✅ 요일 계산 = {target_date}")
                else:
                    # 기본값: 내일
                    target_date = base_time.date() + timedelta(days=1)
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
    
    def create_event_hash(self, schedule):
        """중복 체크를 위한 일정 해시 생성"""
        content = schedule.get('content', '')[:100]
        author = schedule.get('author', '')
        created_at = schedule.get('created_at', '')
        hash_str = f"{content}_{author}_{created_at}"
        return hash(hash_str)
    
    def create_event_from_schedule(self, schedule):
        """일정 정보를 바탕으로 Google Calendar 이벤트 생성"""
        try:
            # 중복 체크
            event_hash = self.create_event_hash(schedule)
            if event_hash in self.added_events:
                print(f"  ⚠️ 중복 건너뛰기: {schedule.get('content', '')[:50]}...")
                return None
            
            # 시간 파싱
            start_time, end_time = self.parse_schedule_time(schedule)
            
            if not start_time:
                print(f"  ⚠️ 시간 파싱 실패: {schedule.get('content', '')[:50]}...")
                return None
            
            # 이벤트 제목 생성
            schedule_type = schedule.get('schedule_type', '일정')
            what = schedule.get('extracted_info', {}).get('what', '')
            
            if what:
                title = f"[{schedule_type}] {what}"
            else:
                title = f"[{schedule_type}] Discord 일정"
            
            # 이벤트 설명 생성
            when_info = schedule.get('extracted_info', {}).get('when', '미상')
            where_info = schedule.get('extracted_info', {}).get('where', '미상')
            confidence = schedule.get('confidence', 0)
            
            description = f"""Discord에서 자동 추출된 일정

📝 원본 메시지: "{schedule.get('content', '')}"
👤 작성자: {schedule.get('author', 'Unknown')}
📍 채널: {schedule.get('channel', 'Unknown')}
🕐 작성 시간: {schedule.get('created_at', 'Unknown')}
🎯 확신도: {confidence:.1%}

📊 추출된 정보:
• 언제: {when_info}
• 무엇: {what}
• 어디서: {where_info}

💭 분류 이유: {schedule.get('reason', '없음')}

🤖 자동 생성된 일정입니다. 정확성을 확인해주세요.
"""
            
            # Google Calendar 이벤트 객체 생성
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'source': {
                    'title': 'Discord Schedule Bot',
                    'url': 'https://github.com/AlwaysSincere/discord-schedule-bot'
                },
                'colorId': '9',  # 파란색 (Discord 색상)
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            self.added_events.add(event_hash)
            return event
            
        except Exception as e:
            print(f"  ❌ 이벤트 생성 오류: {e}")
            return None
    
    def add_schedules_to_calendar(self, schedules):
        """추출된 일정들을 Google Calendar에 추가"""
        if not self.service:
            print("❌ Google Calendar 서비스가 초기화되지 않았습니다.")
            return
        
        if not schedules:
            print("📝 추가할 일정이 없습니다.")
            return
        
        print(f"📅 {len(schedules)}개 일정을 Google Calendar에 추가합니다...")
        print("=" * 70)
        
        added_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, schedule in enumerate(schedules):
            print(f"\n📝 일정 {i+1}/{len(schedules)}: {schedule.get('content', '')[:50]}...")
            print(f"   👤 작성자: {schedule.get('author', 'Unknown')}")
            print(f"   🎯 AI 추출: {schedule.get('extracted_info', {}).get('when', '미상')}")
            
            try:
                event = self.create_event_from_schedule(schedule)
                if not event:
                    if self.create_event_hash(schedule) in self.added_events:
                        skipped_count += 1
                        print(f"      ⏭️ 중복으로 건너뛰기")
                    else:
                        failed_count += 1
                        print(f"      ❌ 이벤트 생성 실패")
                    continue
                
                # Google Calendar에 이벤트 추가
                created_event = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event
                ).execute()
                
                # 결과 출력
                start_time_str = created_event['start'].get('dateTime', created_event['start'].get('date'))
                print(f"      ✅ 캘린더 추가 완료!")
                print(f"      📅 제목: {event['summary']}")
                print(f"      🕐 시간: {start_time_str}")
                
                added_count += 1
                
            except HttpError as http_error:
                print(f"      ❌ Google API 오류: {http_error}")
                failed_count += 1
                
            except Exception as e:
                print(f"      ❌ 예상치 못한 오류: {e}")
                failed_count += 1
        
        # 최종 결과
        print(f"\n" + "=" * 70)
        print(f"📊 캘린더 추가 완료!")
        print(f"   ✅ 성공: {added_count}개")
        print(f"   ⏭️ 중복 건너뛰기: {skipped_count}개")
        print(f"   ❌ 실패: {failed_count}개")
        print(f"   📊 총 처리: {len(schedules)}개")
        
        if len(schedules) > 0:
            success_rate = (added_count / len(schedules)) * 100
            print(f"   🎯 성공률: {success_rate:.1f}%")
        
        if added_count > 0:
            print(f"   📅 Google Calendar에서 확인하세요")

async def add_schedules_to_google_calendar(schedules):
    """일정들을 Google Calendar에 추가하는 메인 함수"""
    print("📅 Google Calendar 연동을 시작합니다...")
    
    try:
        calendar_manager = CalendarManager()
        calendar_manager.add_schedules_to_calendar(schedules)
        return True
    except Exception as e:
        print(f"❌ Google Calendar 연동 실패: {e}")
        return False
