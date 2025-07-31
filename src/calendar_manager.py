import os
import json
import pytz
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
    
    def parse_schedule_time(self, schedule):
        """일정 시간 정보를 파싱하여 datetime 객체 생성"""
        when_text = schedule.get('extracted_info', {}).get('when', '').lower()
        created_at = schedule.get('created_at')
        
        # 기본값: 메시지 작성 시간 기준
        if isinstance(created_at, str):
            base_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            base_time = base_time.astimezone(self.kst)
        else:
            base_time = created_at.astimezone(self.kst) if created_at else datetime.now(self.kst)
        
        # 시간 표현 파싱
        start_time = None
        end_time = None
        
        if '오늘' in when_text or 'today' in when_text:
            # 오늘 일정
            target_date = base_time.date()
            
            if '8시' in when_text or '8인가' in when_text:
                start_time = datetime.combine(target_date, datetime.min.time().replace(hour=20))  # 오후 8시로 가정
            elif '9시' in when_text:
                start_time = datetime.combine(target_date, datetime.min.time().replace(hour=21))  # 오후 9시로 가정
            else:
                # 구체적 시간이 없으면 오후 6시로 기본 설정
                start_time = datetime.combine(target_date, datetime.min.time().replace(hour=18))
                
        elif '내일' in when_text or 'tomorrow' in when_text:
            # 내일 일정
            target_date = (base_time + timedelta(days=1)).date()
            start_time = datetime.combine(target_date, datetime.min.time().replace(hour=18))  # 기본 오후 6시
            
        elif '다음주' in when_text or 'next week' in when_text:
            # 다음주 일정 (월요일로 설정)
            days_ahead = 7 - base_time.weekday()  # 다음 월요일까지의 일수
            target_date = (base_time + timedelta(days=days_ahead)).date()
            start_time = datetime.combine(target_date, datetime.min.time().replace(hour=18))
            
        else:
            # 시간 정보가 없으면 메시지 작성 시간 기준으로 내일 오후 6시
            target_date = (base_time + timedelta(days=1)).date()
            start_time = datetime.combine(target_date, datetime.min.time().replace(hour=18))
        
        # 시간대 설정
        if start_time:
            start_time = self.kst.localize(start_time)
            # 기본 1시간 일정으로 설정
            end_time = start_time + timedelta(hours=1)
        
        return start_time, end_time
    
    def create_event_from_schedule(self, schedule):
        """일정 정보를 바탕으로 Google Calendar 이벤트 생성"""
        try:
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
            
            # 이벤트 설명 생성
            description = f"""Discord에서 자동 추출된 일정

원본 메시지: "{schedule.get('content', '')}"
작성자: {author}
채널: {schedule.get('channel', 'Unknown')}
작성 시간: {schedule.get('created_at', 'Unknown')}
확신도: {schedule.get('confidence', 0):.1%}

추출된 정보:
- 언제: {schedule.get('extracted_info', {}).get('when', '미상')}
- 무엇: {schedule.get('extracted_info', {}).get('what', '미상')}
- 어디서: {schedule.get('extracted_info', {}).get('where', '미상')}

분류 이유: {schedule.get('reason', '없음')}
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
            }
            
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
        
        added_count = 0
        failed_count = 0
        
        for i, schedule in enumerate(schedules):
            print(f"\n  📝 일정 {i+1}/{len(schedules)}: {schedule.get('content', '')[:50]}...")
            
            try:
                # 이벤트 생성
                event = self.create_event_from_schedule(schedule)
                if not event:
                    failed_count += 1
                    continue
                
                # Google Calendar에 이벤트 추가
                created_event = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event
                ).execute()
                
                # 결과 출력
                start_time = created_event['start'].get('dateTime', created_event['start'].get('date'))
                print(f"     ✅ 추가 완료: {event['summary']}")
                print(f"     🕐 시간: {start_time}")
                print(f"     🔗 링크: {created_event.get('htmlLink', 'N/A')}")
                
                added_count += 1
                
            except HttpError as http_error:
                print(f"     ❌ Google API 오류: {http_error}")
                failed_count += 1
                
            except Exception as e:
                print(f"     ❌ 예상치 못한 오류: {e}")
                failed_count += 1
        
        # 최종 결과
        print(f"\n📊 캘린더 추가 완료!")
        print(f"   ✅ 성공: {added_count}개")
        print(f"   ❌ 실패: {failed_count}개")
        
        if added_count > 0:
            print(f"   🎯 성공률: {added_count/len(schedules)*100:.1f}%")
            print(f"   📅 Google Calendar에서 확인하세요: https://calendar.google.com")

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

# 테스트용 메인 함수
if __name__ == "__main__":
    print("=" * 60)
    print("📅 Google Calendar Manager - 테스트")
    print("=" * 60)
    
    # 샘플 일정으로 테스트
    sample_schedules = [
        {
            'id': 'test_1',
            'content': '오늘합주는8시 그대로 하죠?',
            'author': 'happyme_1009',
            'channel': '#💬잡담',
            'created_at': datetime.now(pytz.timezone('Asia/Seoul')),
            'schedule_type': '합주',
            'confidence': 0.95,
            'extracted_info': {
                'when': '오늘 8시',
                'what': '합주',
                'where': '연습실'
            },
            'reason': '구체적인 시간과 활동이 명시됨'
        }
    ]
    
    import asyncio
    
    async def test():
        success = await add_schedules_to_google_calendar(sample_schedules)
        print(f"\n🎯 테스트 결과: {'성공' if success else '실패'}")
    
    asyncio.run(test())# Google Calendar manager
