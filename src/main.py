#!/usr/bin/env python3
"""
Discord Schedule Bot - 메인 실행 파일
Discord 메시지 수집 → AI 분류 → Google Calendar 연동
"""

import asyncio
import sys
import os
from datetime import datetime
import pytz

# 프로젝트 모듈 import
from discord_collector import collect_discord_messages
from ai_classifier import classify_schedule_messages

async def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🤖 Discord Schedule Bot - 자동 일정 추출 시스템")
    print("=" * 70)
    
    # 실행 모드 확인 (환경변수로 제어)
    analysis_mode = os.getenv('ANALYSIS_MODE', 'false').lower() == 'true'
    
    if analysis_mode:
        print("🔍 키워드 분석 모드 - OpenAI API 사용하지 않음")
    else:
        print("🚀 전체 실행 모드 - Discord → AI → Calendar")
    
    # 한국 시간 설정
    kst = pytz.timezone('Asia/Seoul')
    start_time = datetime.now(kst)
    print(f"🕐 실행 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    try:
        # 1단계: Discord 메시지 수집
        print(f"\n📥 1단계: Discord 메시지 수집")
        print("-" * 50)
        
        messages = await collect_discord_messages()
        
        if not messages:
            print("❌ 수집된 메시지가 없습니다. 프로그램을 종료합니다.")
            return
        
        print(f"✅ {len(messages)}개 메시지 수집 완료!")
        
        # 분석 모드에서는 여기서 종료
        if analysis_mode:
            print(f"\n🔍 키워드 분석 완료!")
            print(f"💡 위 결과를 검토하여 키워드를 최적화한 후 전체 모드로 실행하세요.")
            print(f"📝 전체 모드 실행: GitHub Actions에서 ANALYSIS_MODE 제거 또는 'false'로 설정")
            return
        
        # 2단계: AI 일정 분류 (전체 모드에서만)
        print(f"\n🤖 2단계: AI 일정 분류")
        print("-" * 50)
        
        schedules, non_schedules = await classify_schedule_messages(messages)
        
        if not schedules:
            print("📝 일정으로 분류된 메시지가 없습니다.")
            print("💡 키워드나 분류 기준을 조정해볼 수 있습니다.")
            return
        
        print(f"✅ {len(schedules)}개 일정 발견!")
        
        # 3단계: Google Calendar 연동 (다음에 구현 예정)
        print(f"\n📅 3단계: Google Calendar 연동")
        print("-" * 50)
        print("🚧 Google Calendar 연동 기능은 다음 단계에서 구현 예정입니다.")
        print("📋 현재까지 발견된 일정들:")
        
        # 발견된 일정들 상세 출력
        for i, schedule in enumerate(schedules):
            print(f"\n   📅 일정 #{i+1}:")
            print(f"      💬 내용: {schedule.get('content', '')}")
            print(f"      👤 작성자: {schedule.get('author', '')}")
            print(f"      📝 채널: {schedule.get('channel', '')}")
            print(f"      🎯 유형: {schedule.get('schedule_type', 'Unknown')}")
            print(f"      🕐 언제: {schedule.get('extracted_info', {}).get('when', '미상')}")
            print(f"      📍 내용: {schedule.get('extracted_info', {}).get('what', '미상')}")
            print(f"      📍 장소: {schedule.get('extracted_info', {}).get('where', '미상')}")
            print(f"      🎯 확신도: {schedule.get('confidence', 0):.1%}")
            print(f"      💭 이유: {schedule.get('reason', '')}")
        
        # 실행 완료 정보
        end_time = datetime.now(kst)
        duration = end_time - start_time
        
        print(f"\n" + "=" * 70)
        print(f"🎉 실행 완료!")
        print(f"🕐 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
        print(f"⏱️  소요 시간: {duration.total_seconds():.1f}초")
        print(f"📊 최종 결과:")
        print(f"   📥 수집된 메시지: {len(messages)}개")
        print(f"   📅 발견된 일정: {len(schedules)}개")
        print(f"   💬 일반 대화: {len(non_schedules)}개")
        print(f"   🎯 일정 비율: {len(schedules)/(len(schedules)+len(non_schedules))*100:.1f}%")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print(f"\n⏸️  사용자에 의해 중단되었습니다.")
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생:")
        print(f"   오류 내용: {str(e)}")
        print(f"   오류 타입: {type(e).__name__}")
        
        # 디버깅을 위한 상세 정보 (개발 중에만)
        if os.getenv('DEBUG', '').lower() == 'true':
            import traceback
            print(f"\n🔍 상세 스택 트레이스:")
            traceback.print_exc()

def check_environment():
    """환경 변수 및 설정 확인"""
    required_vars = ['DISCORD_TOKEN', 'OPENAI_API_KEY', 'GOOGLE_CREDENTIALS', 'CALENDAR_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 누락된 환경 변수: {', '.join(missing_vars)}")
        print(f"💡 GitHub Secrets에서 다음 변수들을 설정해주세요:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print(f"✅ 모든 환경 변수가 설정되었습니다.")
    return True

if __name__ == "__main__":
    print("🔍 환경 변수 확인 중...")
    
    if not check_environment():
        print("❌ 환경 설정이 완료되지 않았습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    
    # 비동기 메인 함수 실행
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        sys.exit(1)
