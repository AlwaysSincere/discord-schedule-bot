import discord
import os
import asyncio
from datetime import datetime, timedelta
import pytz
import re

class ManualTestCollector(discord.Client):
    def __init__(self):
        # Discord 봇 초기화
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용 읽기 권한
        intents.guilds = True           # 서버 정보 접근 권한
        super().__init__(intents=intents)
        
        # 필터링된 메시지를 저장할 리스트
        self.filtered_messages = []
        
        # 데이터 기반 키워드 (분석 결과)
        self.data_based_keywords = {
            # 최고 효율 키워드 (정확도 7배 이상)
            'high_precision': ['합니다', '그래서', '공연', '연습', '세팅'],
            
            # 핵심 일정 키워드 (높은 빈도)
            'core_schedule': ['합주', '리허설', '콘서트', '라이트', '더스트', '현합'],
            
            # 시간 관련 키워드
            'time_related': ['오늘', '내일', '이번', '언제', '몇시', '시간'],
            
            # 보조 키워드 (낮은 우선순위)
            'support': ['저희', 'mtr', '우리', 'everyone', '같습니다', '끝나고']
        }
        
        # 실제 일정 날짜들 (검증용)
        self.actual_schedule_dates = [
            '2025-06-03', '2025-06-04', '2025-06-10', '2025-06-11',
            '2025-06-17', '2025-06-18', '2025-06-20', '2025-06-25', 
            '2025-06-26', '2025-06-29', '2025-06-30', '2025-07-01',
            '2025-07-02', '2025-07-08', '2025-07-09', '2025-07-11',
            '2025-07-15', '2025-07-16', '2025-07-18', '2025-07-22',
            '2025-07-23', '2025-07-25', '2025-07-29', '2025-07-30',
            '2025-08-01', '2025-08-08', '2025-08-09'
        ]
    
    async def on_ready(self):
        """봇이 로그인한 후 메시지 수집 시작"""
        print(f'🎉 봇 로그인 성공: {self.user}')
        
        try:
            # 6개월 메시지 수집 및 필터링
            await self.collect_and_filter_messages()
        except Exception as e:
            print(f"❌ 메시지 수집 중 오류: {e}")
        finally:
            # 수집 완료 후 봇 안전 종료
            print("🔌 봇 연결을 종료합니다...")
            await self.close()
    
    def evaluate_message_with_data_keywords(self, message_text):
        """데이터 기반 키워드로 메시지 평가"""
        text = message_text.lower()
        
        # 스코어링 시스템
        score = 0
        matched_keywords = []
        match_reasons = []
        
        # 최고 효율 키워드 (가중치 높음)
        for keyword in self.data_based_keywords['high_precision']:
            if keyword in text:
                score += 10
                matched_keywords.append(f"고효율:{keyword}")
                match_reasons.append(f"고효율키워드 '{keyword}' (10점)")
        
        # 핵심 일정 키워드
        for keyword in self.data_based_keywords['core_schedule']:
            if keyword in text:
                score += 5
                matched_keywords.append(f"핵심:{keyword}")
                match_reasons.append(f"핵심키워드 '{keyword}' (5점)")
        
        # 시간 관련 키워드
        time_found = []
        for keyword in self.data_based_keywords['time_related']:
            if keyword in text:
                time_found.append(keyword)
        
        if time_found:
            score += 3 * len(time_found)
            matched_keywords.extend([f"시간:{kw}" for kw in time_found])
            match_reasons.append(f"시간키워드 {time_found} ({3*len(time_found)}점)")
        
        # 보조 키워드
        for keyword in self.data_based_keywords['support']:
            if keyword in text:
                score += 1
                matched_keywords.append(f"보조:{keyword}")
                match_reasons.append(f"보조키워드 '{keyword}' (1점)")
        
        # 시간 패턴 보너스 (숫자+시)
        time_patterns = re.findall(r'\d{1,2}시\s*\d{0,2}분?|\d{1,2}:\d{2}', text)
        if time_patterns:
            score += 5
            matched_keywords.append(f"시간패턴:{time_patterns}")
            match_reasons.append(f"시간패턴 {time_patterns} (5점)")
        
        # 필터링 기준: 8점 이상 (데이터 기반 최적화)
        is_schedule = score >= 8
        
        return is_schedule, score, matched_keywords, match_reasons
    
    async def collect_and_filter_messages(self):
        """2월~7월 6개월간 메시지 수집 및 데이터 기반 필터링"""
        print(f'\n📥 6개월 데이터 기반 필터링 테스트를 시작합니다...')
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        
        # 2월 1일~7월 31일 설정 (6개월)
        start_date = datetime(2025, 2, 1, tzinfo=kst)
        end_date = datetime(2025, 8, 1, tzinfo=kst)  # 7월 31일까지
        
        print(f'📅 테스트 기간: {start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")} (6개월)')
        print(f'🔍 필터링: 데이터 기반 키워드 (26개 + 현합)')
        print(f'🎯 목적: 실제 정확도 수동 검증')
        print('=' * 70)
        
        # 키워드 정보 출력
        print('🔥 사용될 데이터 기반 키워드:')
        print(f'   고효율 (10점): {self.data_based_keywords["high_precision"]}')
        print(f'   핵심 (5점): {self.data_based_keywords["core_schedule"]}')
        print(f'   시간 (3점): {self.data_based_keywords["time_related"]}')
        print(f'   보조 (1점): {self.data_based_keywords["support"]}')
        print(f'   시간패턴 (+5점): 숫자+시 패턴')
        print(f'   📊 필터링 기준: 8점 이상')
        print('=' * 70)
        
        total_messages = 0
        filtered_count = 0
        
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
                    channel_filtered = 0
                    
                    # 지정 기간 메시지 가져오기
                    async for message in channel.history(after=start_date, before=end_date, limit=None):
                        # 봇 메시지는 제외
                        if message.author.bot:
                            continue
                        
                        total_messages += 1
                        channel_count += 1
                        
                        # 데이터 기반 키워드로 필터링
                        is_schedule, score, matched_keywords, match_reasons = self.evaluate_message_with_data_keywords(message.content)
                        
                        if is_schedule:
                            filtered_count += 1
                            channel_filtered += 1
                            
                            # 실제 일정 날짜인지 확인
                            msg_date = message.created_at.astimezone(kst).strftime('%Y-%m-%d')
                            is_actual_schedule_date = msg_date in self.actual_schedule_dates
                            
                            # 메시지 정보 저장 (수동 검증용)
                            message_data = {
                                'id': message.id,
                                'content': message.content.strip(),
                                'author': str(message.author),
                                'channel': f'#{message.channel.name}',
                                'created_at': message.created_at.astimezone(kst),
                                'date_str': msg_date,
                                'score': score,
                                'matched_keywords': matched_keywords,
                                'match_reasons': match_reasons,
                                'is_actual_schedule_date': is_actual_schedule_date,
                                'message_length': len(message.content)
                            }
                            self.filtered_messages.append(message_data)
                    
                    # 진행률 출력
                    filter_rate = f"{(channel_filtered/channel_count*100):.1f}%" if channel_count > 0 else "0%"
                    print(f'📊 {channel_count:4d}개 → {channel_filtered:3d}개 ({filter_rate})')
                    
                except discord.Forbidden:
                    print(f'❌ 접근 권한 없음')
                except Exception as e:
                    print(f'❌ 오류: {str(e)[:50]}...')
        
        # 수집 결과 출력
        print(f'\n📊 6개월 데이터 기반 필터링 완료!')
        print('=' * 70)
        print(f'   📥 전체 메시지: {total_messages:,}개 (6개월)')
        print(f'   🔍 필터링된 메시지: {filtered_count:,}개')
        print(f'   📈 필터링 비율: {(filtered_count/total_messages*100):.2f}%' if total_messages > 0 else '   비율: 0%')
        
        # 수동 검증용 결과 분석
        await self.analyze_for_manual_verification()
    
    async def analyze_for_manual_verification(self):
        """수동 검증을 위한 결과 분석 및 출력"""
        print(f'\n📋 수동 검증용 분석 결과:')
        print('=' * 70)
        
        if not self.filtered_messages:
            print("❌ 필터링된 메시지가 없습니다.")
            return
        
        # 실제 일정 날짜 vs 기타 날짜 분류
        actual_date_messages = [msg for msg in self.filtered_messages if msg['is_actual_schedule_date']]
        other_date_messages = [msg for msg in self.filtered_messages if not msg['is_actual_schedule_date']]
        
        print(f'🎯 실제 일정일에 필터링된 메시지: {len(actual_date_messages)}개 (True Positive 후보)')
        print(f'📅 기타 날짜에 필터링된 메시지: {len(other_date_messages)}개 (False Positive 후보)')
        
        # 점수별 분포
        score_distribution = {}
        for msg in self.filtered_messages:
            score_range = f"{(msg['score']//5)*5}-{(msg['score']//5)*5+4}점"
            score_distribution[score_range] = score_distribution.get(score_range, 0) + 1
        
        print(f'\n📊 점수별 분포:')
        for score_range, count in sorted(score_distribution.items()):
            print(f'   {score_range}: {count}개')
        
        # 수동 검증용 샘플 출력 (실제 일정일)
        print(f'\n🎯 실제 일정일 샘플 (수동 검증용) - 상위 10개:')
        print('-' * 70)
        
        # 점수 높은 순으로 정렬
        actual_sorted = sorted(actual_date_messages, key=lambda x: x['score'], reverse=True)
        
        for i, msg in enumerate(actual_sorted[:10]):
            print(f'\n{i+1:2d}. [점수: {msg["score"]:2d}점] {msg["date_str"]} {msg["channel"]:12s}')
            print(f'    작성자: {msg["author"]:15s}')
            print(f'    내용: "{msg["content"][:100]}..."')
            print(f'    키워드: {", ".join(msg["matched_keywords"])[:80]}...')
            print(f'    ✅ 실제 일정일: {msg["is_actual_schedule_date"]}')
        
        # False Positive 후보 출력
        print(f'\n📅 False Positive 후보 (기타 날짜) - 상위 10개:')
        print('-' * 70)
        
        other_sorted = sorted(other_date_messages, key=lambda x: x['score'], reverse=True)
        
        for i, msg in enumerate(other_sorted[:10]):
            print(f'\n{i+1:2d}. [점수: {msg["score"]:2d}점] {msg["date_str"]} {msg["channel"]:12s}')
            print(f'    작성자: {msg["author"]:15s}')
            print(f'    내용: "{msg["content"][:100]}..."')
            print(f'    키워드: {", ".join(msg["matched_keywords"])[:80]}...')
            print(f'    ❓ 실제 일정일: {msg["is_actual_schedule_date"]}')
        
        # 키워드별 성능 분석
        print(f'\n🔍 키워드별 성능 분석:')
        print('-' * 70)
        
        keyword_stats = {}
        for msg in self.filtered_messages:
            for keyword in msg['matched_keywords']:
                if keyword not in keyword_stats:
                    keyword_stats[keyword] = {'total': 0, 'actual_date': 0}
                keyword_stats[keyword]['total'] += 1
                if msg['is_actual_schedule_date']:
                    keyword_stats[keyword]['actual_date'] += 1
        
        # 정확도 기준으로 정렬
        sorted_keywords = sorted(keyword_stats.items(), 
                               key=lambda x: x[1]['actual_date']/x[1]['total'] if x[1]['total'] > 0 else 0, 
                               reverse=True)
        
        print('키워드별 정확도 (실제 일정일 비율):')
        for keyword, stats in sorted_keywords[:15]:
            accuracy = stats['actual_date'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f'   {keyword:20s}: {accuracy:5.1f}% ({stats["actual_date"]}/{stats["total"]})')
        
        # 수동 검증 가이드
        print(f'\n💡 수동 검증 가이드:')
        print('=' * 70)
        print('1. 🎯 "실제 일정일 샘플"을 확인하여 True Positive 비율 계산')
        print('2. 📅 "False Positive 후보"를 확인하여 실제 오분류 파악') 
        print('3. 🔍 키워드별 정확도를 보고 개선점 찾기')
        print('4. 📊 전체적으로 만족스러우면 AI 단계로 진행')
        print('5. 🛠️  개선이 필요하면 점수 기준이나 키워드 조정')

async def test_data_based_filtering():
    """데이터 기반 필터링 테스트 메인 함수"""
    print("🧪 데이터 기반 필터링 정확도 테스트를 시작합니다...")
    print("=" * 70)
    print("🎯 목적: 6개월 데이터로 수동 검증하여 필터링 정확도 확인")
    print("📅 기간: 2025년 2월 1일 ~ 7월 31일 (6개월)")
    print("🔍 방식: 데이터 분석 결과 키워드 + 점수 시스템")
    print("📊 검증: 실제 일정 날짜와 비교하여 정확도 측정")
    print("=" * 70)
    
    # 환경변수에서 Discord 토큰 가져오기
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ 오류: DISCORD_TOKEN이 설정되지 않았습니다!")
        return
    
    # 테스트 수집기 실행
    collector = ManualTestCollector()
    
    try:
        await collector.start(token)
        print("✅ 데이터 기반 필터링 테스트 완료")
        
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
