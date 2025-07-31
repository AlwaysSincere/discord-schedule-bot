#!/usr/bin/env python3
"""
Discord Schedule Bot - 메인 실행 파일 (개선된 버전)
Discord 메시지 수집 → AI 분류 → Google Calendar 연동
"""

import asyncio
import sys
import os
from datetime import datetime
import pytz

# 프로젝트 모듈 import
from discord_collector import collect_discord_messages

# AI 모듈은 조건부 import (키워드 분석 모드에서는 불필요)
try:
    from ai_classifier import classify_schedule_messages
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  AI 모듈 import 실패 - 키워드 분석 모드에서만 실행 가능")

# Calendar 모듈은 조건부 import
try:
    from calendar_manager import add_schedules_to_google_calendar
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    print("⚠️  Calendar 모듈 import 실패 - 캘린더 연동 불가")

def print_system_info():
    """시스템 정보 출력"""
    print("🔧 시스템 정보:")
    print(f"   Python 버전: {sys.version.split()[0]}")
    print(f"   실행 환경: {'GitHub Actions' if os.getenv('GITHUB_ACTIONS') else '로컬'}")
    print(f"   AI 모듈: {'✅ 사용 가능' if AI_AVAILABLE else '❌ 불가능'}")
    print(f"   Calendar 모듈: {'✅ 사용 가능' if CALENDAR_AVAILABLE else '❌ 불가능'}")

def print_environment_status():
    """환경 변수 상태 출력 (값은 숨김)"""
    required_vars = {
        'DISCORD_TOKEN': '필수',
        'OPENAI_API_KEY': 'AI 분석용',
        'GOOGLE_CREDENTIALS': 'Calendar 연동용',
        'CALENDAR_ID': 'Calendar 연동용'
    }
    
    print("🔑 환경 변수 상태:")
    for var, description in required_vars.items():
        status = "✅ 설정됨" if os.getenv(var) else "❌ 없음"
        print(f"   {var}: {status} ({description})")

