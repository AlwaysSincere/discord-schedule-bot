import discord
import os
import asyncio
from datetime import datetime, timedelta
import pytz
import json
import re

class KeywordAnalysisCollector(discord.Client):
    def __init__(self):
        # Discord 봇 초기화
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용 읽기 권한
        intents.guilds = True           # 서버 정보 접근 권한
        super().__init__(intents=intents)
        
        # 모든 메시지를 저장할 리스트 (필터링 없이)
        self.all_messages = []
        
        # 실제 일정 날짜들 (사용자 제공 데이터)
        self.actual_schedule_dates = [
            '2025-06-03', '2025-06-04', '2025-06-10', '2025-06-11',
            '2025-06-17', '2025-06-18', '2025-06-20', '2025-06-25', 
            '2025-06-26', '2025-06-29', '2025-06-30', '2025-07-01',
            '2025-07-02', '2025-07-08', '2025-07-09', '2025-07-11',
            '2025-07-15', '2025-07-16', '2025-07-18', '2025-07-22',
            '2025-07-23', '2025-07-25', '2025-07-29', '2025-07-30',
            '2025-08-01', '2025-08-08', '2025-08-09'
        ]
        
        # 실제 일정명들
        self.actual_schedule_names = [
            '라이트 합주', '더스트 합주', '라이트 현실합주', '더스트 현실합주',
            '리허설', '콘서트'
        ]
    
    async def on_ready(self):
        """봇이 로그인한 후 전체 메시지 수집 시작"""
        print(f'🎉 봇 로그인 성공: {self.user}')
        
        try:
            # 전체 메시지 수집 (필터링 없이)
            await self.collect_all_messages()
            # 키워드 분석 실행
            await self.analyze_keywords()
        except Exception as e:
            print(f"❌ 메시지 수집 중 오류: {e}")
        finally:
            # 수집 완료 후 봇 안전 종료
            print("🔌 봇 연결을 종료합니다...")
            await self.close()
    
    async def collect_all_messages(self):
        """6월 1일~7월 31일 모든 메시지 수집 (필터링 없이)"""
        print(f'\n📥 키워드 분석용 전체 메시지 수집을 시작합니다...')
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        
        # 6월 1일~7월 31일 설정
        start_date = datetime(2025, 6, 1, tzinfo=kst)
        end_date = datetime(2025, 8, 1, tzinfo=kst)  # 7월 31일까지
        
        print(f'📅 수집 기간: {start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")} (2개월)')
        print(f'🔍 필터링: 없음 (모든 메시지 수집)')
        print(f'🎯 목적: 실제 일정과 연관된 키워드 패턴 분석')
        
        total_messages = 0
        
        # 모든 서버의 모든 채널에서 메시지 수집
        for guild in self.guilds:
            print(f'\n🏢 서버: {guild.name}')
            
            for channel in guild.text_channels:
                try:
                    # 채널 접근 권한 확인
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    print(f'  📝 #{channel.name:20s} ', end='', flush=True)
                    
                    channel_count = 0
                    
                    # 지정 기간 메시지 가져오기 (모든 메시지)
                    async for message in channel.history(after=start_date, before=end_date, limit=None):
                        # 봇 메시지는 제외
                        if message.author.bot:
                            continue
                        
                        total_messages += 1
                        channel_count += 1
                        
                        # 메시지 정보 저장 (필터링 없이 모두)
                        message_data = {
                            'id': message.id,
                            'content': message.content.strip(),
                            'author': str(message.author),
                            'channel': f'#{message.channel.name}',
                            'guild': message.guild.name,
                            'created_at': message.created_at.astimezone(kst),
                            'date_str': message.created_at.astimezone(kst).strftime('%Y-%m-%d'),
                            'time_str': message.created_at.astimezone(kst).strftime('%H:%M'),
                            'message_length': len(message.content),
                            'has_mention': '@' in message.content,
                        }
                        self.all_messages.append(message_data)
                    
                    print(f'📊 {channel_count:4d}개 수집완료')
                    
                except discord.Forbidden:
                    print(f'❌ 접근 권한 없음')
                except Exception as e:
                    print(f'❌ 오류: {str(e)[:50]}...')
        
        print(f'\n📊 전체 메시지 수집 완료!')
        print(f'   📥 총 메시지: {total_messages:,}개 (6-7월 2개월)')
        print(f'   🎯 다음 단계: 실제 일정 날짜와 매칭 분석')
    
    async def analyze_keywords(self):
        """실제 일정 날짜와 메시지를 분석하여 키워드 추출"""
        print(f'\n🔬 키워드 분석을 시작합니다...')
        print('=' * 70)
        
        # 날짜별로 메시지 그룹핑
        messages_by_date = {}
        for msg in self.all_messages:
            date_str = msg['date_str']
            if date_str not in messages_by_date:
                messages_by_date[date_str] = []
            messages_by_date[date_str].append(msg)
        
        print(f'📅 분석 대상 날짜: {len(messages_by_date)}일')
        print(f'📊 실제 일정 날짜: {len(self.actual_schedule_dates)}일')
        
        # 실제 일정 날짜의 메시지들 분석
        schedule_related_messages = []
        
        for schedule_date in self.actual_schedule_dates:
            print(f'\n📅 {schedule_date} 분석 중...')
            
            # 해당 날짜와 전후 1일 메시지들 확인
            target_dates = [
                schedule_date,
                (datetime.fromisoformat(schedule_date) - timedelta(days=1)).strftime('%Y-%m-%d'),
                (datetime.fromisoformat(schedule_date) + timedelta(days=1)).strftime('%Y-%m-%d'),
            ]
            
            date_messages = []
            for target_date in target_dates:
                if target_date in messages_by_date:
                    date_messages.extend(messages_by_date[target_date])
            
            print(f'   📝 해당 기간 메시지: {len(date_messages)}개')
            
            # 일정명과 관련된 메시지 찾기
            relevant_messages = []
            for msg in date_messages:
                content_lower = msg['content'].lower()
                
                # 일정명 직접 매칭
                for schedule_name in self.actual_schedule_names:
                    if any(word in content_lower for word in schedule_name.lower().split()):
                        relevant_messages.append({
                            'message': msg,
                            'matched_schedule': schedule_name,
                            'match_reason': f'일정명 매칭: {schedule_name}'
                        })
                        break
                
                # 시간 관련 키워드가 있는 메시지들도 수집
                time_keywords = ['시', '분', '오전', '오후', '오늘', '내일', '언제', '몇시', '시간']
                if any(keyword in content_lower for keyword in time_keywords):
                    relevant_messages.append({
                        'message': msg,
                        'matched_schedule': '시간 관련',
                        'match_reason': '시간 키워드 포함'
                    })
            
            if relevant_messages:
                print(f'   🎯 관련 메시지: {len(relevant_messages)}개 발견')
                for rel_msg in relevant_messages[:3]:  # 상위 3개만 출력
                    print(f'      💬 "{rel_msg["message"]["content"][:50]}..." ({rel_msg["match_reason"]})')
                
                schedule_related_messages.extend(relevant_messages)
            else:
                print(f'   ⚠️  관련 메시지 없음')
        
        # 키워드 빈도 분석
        print(f'\n📊 키워드 빈도 분석...')
        print('=' * 70)
        
        word_frequency = {}
        bigram_frequency = {}
        
        for rel_msg in schedule_related_messages:
            content = rel_msg['message']['content'].lower()
            
            # 단어 단위 분석 (한글, 영어, 숫자만)
            words = re.findall(r'[가-힣a-z0-9]+', content)
            
            for word in words:
                if len(word) >= 2:  # 2글자 이상만
                    word_frequency[word] = word_frequency.get(word, 0) + 1
            
            # 2글자 조합 분석
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                bigram_frequency[bigram] = bigram_frequency.get(bigram, 0) + 1
        
        # 상위 키워드 출력
        print(f'🔥 상위 단일 키워드 (빈도순):')
        sorted_words = sorted(word_frequency.items(), key=lambda x: x[1], reverse=True)
        for i, (word, freq) in enumerate(sorted_words[:20]):
            print(f'   {i+1:2d}. {word:15s}: {freq:3d}회')
        
        print(f'\n🔥 상위 조합 키워드 (빈도순):')
        sorted_bigrams = sorted(bigram_frequency.items(), key=lambda x: x[1], reverse=True)
        for i, (bigram, freq) in enumerate(sorted_bigrams[:15]):
            print(f'   {i+1:2d}. "{bigram:20s}": {freq:3d}회')
        
        # 추천 키워드 생성
        print(f'\n💡 추천 필터링 키워드:')
        print('=' * 70)
        
        recommended_keywords = []
        
        # 빈도 기반 추천 (상위 키워드 중 일정 관련성 높은 것들)
        schedule_related_words = ['합주', '리허설', '연습', '콘서트', '공연', '라이트', '더스트', '현실']
        
        for word, freq in sorted_words[:30]:
            if (word in schedule_related_words or 
                freq >= 5 and any(s_word in word for s_word in schedule_related_words)):
                recommended_keywords.append(f"'{word}' ({freq}회)")
        
        print('✅ 고빈도 일정 관련 키워드:')
        for keyword in recommended_keywords[:10]:
            print(f'   • {keyword}')
        
        # 패턴 분석
        print(f'\n🔍 메시지 패턴 분석:')
        print('=' * 70)
        
        time_patterns = []
        for rel_msg in schedule_related_messages:
            content = rel_msg['message']['content']
            
            # 시간 패턴 찾기
            time_matches = re.findall(r'\d{1,2}시\s*\d{0,2}분?|\d{1,2}:\d{2}|오전|오후', content)
            if time_matches:
                time_patterns.extend(time_matches)
        
        # 시간 패턴 빈도
        time_pattern_freq = {}
        for pattern in time_patterns:
            time_pattern_freq[pattern] = time_pattern_freq.get(pattern, 0) + 1
        
        print('⏰ 발견된 시간 패턴:')
        for pattern, freq in sorted(time_pattern_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f'   • "{pattern}": {freq}회')
        
        # 결과 JSON 저장 (로컬 개발용)
        analysis_result = {
            'total_messages': len(self.all_messages),
            'schedule_related_messages': len(schedule_related_messages),
            'top_keywords': sorted_words[:30],
            'top_bigrams': sorted_bigrams[:20],
            'recommended_keywords': recommended_keywords,
            'time_patterns': list(time_pattern_freq.items()),
            'actual_schedule_dates': self.actual_schedule_dates
        }
        
        print(f'\n📋 키워드 분석 완료!')
        print(f'   📊 총 메시지: {len(self.all_messages):,}개')
        print(f'   🎯 일정 관련: {len(schedule_related_messages)}개')
        print(f'   🔥 추천 키워드: {len(recommended_keywords)}개')
        print(f'   ⏰ 시간 패턴: {len(time_pattern_freq)}개')

