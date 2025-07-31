#!/usr/bin/env python3
"""
Discord Schedule Bot - 키워드 분석 전용 실행 파일
실제 일정과 연관된 키워드 패턴을 추출하여 더 정확한 필터링 로직 구축
"""

import asyncio
import sys
import os
from datetime import datetime
import pytz

# 키워드 분석 모듈 import
from keyword_analysis_collector import analyze_discord_keywords

def print_analysis_info():
    """키워드 분석 정보 출력"""
    print("💡 키워드 분석 모드 특징:")
    print("   • OpenAI API 사용 안함 (비용 없음)")
    print("   • 필터링 없이 모든 메시지 수집")
    print("   • 실제 일정 날짜와 메시지 매칭 분석")
    print("   • 데이터 기반 키워드 추출")

def print_schedule_data():
    """분석할 실제 일정 데이터 출력"""
    schedules = [
        "250603 라이트 합주", "250604 더스트 합주", "250610 라이트 합주",
        "250611 더스트 합주", "250617 라이트 합주", "250618 더스트 합주",
        "250620 라이트 현실합주", "250625 라이트 합주", "250626 더스트 합주",
        "250629 더스트 현실합주", "250630 라이트 현실합주", "250701 라이트 합주",
        "250702 더스트 합주", "250708 라이트 합주", "250709 더스트 합주",
        "250711 라이트 현실합주", "250715 라이트 합주", "250716 더스트 합주",
        "250718 리허설", "250722 라이트 합주", "250723 더스트 합주",
        "250725 라이트 합주", "250729 리허설", "250730 더스트 합주",
        "250801 라이트 현실합주", "250808 리허설", "250809 콘서트"
    ]
    
    print("📅 분석 대상 실제 일정 (총 27개):")
    for i, schedule in enumerate(schedules):
        print(f"   {i+1:2d}. {schedule}")

async def main():
    """키워드 분석 메인 함수"""
    print("=" * 70)
    print("🔬 Discord 키워드 분석 시스템 v1.0")
    print("=" * 70)
    
    print_analysis_info()
    print()
    print_schedule_data()
    print()
    
    # 한국 시간 설정
    kst = pytz.timezone('Asia/Seoul')
    start_time = datetime.now(kst)
    print(f"🕐 분석 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    try:
        print(f"\n" + "=" * 70)
        print(f"📊 단계 1: 데이터 기반 키워드 분석")
        print("=" * 70)
        print("🎯 목표: False Positive/Negative 최소화")
        print("📅 기간: 2025년 6월 1일 ~ 7월 31일")
        print("🔍 방식: 실제 일정 날짜와 메시지 매칭 분석")
        print("💰 비용: 0원 (OpenAI API 사용 안함)")
        
        # 키워드 분석 실행
        await analyze_discord_keywords()
        
        # 분석 완료 정보
        end_time = datetime.now(kst)
        duration = end_time - start_time
        
        print(f"\n" + "=" * 70)
        print(f"🎉 키워드 분석 완료!")
        print("=" * 70)
        print(f"🕐 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 종료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  소요: {duration.total_seconds():.1f}초")
        
        print(f"\n📋 다음 단계 가이드:")
        print(f"1. 🔍 위 분석 결과의 '추천 키워드' 확인")
        print(f"2. 🛠️  기존 필터링 로직에 새 키워드 적용")
        print(f"3. 🧪 개선된 필터링으로 다시 테스트")
        print(f"4. 🤖 OpenAI API 사용하여 최종 검증")
        
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

def check_environment():
    """환경 변수 확인 (Discord Token만 필요)"""
    print("🔍 환경 설정 확인 중...")
    print("=" * 50)
    
    # 키워드 분석 모드: Discord Token만 필요
    required_vars = ['DISCORD_TOKEN']
    
    missing_vars = []
    present_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            present_vars.append(var)
        else:
            missing_vars.append(var)
    
    # 결과 출력
    print(f"✅ 설정된 환경변수:")
    for var in present_vars:
        value = os.getenv(var)
        preview = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "설정됨"
        print(f"   • {var}: {preview}")
    
    if missing_vars:
        print(f"\n❌ 누락된 환경변수:")
        for var in missing_vars:
            print(f"   • {var}")
        
        print(f"\n💡 해결 방법:")
        if os.getenv('GITHUB_ACTIONS'):
            print(f"   🔧 GitHub Repository → Settings → Secrets")
            print(f"   📝 DISCORD_TOKEN Secret 추가")
        else:
            print(f"   🔧 DISCORD_TOKEN 환경변수 설정")
        
        return False
    
    print(f"\n✅ 키워드 분석 준비 완료!")
    print(f"💡 OpenAI API나 Google Calendar API는 불필요합니다.")
    
    return True

if __name__ == "__main__":
    if not check_environment():
        print("\n❌ Discord Token이 설정되지 않았습니다.")
        print("💡 DISCORD_TOKEN 환경변수를 설정한 후 다시 실행해주세요.")
        sys.exit(1)
    
    print("=" * 50)
    print("🚀 키워드 분석을 시작합니다...")
    
    # 비동기 메인 함수 실행
    try:
        asyncio.run(main())
        print("\n👋 키워드 분석이 완료되었습니다.")
        print("💡 분석 결과를 바탕으로 필터링 로직을 개선하세요!")
    except KeyboardInterrupt:
        print("\n⏸️  사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 시스템 치명적 오류: {e}")
        print(f"📞 개발자에게 문의하거나 GitHub Issues에 오류를 제보해주세요.")
        sys.exit(1)
