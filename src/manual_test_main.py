#!/usr/bin/env python3
"""
Discord Schedule Bot - 데이터 기반 필터링 정확도 테스트
6개월 데이터로 수동 검증하여 키워드 필터링 성능 평가
"""

import asyncio
import sys
import os
from datetime import datetime
import pytz

# 테스트 모듈 import
from manual_test_collector import test_data_based_filtering

def print_test_info():
    """테스트 정보 출력"""
    print("🧪 데이터 기반 필터링 테스트 특징:")
    print("   • 6개월 데이터 (2월~7월) 크롤링")
    print("   • 26개 데이터 분석 키워드 + '현합' 사용")
    print("   • 점수 시스템 (8점 이상 필터링)")
    print("   • 실제 일정 날짜와 비교 검증")
    print("   • True/False Positive 수동 확인 가능")

def print_keyword_strategy():
    """키워드 전략 출력"""
    print("🔥 데이터 기반 키워드 전략:")
    print("   고효율 키워드 (10점): 합니다, 그래서, 공연, 연습, 세팅")
    print("   핵심 키워드 (5점): 합주, 리허설, 콘서트, 라이트, 더스트, 현합")
    print("   시간 키워드 (3점): 오늘, 내일, 이번, 언제, 몇시, 시간")
    print("   보조 키워드 (1점): 저희, mtr, 우리, everyone, 같습니다, 끝나고")
    print("   시간패턴 (+5점): 숫자+시 패턴 (예: 2시, 14시 30분)")
    print("   📊 필터링 기준: 총 8점 이상")

async def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🧪 데이터 기반 필터링 정확도 테스트 v1.0")
    print("=" * 70)
    
    print_test_info()
    print()
    print_keyword_strategy()
    print()
    
    # 한국 시간 설정
    kst = pytz.timezone('Asia/Seoul')
    start_time = datetime.now(kst)
    print(f"🕐 테스트 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    try:
        print(f"\n" + "=" * 70)
        print(f"🎯 단계: 6개월 데이터로 필터링 정확도 검증")
        print("=" * 70)
        print("📅 기간: 2025년 2월 1일 ~ 7월 31일 (6개월)")
        print("🔍 방식: 26개 데이터 분석 키워드 + 점수 시스템")
        print("📊 목표: True/False Positive 비율 수동 확인")
        print("💰 비용: 0원 (OpenAI API 사용 안함)")
        
        # 데이터 기반 필터링 테스트 실행
        await test_data_based_filtering()
        
        # 테스트 완료 정보
        end_time = datetime.now(kst)
        duration = end_time - start_time
        
        print(f"\n" + "=" * 70)
        print(f"🎉 데이터 기반 필터링 테스트 완료!")
        print("=" * 70)
        print(f"🕐 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 종료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  소요: {duration.total_seconds():.1f}초")
        
        print(f"\n📋 다음 단계 가이드:")
        print(f"1. 🔍 위의 '실제 일정일 샘플' 검토 → True Positive 정확도 확인")
        print(f"2. 📅 'False Positive 후보' 검토 → 오분류 비율 파악")
        print(f"3. 📊 키워드별 성능 분석 → 개선점 찾기")
        print(f"4. ✅ 만족스러우면 → OpenAI API 단계로 진행")
        print(f"5. 🛠️  개선 필요하면 → 점수 기준 또는 키워드 조정")
        
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
    
    # 테스트 모드: Discord Token만 필요
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
    
    print(f"\n✅ 데이터 기반 필터링 테스트 준비 완료!")
    print(f"💡 OpenAI API나 Google Calendar API는 불필요합니다.")
    
    return True

if __name__ == "__main__":
    if not check_environment():
        print("\n❌ Discord Token이 설정되지 않았습니다.")
        print("💡 DISCORD_TOKEN 환경변수를 설정한 후 다시 실행해주세요.")
        sys.exit(1)
    
    print("=" * 50)
    print("🚀 데이터 기반 필터링 테스트를 시작합니다...")
    
    # 비동기 메인 함수 실행
    try:
        asyncio.run(main())
        print("\n👋 데이터 기반 필터링 테스트가 완료되었습니다.")
        print("💡 분석 결과를 바탕으로 필터링 성능을 평가하세요!")
    except KeyboardInterrupt:
        print("\n⏸️  사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 시스템 치명적 오류: {e}")
        print(f"📞 개발자에게 문의하거나 GitHub Issues에 오류를 제보해주세요.")
        sys.exit(1)
