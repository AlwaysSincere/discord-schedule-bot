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
        """모든 메시지를 분석하여 키워드 추출 (False Negative 방지)"""
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
        print(f'📊 총 메시지: {len(self.all_messages):,}개')
        print(f'🎯 실제 일정 날짜: {len(self.actual_schedule_dates)}일')
        print(f'⚠️  False Negative 방지를 위해 모든 날짜 분석 (포괄적 접근)')
        
        # 모든 메시지를 대상으로 일정 관련 메시지 찾기
        schedule_related_messages = []
        total_dates = len(messages_by_date)
        processed_dates = 0
        
        print(f'\n📊 전체 메시지 분석 진행중...')
        
        for date_str, date_messages in messages_by_date.items():
            processed_dates += 1
            
            # 진행 상황 표시 (10% 단위로)
            progress = (processed_dates / total_dates) * 100
            if processed_dates % max(1, total_dates // 10) == 0 or processed_dates == total_dates:
                print(f'   📈 진행률: {progress:.1f}% ({processed_dates}/{total_dates}일) - {date_str}')
            
            # 실제 일정 날짜 여부 확인
            is_actual_schedule_date = date_str in self.actual_schedule_dates
            
            # 각 날짜의 메시지들 분석
            for msg in date_messages:
                content_lower = msg['content'].lower()
                
                # 일정명 직접 매칭 (핵심 키워드)
                matched_schedule = None
                for schedule_name in self.actual_schedule_names:
                    if any(word in content_lower for word in schedule_name.lower().split()):
                        matched_schedule = schedule_name
                        break
                
                # 더 광범위한 일정 관련 키워드 체크
                broad_schedule_keywords = [
                    '합주', '리허설', '연습', '콘서트', '공연', '라이트', '더스트',
                    '현실', '세팅', '사운드체크', '콜타임', '준비', '모임'
                ]
                
                has_schedule_keyword = any(keyword in content_lower for keyword in broad_schedule_keywords)
                
                # 시간 표현 더 정확하게 감지 (숫자+시 패턴)
                time_patterns = [
                    r'\d{1,2}시\s*\d{0,2}분?',  # "2시", "2시 30분"
                    r'\d{1,2}:\d{2}',           # "14:30"
                    r'오전|오후',                # "오전", "오후"
                ]
                
                has_time_pattern = any(re.search(pattern, content_lower) for pattern in time_patterns)
                
                # 날짜/시간 키워드
                time_keywords = ['오늘', '내일', '모레', '언제', '몇시', '시간', '이번주', '다음주']
                has_time_keyword = any(keyword in content_lower for keyword in time_keywords)
                
                # 일정 관련 메시지 판단 (더 포괄적)
                is_relevant = False
                match_reasons = []
                
                if matched_schedule:
                    is_relevant = True
                    match_reasons.append(f'일정명: {matched_schedule}')
                
                if has_schedule_keyword and (has_time_pattern or has_time_keyword):
                    is_relevant = True
                    match_reasons.append('일정키워드+시간표현')
                
                if has_schedule_keyword and is_actual_schedule_date:
                    is_relevant = True
                    match_reasons.append('일정키워드+실제일정일')
                
                # 관련 메시지로 분류
                if is_relevant:
                    schedule_related_messages.append({
                        'message': msg,
                        'matched_schedule': matched_schedule or '일반 일정',
                        'match_reasons': match_reasons,
                        'is_actual_schedule_date': is_actual_schedule_date,
                        'has_time_pattern': has_time_pattern,
                        'has_schedule_keyword': has_schedule_keyword
                    })
        
        print(f'\n✅ 전체 메시지 분석 완료!')
        print(f'   📊 일정 관련 메시지: {len(schedule_related_messages):,}개')
        print(f'   📈 전체 대비 비율: {(len(schedule_related_messages)/len(self.all_messages)*100):.2f}%')
        
        # 실제 일정 날짜 vs 기타 날짜 분석
        actual_date_messages = [msg for msg in schedule_related_messages if msg['is_actual_schedule_date']]
        other_date_messages = [msg for msg in schedule_related_messages if not msg['is_actual_schedule_date']]
        
        print(f'   🎯 실제 일정일 메시지: {len(actual_date_messages)}개')
        print(f'   📅 기타 날짜 메시지: {len(other_date_messages)}개 (False Negative 후보)')
        
        return schedule_related_messages
        
    async def analyze_keywords(self):
        """모든 메시지를 분석하여 키워드 추출 (간소화된 버전)"""
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
        print(f'📊 총 메시지: {len(self.all_messages):,}개')
        print(f'🎯 실제 일정 날짜: {len(self.actual_schedule_dates)}일')
        
        # 모든 메시지를 대상으로 일정 관련 메시지 찾기
        schedule_related_messages = []
        
        print(f'\n📊 전체 메시지 분석 중... (진행률 표시 없음 - 리소스 절약)')
        
        for date_str, date_messages in messages_by_date.items():
            # 실제 일정 날짜 여부 확인
            is_actual_schedule_date = date_str in self.actual_schedule_dates
            
            # 각 날짜의 메시지들 분석
            for msg in date_messages:
                content_lower = msg['content'].lower()
                
                # 일정명 직접 매칭 (핵심 키워드)
                matched_schedule = None
                for schedule_name in self.actual_schedule_names:
                    if any(word in content_lower for word in schedule_name.lower().split()):
                        matched_schedule = schedule_name
                        break
                
                # 더 광범위한 일정 관련 키워드 체크
                broad_schedule_keywords = [
                    '합주', '리허설', '연습', '콘서트', '공연', '라이트', '더스트',
                    '현실', '세팅', '사운드체크', '콜타임', '준비', '모임', '현합'
                ]
                
                has_schedule_keyword = any(keyword in content_lower for keyword in broad_schedule_keywords)
                
                # 시간 표현 더 정확하게 감지 (숫자+시 패턴)
                time_patterns = [
                    r'\d{1,2}시\s*\d{0,2}분?',  # "2시", "2시 30분"
                    r'\d{1,2}:\d{2}',           # "14:30"
                    r'오전|오후',                # "오전", "오후"
                ]
                
                has_time_pattern = any(re.search(pattern, content_lower) for pattern in time_patterns)
                
                # 날짜/시간 키워드
                time_keywords = ['오늘', '내일', '모레', '언제', '몇시', '시간', '이번주', '다음주']
                has_time_keyword = any(keyword in content_lower for keyword in time_keywords)
                
                # 일정 관련 메시지 판단
                is_relevant = False
                match_reasons = []
                
                if matched_schedule:
                    is_relevant = True
                    match_reasons.append(f'일정명: {matched_schedule}')
                
                if has_schedule_keyword and (has_time_pattern or has_time_keyword):
                    is_relevant = True
                    match_reasons.append('일정키워드+시간표현')
                
                if has_schedule_keyword and is_actual_schedule_date:
                    is_relevant = True
                    match_reasons.append('일정키워드+실제일정일')
                
                # 관련 메시지로 분류
                if is_relevant:
                    schedule_related_messages.append({
                        'message': msg,
                        'matched_schedule': matched_schedule or '일반 일정',
                        'match_reasons': match_reasons,
                        'is_actual_schedule_date': is_actual_schedule_date,
                        'has_time_pattern': has_time_pattern,
                        'has_schedule_keyword': has_schedule_keyword
                    })
        
        print(f'✅ 전체 메시지 분석 완료!')
        print(f'   📊 일정 관련 메시지: {len(schedule_related_messages):,}개')
        print(f'   📈 전체 대비 비율: {(len(schedule_related_messages)/len(self.all_messages)*100):.2f}%')
        
        # 실제 일정 날짜 vs 기타 날짜 분석
        actual_date_messages = [msg for msg in schedule_related_messages if msg['is_actual_schedule_date']]
        other_date_messages = [msg for msg in schedule_related_messages if not msg['is_actual_schedule_date']]
        
        print(f'   🎯 실제 일정일 메시지: {len(actual_date_messages)}개')
        print(f'   📅 기타 날짜 메시지: {len(other_date_messages)}개 (False Negative 후보)')
        
        # 키워드 빈도 분석 시작
        print(f'\n📊 키워드 빈도 분석 중...')
        print('=' * 70)
        
        # 실제 일정 관련 메시지들만 대상으로 키워드 추출
        print(f'🎯 실제 일정일 메시지 기준 키워드 분석: {len(actual_date_messages)}개')
        print(f'📅 기타 날짜 메시지 (비교용): {len(other_date_messages)}개')
        
        # 키워드 빈도 분석 함수
        def analyze_word_frequency(messages, group_name):
            word_frequency = {}
            bigram_frequency = {}
            
            for rel_msg in messages:
                content = rel_msg['message']['content'].lower()
                
                # 단어 단위 분석 (한글, 영어, 숫자만, 의미있는 단어만)
                words = re.findall(r'[가-힣a-z0-9]+', content)
                
                # 불용어 제거 (의미없는 단어들)
                stop_words = {
                    '그', '이', '저', '것', '수', '있', '는', '다', '하', '을', '를', '가', '에',
                    '와', '과', '도', '만', '까지', '부터', '으로', '로', '에서', '한테',
                    '더', '너무', '정말', '진짜', '완전', '좀', '잠깐', '근데', '그런데',
                    '아니', '네', '예', '응', '음', '어', '이제', '그냥', '일단', '하나',
                    '둘', '셋', '넷', '다섯', '여섯', '일곱', '여덟', '아홉', '열', '혹시',
                    '미르님', '제가', '근데', '역시', '여러분', '하는', '1325513395893702708'
                }
                
                for word in words:
                    if len(word) >= 2 and word not in stop_words:  # 2글자 이상, 불용어 제외
                        word_frequency[word] = word_frequency.get(word, 0) + 1
                
                # 2글자 조합 분석 (의미있는 조합만)
                for i in range(len(words) - 1):
                    if words[i] not in stop_words and words[i+1] not in stop_words:
                        bigram = f"{words[i]} {words[i+1]}"
                        if len(bigram) >= 5:  # 너무 짧은 조합 제외
                            bigram_frequency[bigram] = bigram_frequency.get(bigram, 0) + 1
            
            return word_frequency, bigram_frequency
        
        # 실제 일정일 메시지 분석
        actual_words, actual_bigrams = analyze_word_frequency(actual_date_messages, "실제 일정일")
        
        # 기타 날짜 메시지 분석 (비교용)
        other_words, other_bigrams = analyze_word_frequency(other_date_messages, "기타 날짜")
        
        # 결과 출력
        print(f'\n🔥 실제 일정일 상위 키워드 (빈도순):')
        sorted_actual_words = sorted(actual_words.items(), key=lambda x: x[1], reverse=True)
        for i, (word, freq) in enumerate(sorted_actual_words[:25]):
            # 기타 날짜에서의 빈도와 비교
            other_freq = other_words.get(word, 0)
            ratio = freq / max(other_freq, 1)
            print(f'   {i+1:2d}. {word:15s}: {freq:3d}회 (기타: {other_freq:3d}회, 비율: {ratio:.1f}x)')
        
        print(f'\n🔥 실제 일정일 상위 조합 키워드:')
        sorted_actual_bigrams = sorted(actual_bigrams.items(), key=lambda x: x[1], reverse=True)
        for i, (bigram, freq) in enumerate(sorted_actual_bigrams[:15]):
            other_freq = other_bigrams.get(bigram, 0)
            print(f'   {i+1:2d}. "{bigram:25s}": {freq:2d}회 (기타: {other_freq}회)')
        
        # 실제 일정일에만 높은 빈도로 나타나는 키워드 추출
        high_precision_keywords = []
        for word, freq in sorted_actual_words:
            if freq >= 5:  # 최소 5회 이상
                other_freq = other_words.get(word, 0)
                ratio = freq / max(other_freq, 1)
                if ratio >= 2.0:  # 실제 일정일에서 2배 이상 많이 나타남
                    high_precision_keywords.append((word, freq, ratio))
        
        print(f'\n💎 고정밀도 일정 키워드 (실제 일정일 특화):')
        for i, (word, freq, ratio) in enumerate(high_precision_keywords[:15]):
            print(f'   {i+1:2d}. "{word}" - {freq}회, {ratio:.1f}배 차이')
        
        # 최종 추천 키워드 생성
        print(f'\n💡 최종 추천 필터링 키워드:')
        print('=' * 70)
        
        # 기존 분석 결과와 새로운 고정밀도 키워드 결합
        final_keywords = []
        
        # 1. 고빈도 + 고정밀도 키워드
        for word, freq, ratio in high_precision_keywords:
            if freq >= 10:  # 충분한 빈도
                final_keywords.append(f"'{word}' (빈도:{freq}, 정확도:{ratio:.1f}배)")
        
        # 2. 기본 일정 키워드 (항상 포함)
        core_keywords = ['합주', '리허설', '연습', '콘서트', '공연', '라이트', '더스트', '현실', '현합']
        for keyword in core_keywords:
            if keyword in actual_words and actual_words[keyword] >= 5:
                freq = actual_words[keyword]
                final_keywords.append(f"'{keyword}' (핵심키워드:{freq}회)")
        
        print('✅ 최종 추천 키워드:')
        for i, keyword in enumerate(final_keywords[:12]):  # 상위 12개
            print(f'   {i+1:2d}. {keyword}')
        
        # 시간 패턴 분석
        print(f'\n🔍 시간 패턴 분석:')
        print('=' * 70)
        
        time_patterns = []
        time_context_messages = []
        
        for rel_msg in schedule_related_messages:
            content = rel_msg['message']['content']
            content_lower = content.lower()
            
            # 더 정확한 시간 패턴 찾기 (숫자와 함께)
            precise_time_patterns = [
                r'\d{1,2}시\s*\d{0,2}분?',  # "2시", "2시 30분", "14시 20분"
                r'\d{1,2}:\d{2}',           # "14:30", "9:15"
                r'오전\s*\d{1,2}시?',       # "오전 9시", "오전 9"
                r'오후\s*\d{1,2}시?',       # "오후 3시", "오후 3"
                r'\d{1,2}시\s*반',          # "2시 반"
                r'\d{1,2}시경',             # "3시경"
            ]
            
            found_patterns = []
            for pattern in precise_time_patterns:
                matches = re.findall(pattern, content_lower)
                found_patterns.extend(matches)
            
            if found_patterns:
                time_patterns.extend(found_patterns)
                time_context_messages.append({
                    'message': rel_msg['message'],
                    'patterns': found_patterns,
                    'is_actual_date': rel_msg['is_actual_schedule_date']
                })
        
        # 시간 패턴 빈도 분석
        time_pattern_freq = {}
        for pattern in time_patterns:
            # 패턴 정규화 (예: "9시", "09시" -> "9시")
            normalized = re.sub(r'0(\d)', r'\1', pattern)
            time_pattern_freq[normalized] = time_pattern_freq.get(normalized, 0) + 1
        
        print('⏰ 발견된 정확한 시간 패턴:')
        sorted_time_patterns = sorted(time_pattern_freq.items(), key=lambda x: x[1], reverse=True)
        for i, (pattern, freq) in enumerate(sorted_time_patterns[:15]):
            print(f'   {i+1:2d}. "{pattern}": {freq}회')
        
        # 시간이 언급된 메시지 샘플 출력
        print(f'\n⏰ 시간 패턴이 포함된 메시지 샘플:')
        actual_time_msgs = [msg for msg in time_context_messages if msg['is_actual_date']][:5]
        other_time_msgs = [msg for msg in time_context_messages if not msg['is_actual_date']][:3]
        
        print(f'   🎯 실제 일정일 메시지 ({len(actual_time_msgs)}개 샘플):')
        for i, msg in enumerate(actual_time_msgs):
            content = msg['message']['content'][:60]
            patterns = ', '.join(msg['patterns'])
            print(f'      {i+1}. "{content}..." → [{patterns}]')
        
        print(f'   📅 기타 날짜 메시지 ({len(other_time_msgs)}개 샘플):')
        for i, msg in enumerate(other_time_msgs):
            content = msg['message']['content'][:60]
            patterns = ', '.join(msg['patterns'])
            print(f'      {i+1}. "{content}..." → [{patterns}]')
        
        # 최종 분석 결과 요약
        print(f'\n📋 키워드 분석 최종 요약:')
        print('=' * 70)
        print(f'   📊 총 메시지: {len(self.all_messages):,}개 (2개월)')
        print(f'   🎯 일정 관련 메시지: {len(schedule_related_messages):,}개')
        print(f'   📅 실제 일정일 메시지: {len(actual_date_messages)}개')
        print(f'   📅 기타 날짜 메시지: {len(other_date_messages)}개 (False Negative 후보)')
        print(f'   🔥 고정밀도 키워드: {len(high_precision_keywords)}개')
        print(f'   ⏰ 정확한 시간 패턴: {len(time_pattern_freq)}개')
        print(f'   💎 최종 추천 키워드: {len(final_keywords)}개')
        
        # 개선 제안
        print(f'\n💡 다음 단계 제안:')
        print('=' * 70)
        print('1. 🎯 위 "최종 추천 키워드"를 기존 필터링에 적용')
        print('2. 📅 "기타 날짜 메시지"를 검토하여 놓친 일정 확인')
        print('3. 🔧 시간 패턴을 활용한 정확도 개선')
        print('4. 🧪 개선된 필터링으로 소규모 테스트')
        print('5. 🚀 최종 시스템으로 전면 테스트')
        
        return schedule_related_messages
        
        # 시간 패턴 분석 (개선된 정확도)
        print(f'\n🔍 시간 패턴 분석 (정확도 개선):')
        print('=' * 70)
        
        time_patterns = []
        time_context_messages = []
        
        for rel_msg in schedule_related_messages:
            content = rel_msg['message']['content']
            content_lower = content.lower()
            
            # 더 정확한 시간 패턴 찾기 (숫자와 함께)
            precise_time_patterns = [
                r'\d{1,2}시\s*\d{0,2}분?',  # "2시", "2시 30분", "14시 20분"
                r'\d{1,2}:\d{2}',           # "14:30", "9:15"
                r'오전\s*\d{1,2}시?',       # "오전 9시", "오전 9"
                r'오후\s*\d{1,2}시?',       # "오후 3시", "오후 3"
                r'\d{1,2}시\s*반',          # "2시 반"
                r'\d{1,2}시경',             # "3시경"
            ]
            
            found_patterns = []
            for pattern in precise_time_patterns:
                matches = re.findall(pattern, content_lower)
                found_patterns.extend(matches)
            
            if found_patterns:
                time_patterns.extend(found_patterns)
                time_context_messages.append({
                    'message': rel_msg['message'],
                    'patterns': found_patterns,
                    'is_actual_date': rel_msg['is_actual_schedule_date']
                })
        
        # 시간 패턴 빈도 분석
        time_pattern_freq = {}
        for pattern in time_patterns:
            # 패턴 정규화 (예: "9시", "09시" -> "9시")
            normalized = re.sub(r'0(\d)', r'\1', pattern)
            time_pattern_freq[normalized] = time_pattern_freq.get(normalized, 0) + 1
        
        print('⏰ 발견된 정확한 시간 패턴:')
        sorted_time_patterns = sorted(time_pattern_freq.items(), key=lambda x: x[1], reverse=True)
        for i, (pattern, freq) in enumerate(sorted_time_patterns[:15]):
            print(f'   {i+1:2d}. "{pattern}": {freq}회')
        
        # 시간이 언급된 메시지 샘플 출력
        print(f'\n⏰ 시간 패턴이 포함된 메시지 샘플:')
        actual_time_msgs = [msg for msg in time_context_messages if msg['is_actual_date']][:5]
        other_time_msgs = [msg for msg in time_context_messages if not msg['is_actual_date']][:3]
        
        print(f'   🎯 실제 일정일 메시지 ({len(actual_time_msgs)}개 샘플):')
        for i, msg in enumerate(actual_time_msgs):
            content = msg['message']['content'][:60]
            patterns = ', '.join(msg['patterns'])
            print(f'      {i+1}. "{content}..." → [{patterns}]')
        
        print(f'   📅 기타 날짜 메시지 ({len(other_time_msgs)}개 샘플):')
        for i, msg in enumerate(other_time_msgs):
            content = msg['message']['content'][:60]
            patterns = ', '.join(msg['patterns'])
            print(f'      {i+1}. "{content}..." → [{patterns}]')
        
        # 최종 분석 결과 요약
        print(f'\n📋 키워드 분석 최종 요약:')
        print('=' * 70)
        print(f'   📊 총 메시지: {len(self.all_messages):,}개 (2개월)')
        print(f'   🎯 일정 관련 메시지: {len(schedule_related_messages):,}개')
        print(f'   📅 실제 일정일 메시지: {len(actual_schedule_messages)}개')
        print(f'   📅 기타 날짜 메시지: {len(other_messages)}개 (False Negative 후보)')
        print(f'   🔥 고정밀도 키워드: {len(high_precision_keywords)}개')
        print(f'   ⏰ 정확한 시간 패턴: {len(time_pattern_freq)}개')
        print(f'   💎 최종 추천 키워드: {len(final_keywords)}개')
        
        # 개선 제안
        print(f'\n💡 다음 단계 제안:')
        print('=' * 70)
        print('1. 🎯 위 "최종 추천 키워드"를 기존 필터링에 적용')
        print('2. 📅 "기타 날짜 메시지"를 검토하여 놓친 일정 확인')
        print('3. 🔧 시간 패턴을 활용한 정확도 개선')
        print('4. 🧪 개선된 필터링으로 소규모 테스트')
        print('5. 🚀 최종 시스템으로 전면 테스트')
        
        return schedule_related_messages

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