async def main():
    """메인 실행 함수 (개선된 버전)"""
    print("=" * 70)
    print("🤖 Discord Schedule Bot - 자동 일정 추출 시스템 v2.0")
    print("=" * 70)
    
    # 시스템 정보 출력
    print_system_info()
    print()
    print_environment_status()
    print()
    
    # 실행 모드 확인 (환경변수로 제어)
    analysis_mode = os.getenv('ANALYSIS_MODE', 'false').lower() == 'true'
    
    if analysis_mode:
        print("🔍 키워드 분석 모드 - OpenAI API 사용하지 않음")
        print("   → Discord 메시지 수집 및 필터링 품질 분석만 수행")
    else:
        print("🚀 전체 실행 모드 - Discord → AI → Calendar")
        print("   → 60일간 데이터 수집 → AI 분류 (개선된 정확도) → 캘린더 연동")
    
    # 한국 시간 설정
    kst = pytz.timezone('Asia/Seoul')
    start_time = datetime.now(kst)
    print(f"🕐 실행 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    try:
        # 1단계: Discord 메시지 수집
        print(f"\n" + "=" * 70)
        print(f"📥 1단계: Discord 메시지 수집 (60일 대용량 테스트)")
        print("=" * 70)
        
        messages = await collect_discord_messages()
        
        if not messages:
            print("❌ 수집된 메시지가 없습니다.")
            print("💡 가능한 원인:")
            print("   • Discord 토큰이 잘못됨")
            print("   • 봇이 서버에 없거나 권한이 부족함")
            print("   • 최근 60일간 일정 관련 메시지가 없음")
            print("   • 필터링 기준이 너무 엄격함")
            return
        
        print(f"\n✅ {len(messages):,}개 맥락 그룹 수집 완료!")
        
        # 분석 모드에서는 여기서 종료
        if analysis_mode:
            print(f"\n🔍 키워드 분석 완료!")
            print(f"💡 위 필터링 결과를 검토하여 키워드를 최적화한 후 전체 모드로 실행하세요.")
            print(f"📝 전체 모드 실행: GitHub Actions에서 ANALYSIS_MODE 제거 또는 'false'로 설정")
            return
        
        # 대용량 데이터 경고
        estimated_batches = (len(messages) + 14) // 15
        estimated_cost = estimated_batches * 5
        estimated_time = estimated_batches * 1.5 / 60  # 분 단위
        
        print(f"\n📊 AI 분석 예상 정보:")
        print(f"   🔢 처리 대상: {len(messages):,}개 맥락 그룹")
        print(f"   📦 예상 배치: {estimated_batches}개 (배치당 15개)")
        print(f"   💰 예상 비용: 약 {estimated_cost:,}원")
        print(f"   ⏱️  예상 시간: 약 {estimated_time:.1f}분")
        
        # 2단계: AI 일정 분류 (전체 모드에서만)
        print(f"\n" + "=" * 70)
        print(f"🤖 2단계: AI 일정 분류 (개선된 정확도)")
        print("=" * 70)
        
        if not AI_AVAILABLE:
            print("❌ AI 모듈을 불러올 수 없습니다.")
            print("💡 키워드 분석 모드로 실행하거나 ai_classifier.py 파일을 확인해주세요.")
            return
        
        schedules, non_schedules = await classify_schedule_messages(messages)
        
        # AI 분석 결과 상세 출력
        total_analyzed = len(schedules) + len(non_schedules)
        print(f"\n📊 AI 분석 완료!")
        print(f"   📥 입력: {len(messages):,}개 맥락 그룹")
        print(f"   📤 출력: {total_analyzed:,}개 분석 완료")
        print(f"   📅 일정 발견: {len(schedules)}개")
        print(f"   💬 일정 아님: {len(non_schedules)}개")
        
        if total_analyzed > 0:
            schedule_ratio = len(schedules) / total_analyzed * 100
            print(f"   🎯 일정 비율: {schedule_ratio:.1f}%")
        
        if not schedules:
            print(f"\n💡 일정으로 분류된 메시지가 없습니다.")
            print(f"   🔍 가능한 원인:")
            print(f"      • 실제로 일정 관련 메시지가 없음")
            print(f"      • AI 분류 기준이 너무 엄격함 (확신도 85% 이상만 통과)")
            print(f"      • 대부분이 과거형 질문이나 일반 대화였음")
            return
        
        # 3단계: Google Calendar 연동
        print(f"\n" + "=" * 70)
        print(f"📅 3단계: Google Calendar 연동 (개선된 시간 파싱)")
        print("=" * 70)
        
        if not CALENDAR_AVAILABLE:
            print("❌ Calendar 모듈을 불러올 수 없습니다.")
            print("💡 calendar_manager.py 파일과 Google 인증 정보를 확인해주세요.")
            print(f"\n🎯 발견된 일정 요약:")
            for i, schedule in enumerate(schedules):
                print(f"   {i+1}. {schedule.get('schedule_type', 'Unknown')}: {schedule.get('content', '')[:50]}...")
        else:
            print(f"📅 {len(schedules)}개 일정을 Google Calendar에 추가합니다...")
            print(f"   🔄 중복 체크 및 시간 파싱 개선 적용")
            print(f"   ⏰ 기본 시간: 시간 불명확시 오전 6시로 설정")
            print(f"   📅 기본 날짜: 주간 일정은 일요일로 설정")
            
            calendar_success = await add_schedules_to_google_calendar(schedules)
            
            if calendar_success:
                print(f"\n✅ Google Calendar 연동 완료!")
                print(f"🔗 확인: https://calendar.google.com")
            else:
                print(f"\n❌ Google Calendar 연동 실패")
                print(f"💡 Google 인증 정보와 캘린더 ID를 확인해주세요.")
        
        # 실행 완료 정보
        end_time = datetime.now(kst)
        duration = end_time - start_time
        
        print(f"\n" + "=" * 70)
        print(f"🎉 전체 시스템 실행 완료!")
        print("=" * 70)
        print(f"🕐 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 종료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  소요: {duration.total_seconds():.1f}초 ({duration.total_seconds()/60:.1f}분)")
        
        print(f"\n📊 최종 성과 (60일 대용량 분석):")
        print(f"   📥 수집된 메시지: {len(messages):,}개 그룹 (60일간)")
        print(f"   🤖 AI 분석 완료: {total_analyzed:,}개")
        print(f"   📅 발견된 일정: {len(schedules)}개")
        print(f"   📈 전체 성공률: {(len(schedules)/len(messages)*100):.1f}%")
        print(f"   🎯 2달 데이터로 더 다양한 패턴 분석 완료!")
        
        if len(schedules) > 0:
            print(f"\n🎯 추출된 일정 요약:")
            schedule_types = {}
            for schedule in schedules:
                stype = schedule.get('schedule_type', 'Unknown')
                schedule_types[stype] = schedule_types.get(stype, 0) + 1
            
            for stype, count in sorted(schedule_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {stype}: {count}개")
        
        print("=" * 70)
        
    except KeyboardInterrupt:
        print(f"\n⏸️  사용자에 의해 중단되었습니다.")
        
    except Exception as e:
        end_time = datetime.now(kst)
        duration = end_time - start_time
        
        print(f"\n❌ 예상치 못한 오류 발생:")
        print(f"   🕐 오류 발생 시점: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   ⏱️  실행 시간: {duration.total_seconds():.1f}초")
        print(f"   🔍 오류 내용: {str(e)}")
        print(f"   📝 오류 타입: {type(e).__name__}")
        
        # 디버깅을 위한 상세 정보 (개발 중에만)
        if os.getenv('DEBUG', '').lower() == 'true':
            import traceback
            print(f"\n🔍 상세 스택 트레이스:")
            traceback.print_exc()
        else:
            print(f"\n💡 디버깅 정보가 필요하면 DEBUG=true 환경변수를 설정하세요.")

def check_environment():
    """환경 변수 및 설정 확인 (개선된 버전)"""
    # 분석 모드 확인
    analysis_mode = os.getenv('ANALYSIS_MODE', 'false').lower() == 'true'
    
    if analysis_mode:
        # 키워드 분석 모드: Discord Token만 필요
        required_vars = ['DISCORD_TOKEN']
        print("🔍 키워드 분석 모드 - Discord Token만 확인")
        print("   → 메시지 수집 및 필터링 품질 분석")
    else:
        # 전체 모드: 모든 환경변수 필요
        required_vars = ['DISCORD_TOKEN', 'OPENAI_API_KEY', 'GOOGLE_CREDENTIALS', 'CALENDAR_ID']
        print("🚀 전체 모드 - 모든 환경변수 확인")
        print("   → Discord → AI → Calendar 전체 파이프라인")
    
    missing_vars = []
    present_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            present_vars.append(var)
        else:
            missing_vars.append(var)
    
    # 결과 출력
    print(f"\n✅ 설정된 환경변수 ({len(present_vars)}개):")
    for var in present_vars:
        value = os.getenv(var)
        if 'TOKEN' in var or 'KEY' in var:
            preview = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "설정됨"
        else:
            preview = f"{len(value)}자" if value else "없음"
        print(f"   • {var}: {preview}")
    
    if missing_vars:
        print(f"\n❌ 누락된 환경변수 ({len(missing_vars)}개):")
        for var in missing_vars:
            print(f"   • {var}")
        
        print(f"\n💡 해결 방법:")
        if os.getenv('GITHUB_ACTIONS'):
            print(f"   🔧 GitHub Repository → Settings → Secrets and variables → Actions")
            print(f"   📝 다음 Secrets를 추가하세요:")
            for var in missing_vars:
                print(f"      - {var}")
        else:
            print(f"   🔧 환경변수를 설정하거나 .env 파일을 생성하세요.")
        
        return False
    
    print(f"\n✅ 필요한 환경변수가 모두 설정되었습니다!")
    
    # 전체 모드에서 추가 확인
    if not analysis_mode:
        print(f"\n🔧 모듈 가용성 최종 확인:")
        
        checks = [
            ("Discord 수집", True, "discord_collector.py"),
            ("AI 분류", AI_AVAILABLE, "ai_classifier.py + OpenAI API"),
            ("Calendar 연동", CALENDAR_AVAILABLE, "calendar_manager.py + Google API"),
        ]
        
        all_ready = True
        for name, available, requirement in checks:
            status = "✅ 준비완료" if available else "❌ 불가능"
            print(f"   • {name}: {status} ({requirement})")
            if not available:
                all_ready = False
        
        if not all_ready:
            print(f"\n⚠️  일부 모듈을 사용할 수 없지만 가능한 부분까지 실행합니다.")
    
    return True

if __name__ == "__main__":
    print("🔍 환경 설정 확인 중...")
    print("=" * 50)
    
    if not check_environment():
        print("\n❌ 필수 환경 설정이 완료되지 않았습니다.")
        print("💡 위의 가이드를 따라 환경변수를 설정한 후 다시 실행해주세요.")
        sys.exit(1)
    
    print("=" * 50)
    print("🚀 환경 설정 완료! 시스템을 시작합니다...")
    
    # 비동기 메인 함수 실행
    try:
        asyncio.run(main())
        print("\n👋 프로그램이 정상적으로 완료되었습니다.")
    except KeyboardInterrupt:
        print("\n⏸️  사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 시스템 치명적 오류: {e}")
        print(f"📞 개발자에게 문의하거나 GitHub Issues에 오류를 제보해주세요.")
        sys.exit(1)