async def analyze_discord_keywords():
    """Discord 키워드 분석 메인 함수"""
    print("🔬 Discord 키워드 분석을 시작합니다...")
    print("=" * 70)
    print("🎯 목적: 실제 일정과 연관된 키워드 패턴 추출")
    print("📅 기간: 2025년 6월 1일 ~ 7월 31일 (2개월)")
    print("🔍 방식: 필터링 없이 모든 메시지 수집 후 분석")
    print("=" * 70)
    
    # 환경변수에서 Discord 토큰 가져오기
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ 오류: DISCORD_TOKEN이 설정되지 않았습니다!")
        return
    
    # 키워드 분석 수집기 실행
    collector = KeywordAnalysisCollector()
    
    try:
        await collector.start(token)
        print("✅ 키워드 분석 완료")
        
    except discord.LoginFailure:
        print("❌ 로그인 실패: Discord 토큰이 잘못되었습니다!")
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        
    finally:
        # 강제로 연결 종료
        try:
            if not collector.is_closed():
                await collector.close()
            print("🔌 Discord 연결이 안전하게 종료되었습니다.")
        except Exception as close_error:
            print(f"⚠️ 연결 종료 중 오류 (무시 가능): {close_error}")
        
        # 추가 대기 시간으로 완전한 정리 보장
        await asyncio.sleep(1)
