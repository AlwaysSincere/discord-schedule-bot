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
    
    def extract_time_from_text(self, when_text, created_at):
        """텍스트에서 구체적인 시간 정보 추출 (개선된 버전)"""
        when_text = when_text.lower().strip()
        
        # 시간 패턴 매칭 (더 정확한 정규식 사용)
        time_patterns = [
            r'(\d{1,2})시\s*(\d{1,2})분',  # "2시 20분"
            r'(\d{1,2})시',               # "8시"
            r'(\d{1,2}):(\d{2})',         # "14:30"
            r'오전\s*(\d{1,2})시',        # "오전 9시"
            r'오후\s*(\d{1,2})시',        # "오후 3시"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, when_text)
            if match:
                if '시' in pattern and '분' in pattern:
                    # "2시 20분" 형태
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                elif ':' in pattern:
                    # "14:30" 형태
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                elif '오전' in when_text:
                    # "오전 9시" 형태
                    hour = int(match.group(1))
                    minute = 0
                elif '오후' in when_text:
                    # "오후 3시" 형태
                    hour = int(match.group(1)) + 12
                    minute = 0
                else:
                    # "8시" 형태 (오후로 가정, 단 새벽 시간대는 그대로)
                    hour = int(match.group(1))
                    minute = 0
                    if hour <= 6:  # 새벽 6시 이전은 그대로
                        pass
                    elif hour <= 12:  # 7시~12시는 오후로 가정
                        hour += 12
                
                return hour, minute
        
        return None, None
    
    def parse_schedule_time(self, schedule):
        """일정 시간 정보를 파싱하여 datetime 객체 생성 (날짜 파싱 개선된 버전)"""
        when_text = schedule.get('extracted_info', {}).get('when', '').lower()
        created_at = schedule.get('created_at')
        
        # 기본값: 메시지 작성 시간 기준
        if isinstance(created_at, str):
            base_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            base_time = base_time.astimezone(self.kst)
        else:
            base_time = created_at.astimezone(self.kst) if created_at else datetime.now(self.kst)
        
        # 구체적인 시간 추출 시도
        extracted_hour, extracted_minute = self.extract_time_from_text(when_text, created_at)
        
        # 날짜 결정 (우선순위 기반으로 개선)
        target_date = None
        default_hour = 6  # 시간이 불명확할 때 오전 6시
        default_minute = 0
        
        # 우선순위 1: 구체적인 요일 (월화수목금토일)
        weekday_patterns = {
            '월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3, 
            '금요일': 4, '토요일': 5, '일요일': 6,
            '월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6
        }
        
        found_weekday = None
        for day_name, day_num in weekday_patterns.items():
            if day_name in when_text:
                found_weekday = day_num
                break
        
        if found_weekday is not None:
            # 이번 주 또는 다음 주의 해당 요일 찾기
            current_weekday = base_time.weekday()  # 월요일=0, 일요일=6
            days_ahead = found_weekday - current_weekday
            
            if days_ahead <= 0:  # 이번 주 해당 요일이 지났거나 오늘
                days_ahead += 7  # 다음 주 해당 요일
            
            target_date = (base_time + timedelta(days=days_ahead)).date()
            print(f"      📅 날짜: {list(weekday_patterns.keys())[found_weekday]} ({target_date})")
        
        # 우선순위 2: 내일 (가장 명확한 표현)
        elif '내일' in when_text or 'tomorrow' in when_text:
            target_date = (base_time + timedelta(days=1)).date()
            print(f"      📅 날짜: 내일 ({target_date})")
        
        # 우선순위 3: 모레
        elif '모레' in when_text:
            target_date = (base_time + timedelta(days=2)).date()
            print(f"      📅 날짜: 모레 ({target_date})")
        
        # 우선순위 4: 오늘 (내일보다 낮은 우선순위)
        elif '오늘' in when_text or 'today' in when_text:
            # '오늘 내일' 같은 경우 내일이 이미 처리되었으므로 여기 도달하지 않음
            target_date = base_time.date()
            print(f"      📅 날짜: 오늘 ({target_date})")
        
        # 우선순위 5: 이번주
        elif '이번주' in when_text or 'this week' in when_text:
            # 이번 주 일요일로 설정 (주간 일정 점검용)
            days_until_sunday = (6 - base_time.weekday()) % 7
            if days_until_sunday == 0:  # 오늘이 일요일이면 다음 일요일
                days_until_sunday = 7
            target_date = (base_time + timedelta(days=days_until_sunday)).date()
            print(f"      📅 날짜: 이번 주 일요일 ({target_date})")
        
        # 우선순위 6: 다음주
        elif '다음주' in when_text or 'next week' in when_text:
            # 다음 주 일요일로 설정
            days_until_next_sunday = (6 - base_time.weekday()) % 7 + 7
            target_date = (base_time + timedelta(days=days_until_next_sunday)).date()
            print(f"      📅 날짜: 다음 주 일요일 ({target_date})")
        
        else:
            # 구체적인 날짜가 없으면 내일로 설정
            target_date = (base_time + timedelta(days=1)).date()
            print(f"      📅 날짜: 구체적 언급 없음 → 내일 ({target_date})")
        
        # 시간 설정
        if extracted_hour is not None and extracted_minute is not None:
            # 구체적인 시간이 추출된 경우
            final_hour = extracted_hour
            final_minute = extracted_minute
            print(f"      🕐 시간: 추출됨 → {final_hour:02d}:{final_minute:02d}")
        else:
            # 시간이 불명확한 경우 기본값 사용
            final_hour = default_hour
            final_minute = default_minute
            print(f"      🕐 시간: 불명확 → 기본값 {final_hour:02d}:{final_minute:02d}")
        
        # 최종 datetime 객체 생성
        try:
            start_time = datetime.combine(target_date, datetime.min.time().replace(
                hour=final_hour, minute=final_minute
            ))
            start_time = self.kst.localize(start_time)
            
            # 종료 시간 (1시간 후)
            end_time = start_time + timedelta(hours=1)
            
            print(f"      ✅ 최종 시간: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%H:%M')}")
            
            return start_time, end_time
            
        except ValueError as e:
            print(f"      ❌ 시간 생성 오류: {e}")
            return None, None
    
    def create_event_hash(self, schedule):
        """중복 체크를 위한 일정 해시 생성"""
        # 메시지 내용, 작성자, 시간을 조합하여 고유한 해시 생성
        content = schedule.get('content', '')[:100]  # 내용 일부만 사용
        author = schedule.get('author', '')
        created_at = schedule.get('created_at', '')
        
        # 간단한 해시 생성 (중복 방지용)
        hash_str = f"{content}_{author}_{created_at}"
        return hash(hash_str)
    
    def create_event_from_schedule(self, schedule):
        """일정 정보를 바탕으로 Google Calendar 이벤트 생성"""
        try:
            # 중복 체크
            event_hash = self.create_event_hash(schedule)
            if event_hash in self.added_events:
                print(f"  ⚠️ 중복 일정 건너뛰기: {schedule.get('content', '')[:50]}...")
                return None
            
            # 시간 파싱
            start_time, end_time = self.parse_schedule_time(schedule)
            
            if not start_time:
                print(f"  ⚠️ 시간 정보 파싱 실패: {schedule.get('content', '')[:50]}...")
                return None
            
            # 이벤트 제목 생성
            schedule_type = schedule.get('schedule_type', '일정')
            what = schedule.get('extracted_info', {}).get('what', '')
            author = schedule.get('author', 'Unknown')
            
            if what:
                title = f"[{schedule_type}] {what}"
            else:
                title = f"[{schedule_type}] Discord 일정"
            
            # 이벤트 설명 생성 (더 상세하게)
            when_info = schedule.get('extracted_info', {}).get('when', '미상')
            where_info = schedule.get('extracted_info', {}).get('where', '미상')
            confidence = schedule.get('confidence', 0)
            
            description = f"""Discord에서 자동 추출된 일정

📝 원본 메시지: "{schedule.get('content', '')}"
👤 작성자: {author}
📍 채널: {schedule.get('channel', 'Unknown')}
🕐 작성 시간: {schedule.get('created_at', 'Unknown')}
🎯 확신도: {confidence:.1%}

📊 추출된 정보:
• 언제: {when_info}
• 무엇: {schedule.get('extracted_info', {}).get('what', '미상')}
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
                'colorId': '9',  # 파란색으로 설정 (Discord 색상)
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},  # 30분 전 알림
                        {'method': 'popup', 'minutes': 10},  # 10분 전 알림
                    ],
                },
            }
            
            # 중복 방지를 위해 해시 저장
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
            print(f"   🎯 AI 추출 시간: {schedule.get('extracted_info', {}).get('when', '미상')}")
            
            try:
                # 이벤트 생성
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
                print(f"      🔗 링크: {created_event.get('htmlLink', 'N/A')}")
                
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
            print(f"   📅 Google Calendar에서 확인하세요: https://calendar.google.com")
            print(f"   🔔 알림: 30분 전, 10분 전 팝업 알림이 설정되었습니다.")

async def add_schedules_to_google_calendar(schedules):
    """일정들을 Google Calendar에 추가하는 메인 함수"""
    print("📅 Google Calendar 연동을 시작합니다...")
    
    try:
        # Calendar Manager 초기화
        calendar_manager = CalendarManager()
        
        # 일정들을 캘린더에 추가
        calendar_manager.add_schedules_to_calendar(schedules)
        
        return True
        
    except Exception as e:
        print(f"❌ Google Calendar 연동 실패: {e}")
        return False
