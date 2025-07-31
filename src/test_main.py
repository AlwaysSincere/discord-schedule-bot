# src/test_main.py - 7일 테스트용
#!/usr/bin/env python3
"""
Discord Schedule Bot - 7일 테스트 버전
안전하게 소량 데이터로 전체 시스템 테스트
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pytz

# 기존 모듈들 import
from discord_collector import MessageCollector
from ai_classifier import classify_schedule_messages
from calendar_manager import add_schedules_to_google_calendar

class TestMessageCollector(MessageCollector):
    """7일 제한 테스트용 수집기"""
    
    async def collect_recent_messages_with_progress(self):
        """7일간만 메시지 수집 (테스트용)"""
        print(f'\n🧪 테스트 모드: 최근 7일간만 수집합니다')
        
        # 7일 제한
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        seven_days_ago = now - timedelta(days=7)  # 7일로 제한
        
        print(f'📅 테스트 기간: {seven_days_ago.strftime("%Y-%m-%d %H:%M")} ~ {now.strftime("%Y-%m-%d %H:%M")}')
        print(f'💰 예상 비용: 약 500-1,000원')
        print(f'⏱️ 예상 시간: 3-5분')
        
        total_processed = 0
        total_filtered = 0
        
        # 모든 서버의 모든 채널에서 메시지 수집 (7일만)
        for guild in self.guilds:
            print(f'\n🏢 서버: {guild.name}')
            
            for channel in guild.text_channels:
                try:
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    print(f'  📝 #{channel.name:<20s} ', end='', flush=True)
                    
                    channel_processed = 0
                    channel_filtered = 0
                    
                    # 7일간 메시지만 가져오기
                    async for message in channel.history(after=seven_days_ago, limit=None):
                        if message.author.bot:
                            continue
                        
                        total_processed += 1
                        channel_processed += 1
                        
                        # 필터링 적용
                        is_schedule, reason = self.is_likely_schedule(message.content)
                        
                        if is_schedule:
                            total_filtered += 1
                            channel_filtered += 1
                            
                            # 메시지 정보 저장
                            message_data = {
                                'id': message.id,
                                'content': message.content,
                                'author': str(message.author),
                                'channel': f'#{message.channel.name}',
                                'guild': message.guild.name,
                                'created_at': message.created_at.astimezone(kst),
                                'filter_reason': reason,
                                'message_length': len(message.content),
                            }
                            self.collected_messages.append(message_data)
                    
                    # 채널 결과 출력
                    filter_rate = f"{(channel_filtered/channel_processed*100):.1f}%" if channel_processed > 0 else "0%"
                    print(f'📊 {channel_processed:4d}개 → {channel_filtered:3d}개 ({filter_rate})')
                    
                except discord.Forbidden:
                    print('❌ 접근 권한 없음')
                except Exception as e:
                    print(f'❌ 오류: {str(e)[:50]}...')
        
        # 테스트 수집 결과
        print(f'\n📊 7일 테스트 수집 완료!')
        print('=' * 70)
        print(f'   📥 처리된 메시지: {total_processed:,}개')
        print(f'   🔍 필터링 결과: {total_filtered:,}개')
        print(f'   📈 필터링 비율: {(total_filtered/total_processed*100):.2f}%' if total_processed > 0 else '   비율: 0%')
        print(f'   💰 AI 분석 예상 비용: 약 {((total_filtered + 14) // 15 * 5):,}원')
        
        # 맥락 묶기
        if self.collected_messages:
            await self.group_context_messages()
            print(f'   🔗 AI 분석 대상: {len(self.collected_messages)}개 맥락 그룹')

async def collect_test_messages():
    """7일 테스트용 메시지 수집"""
    print("🧪 7일 테스트 메시지 수집을 시작합니다...")
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ 오류: DISCORD_TOKEN이 설정되지 않았습니다!")
        return []
    
    collector = TestMessageCollector()
    collected_messages = []
    
    try:
        await collector.start(token)
        collected_messages = collector.collected_messages.copy()
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        
    finally:
        try:
            if not collector.is_closed():
                await collector.close()
            await asyncio.sleep(1)
        except:
            pass
    
    return collected_messages

async def main():
    """7일 테스트 메인 함수"""
    print("=" * 70)
    print("🧪 Discord Schedule Bot - 7일 테스트 모드")
    print("=" * 70)
    print("💡 목적: 전체 시스템을 안전하게 소량으로 테스트")
    print("📅 범위: 최근 7일간 데이터만")
    print("💰 예상 비용: 500-1,000원")
    print("⏱️ 예상 시간: 3-5분")
    
    try:
        # 1단계: 7일간 메시지 수집
        print(f"\n" + "=" * 70)
        print(f"📥 1단계: 7일간 메시지 수집")
        print("=" * 70)
        
        messages = await collect_test_messages()
        
        if not messages:
            print("❌ 수집된 메시지가 없습니다.")
            return
        
        print(f"✅ {len(messages):,}개 맥락 그룹 수집 완료!")
        
        # 2단계: AI 일정 분류
        print(f"\n" + "=" * 70)
        print(f"🤖 2단계: AI 일정 분류")
        print("=" * 70)
        
        schedules, non_schedules = await classify_schedule_messages(messages)
        
        total_analyzed = len(schedules) + len(non_schedules)
        print(f"\n📊 AI 분석 완료!")
        print(f"   📤 분석 완료: {total_analyzed:,}개")
        print(f"   📅 일정 발견: {len(schedules)}개")
        print(f"   💬 일정 아님: {len(non_schedules)}개")
        
        if not schedules:
            print("💡 발견된 일정이 없습니다. (7일 테스트라서 정상)")
            return
        
        # 3단계: Google Calendar 연동
        print(f"\n" + "=" * 70)
        print(f"📅 3단계: Google Calendar 연동")
        print("=" * 70)
        
        calendar_success = await add_schedules_to_google_calendar(schedules)
        
        if calendar_success:
            print(f"✅ 테스트 완료! Google Calendar에 {len(schedules)}개 일정 추가됨")
        else:
            print(f"⚠️ 캘린더 연동 실패, 하지만 AI 분석은 성공")
        
        # 테스트 결과 요약
        print(f"\n" + "=" * 70)
        print(f"🎉 7일 테스트 완료!")
        print("=" * 70)
        print(f"📊 테스트 결과:")
        print(f"   📥 수집: {len(messages):,}개 그룹")
        print(f"   🤖 AI 분석: {total_analyzed:,}개 완료")
        print(f"   📅 발견 일정: {len(schedules)}개")
        print(f"   ✅ 시스템 상태: 정상 작동")
        
        print(f"\n💡 다음 단계:")
        print(f"   1. 결과가 만족스럽다면 → 전체 시스템 실행")  
        print(f"   2. Google Calendar 확인")
        print(f"   3. 필요시 설정 조정 후 재실행")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류: {e}")

if __name__ == "__main__":
    # 7일 테스트 실행
    try:
        asyncio.run(main())
        print("\n🎉 7일 테스트가 완료되었습니다!")
    except KeyboardInterrupt:
        print("\n⏸️ 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n💥 테스트 오류: {e}")
