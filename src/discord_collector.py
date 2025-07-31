import discord
import os
import asyncio
from datetime import datetime, timedelta
import pytz
import re

class MessageCollector(discord.Client):
    def __init__(self):
        # Discord 봇 초기화
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용 읽기 권한
        intents.guilds = True           # 서버 정보 접근 권한
        super().__init__(intents=intents)
        
        # 수집된 메시지를 저장할 리스트
        self.collected_messages = []
    
    async def on_ready(self):
        """봇이 로그인한 후 메시지 수집 시작"""
        print(f'🎉 봇 로그인 성공: {self.user}')
        
        try:
            # 메시지 수집 실행
            await self.collect_recent_messages()
        except Exception as e:
            print(f"❌ 메시지 수집 중 오류: {e}")
        finally:
            # 수집 완료 후 봇 안전 종료
            print("🔌 봇 연결을 종료합니다...")
            await self.close()
    
    def is_likely_schedule(self, message_text):
        """메시지가 일정일 가능성을 더 정교하게 판단하는 함수"""
        text = message_text.lower()
        
        # 명확히 일정이 아닌 패턴들 (강력한 제외 기준)
        exclude_patterns = [
            r'어제.*?어땠',     # "어제 연습 어땠어"
            r'지난번.*?어땠',   # "지난번 공연 어땠어"
            r'.*?었어$',        # "~했었어", "좋았어"
            r'.*?했어$',        # "연습했어", "끝났어"
            r'.*?어떻게\s*생각', # "어떻게 생각해"
            r'.*?녹음.*?있',    # "녹음된 거 있어?"
            r'.*?영상.*?봤',    # "영상 봤어?"
            r'점심.*?뭐.*?먹',  # "점심 뭐 먹을까"
            r'날씨.*?좋',       # "날씨 좋네"
            r'고생.*?했',       # "고생했어"
            r'수고.*?했',       # "수고했어"
        ]
        
        # 제외 패턴에 걸리면 일정이 아님
        for pattern in exclude_patterns:
            if re.search(pattern, text):
                return False, f"제외패턴: {pattern}"
        
        # 강력한 일정 시그널 (이것들이 있으면 거의 확실히 일정)
        strong_schedule_signals = [
            r'\d{1,2}시\s*\d{1,2}분',     # "2시 20분"
            r'오늘.*?\d{1,2}시',           # "오늘 3시"
            r'내일.*?\d{1,2}시',           # "내일 8시"
            r'콜타임',                     # "콜타임입니다"
            r'세팅.*?완료',                 # "세팅 완료"
            r'오전.*?\d{1,2}시',           # "오전 9시"
            r'오후.*?\d{1,2}시',           # "오후 3시"
        ]
        
        for pattern in strong_schedule_signals:
            if re.search(pattern, text):
                return True, f"강력시그널: {pattern}"
        
        # 중간 강도 일정 시그널들 (다른 조건과 함께 고려)
        medium_schedule_signals = [
            r'언제.*?할까',    # "언제 할까"
            r'몇시.*?가능',    # "몇시 가능"
            r'시간.*?어때',    # "시간 어때"
            r'만날까',         # "만날까"
            r'가자',           # "가자"
            r'하자',           # "하자"
            r'어때요?',        # "어때요?"
            r'괜찮나요?',      # "괜찮나요?"
        ]
        
        medium_signals_found = []
        for pattern in medium_schedule_signals:
            if re.search(pattern, text):
                medium_signals_found.append(pattern)
        
        # 핵심 키워드 (음악 동아리 특화)
        core_keywords = ['합주', '리허설', '연습', '공연', '콘서트', '세팅', '사운드체크']
        core_found = [kw for kw in core_keywords if kw in text]
        
        # 시간 표현 키워드
        time_keywords = ['오늘', '내일', '모레', '이번주', '다음주', '언제', '몇시', '시간']
        time_found = [kw for kw in time_keywords if kw in text]
        
        # 장소 키워드
        place_keywords = ['연습실', '스튜디오', '공연장']
        place_found = [kw for kw in place_keywords if kw in text]
        
        # 종합 판단
        score = 0
        reasons = []
        
        # 강력한 시그널이 있으면 이미 True로 반환됨
        
        # 핵심 키워드 점수
        if core_found:
            score += len(core_found) * 3
            reasons.append(f"핵심키워드: {core_found}")
        
        # 시간 표현 점수
        if time_found:
            score += len(time_found) * 2
            reasons.append(f"시간표현: {time_found}")
        
        # 중간 시그널 점수
        if medium_signals_found:
            score += len(medium_signals_found) * 2
            reasons.append(f"일정시그널: {medium_signals_found}")
        
        # 장소 키워드 점수
        if place_found:
            score += len(place_found) * 1
            reasons.append(f"장소: {place_found}")
        
        # 점수 기반 판단 (더 엄격하게)
        if score >= 4:
            return True, f"점수:{score} " + ", ".join(reasons)
        else:
            return False, f"점수부족:{score} " + ", ".join(reasons) if reasons else "키워드없음"
    
    async def collect_recent_messages(self):
        """최근 60일간 메시지 수집 (2달 대용량 테스트)"""
        print(f'\n📥 메시지 수집을 시작합니다...')
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        sixty_days_ago = now - timedelta(days=60)  # 60일 전부터 수집 (2달)
        
        print(f'📅 수집 기간: {sixty_days_ago.strftime("%Y-%m-%d %H:%M")} ~ {now.strftime("%Y-%m-%d %H:%M")} (한국시간)')
        print(f'📊 수집 범위: 최근 60일간 (2달 대용량 테스트)')
        print(f'⚠️  대용량 데이터 처리 - 처리 시간 10-15분 예상')
        
        total_messages = 0
        filtered_messages = 0
        channel_progress = {}
        
        # 모든 서버의 모든 채널에서 메시지 수집
        for guild in self.guilds:
            print(f'\n🏢 서버: {guild.name}')
            
            # 채널별 진행률 추적
            total_channels = len([ch for ch in guild.text_channels if ch.permissions_for(guild.me).read_message_history])
            current_channel = 0
            
            for channel in guild.text_channels:
                try:
                    # 채널 접근 권한 확인
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    current_channel += 1
                    print(f'  📝 [{current_channel:2d}/{total_channels:2d}] #{channel.name:20s} ', end='', flush=True)
                    
                    channel_count = 0
                    channel_filtered = 0
                    
                    # 최근 60일간 메시지 가져오기 (대용량)
                    message_batch = []
                    async for message in channel.history(after=sixty_days_ago, limit=None):
                        total_messages += 1
                        channel_count += 1
                        
                        # 봇 메시지는 제외
                        if message.author.bot:
                            continue
                        
                        # 배치 처리를 위해 임시 저장
                        message_batch.append(message)
                        
                        # 1000개씩 배치 처리 (메모리 효율성)
                        if len(message_batch) >= 1000:
                            batch_filtered = self.process_message_batch_improved(message_batch, kst)
                            channel_filtered += batch_filtered
                            filtered_messages += batch_filtered
                            message_batch = []
                    
                    # 남은 메시지들 처리
                    if message_batch:
                        batch_filtered = self.process_message_batch_improved(message_batch, kst)
                        channel_filtered += batch_filtered
                        filtered_messages += batch_filtered
                    
                    # 진행률 출력
                    filter_rate = f"{(channel_filtered/channel_count*100):.1f}%" if channel_count > 0 else "0%"
                    print(f'📊 {channel_count:4d}개 → {channel_filtered:3d}개 ({filter_rate})')
                    
                    channel_progress[channel.name] = {
                        'total': channel_count,
                        'filtered': channel_filtered
                    }
                    
                except discord.Forbidden:
                    print(f'❌ 접근 권한 없음')
                except Exception as e:
                    print(f'❌ 오류: {str(e)[:50]}...')
        
        # 수집 결과 요약
        print(f'\n📊 60일간 메시지 수집 완료!')
        print(f'   📥 전체 메시지: {total_messages:,}개')
        print(f'   🔍 필터링된 메시지: {filtered_messages:,}개')
        print(f'   📈 필터링 비율: {(filtered_messages/total_messages*100):.2f}%' if total_messages > 0 else '   비율: 0%')
        print(f'   🎯 AI 분석 예상 비용: 약 {((filtered_messages + 14) // 15 * 5):,}원')
        print(f'   ⏱️  예상 처리 시간: 약 {((filtered_messages + 14) // 15 * 1.5 / 60):.1f}분')
        
        # 데이터량 경고
        if filtered_messages > 300:
            print(f'\n⚠️  대용량 데이터 감지!')
            print(f'   📊 필터링된 메시지: {filtered_messages:,}개')
            print(f'   💰 예상 AI 분석 비용: {((filtered_messages + 14) // 15 * 5):,}원')
            print(f'   ⏱️  예상 처리 시간: {((filtered_messages + 14) // 15 * 1.5 / 60):.1f}분')
            print(f'   🎯 2달 데이터로 더 정확한 패턴 분석 가능!')
        
        # 상위 채널별 통계
        print(f'\n📊 채널별 상위 10개:')
        sorted_channels = sorted(channel_progress.items(), key=lambda x: x[1]['filtered'], reverse=True)
        for i, (channel_name, stats) in enumerate(sorted_channels[:10]):
            rate = f"{(stats['filtered']/stats['total']*100):.1f}%" if stats['total'] > 0 else "0%"
            print(f'   {i+1:2d}. #{channel_name:20s}: {stats["filtered"]:3d}개 ({rate})')
        
        # 맥락 묶기 처리
        if self.collected_messages:
            self.group_context_messages()
            
            # 키워드 분석 모드에서는 상세 분석 출력
            print(f'\n📈 개선된 필터링 완료!')
            print(f'   🎯 AI 분석 대상: {len(self.collected_messages)}개 맥락 그룹')
            
            # 필터링 품질 분석
            self.analyze_filtering_quality()
        else:
            print(f'\n💡 필터링된 메시지가 없습니다. 키워드를 조정해보세요.')
    
    def process_message_batch_improved(self, message_batch, kst):
        """개선된 메시지 배치 처리 (더 정교한 필터링)"""
        batch_filtered = 0
        
        for message in message_batch:
            # 개선된 일정 가능성 판단
            is_schedule, reason = self.is_likely_schedule(message.content)
            
            if is_schedule:
                batch_filtered += 1
                
                # 메시지 정보 저장 (더 상세한 정보 포함)
                message_data = {
                    'id': message.id,
                    'content': message.content,
                    'author': str(message.author),
                    'channel': f'#{message.channel.name}',
                    'guild': message.guild.name,
                    'created_at': message.created_at.astimezone(kst),
                    'filter_reason': reason,  # 필터링 이유 추가
                    'message_length': len(message.content),
                    'has_mention': '@' in message.content,
                    'has_url': 'http' in message.content.lower(),
                }
                self.collected_messages.append(message_data)
        
        return batch_filtered
    
    def group_context_messages(self):
        """맥락 묶기 처리 (기존과 동일하지만 성능 최적화)"""
        print(f'\n🔗 맥락 묶기 처리 중...')
        
        if len(self.collected_messages) > 1000:
            print(f'⚠️  대용량 데이터({len(self.collected_messages):,}개) 처리 중입니다.')
        
        # 시간순으로 정렬
        all_messages_sorted = sorted(self.collected_messages, key=lambda x: x['created_at'])
        
        # 작성자별로 그룹핑 (성능 최적화)
        author_messages = {}
        for msg in all_messages_sorted:
            author = msg['author']
            if author not in author_messages:
                author_messages[author] = []
            author_messages[author].append(msg)
        
        # 맥락 그룹 생성
        context_groups = []
        processed_message_ids = set()
        
        for msg in all_messages_sorted:
            # 이미 처리된 메시지는 건너뛰기
            if msg['id'] in processed_message_ids:
                continue
            
            author = msg['author']
            msg_time = msg['created_at']
            
            # 맥락 그룹 시작
            context_messages = [msg]
            processed_message_ids.add(msg['id'])
            
            author_msg_list = author_messages.get(author, [])
            msg_index = next((i for i, m in enumerate(author_msg_list) if m['id'] == msg['id']), -1)
            
            if msg_index >= 0:
                # 이후 최대 4개 메시지 수집 (5개에서 줄임)
                for i in range(msg_index + 1, min(msg_index + 5, len(author_msg_list))):
                    next_msg = author_msg_list[i]
                    time_diff = (next_msg['created_at'] - msg_time).total_seconds() / 60  # 분 단위
                    
                    # 5분 이내의 메시지만 포함 (10분에서 줄임)
                    if time_diff <= 5:
                        context_messages.append(next_msg)
                        processed_message_ids.add(next_msg['id'])
                    else:
                        break
            
            # 맥락 그룹 생성
            combined_content = ' '.join([m['content'] for m in context_messages])
            
            # 모든 필터링 이유 수집
            all_reasons = []
            for m in context_messages:
                if 'filter_reason' in m:
                    all_reasons.append(m['filter_reason'])
            
            context_group = {
                'id': f"context_{msg['id']}",
                'content': combined_content,
                'original_content': msg['content'],
                'author': author,
                'channel': msg['channel'],
                'guild': msg['guild'],
                'created_at': msg['created_at'],
                'filter_reasons': all_reasons,  # 필터링 이유들
                'message_count': len(context_messages),
                'context_messages': context_messages,
                'is_context_grouped': len(context_messages) > 1,
                'total_length': len(combined_content),
                'keywords_found': []  # AI에서 채워질 예정
            }
            context_groups.append(context_group)
        
        # 원본 메시지 리스트를 맥락 그룹으로 교체
        original_count = len(self.collected_messages)
        self.collected_messages = context_groups
        
        # 맥락 묶기 결과 출력
        grouped_count = sum(1 for msg in context_groups if msg['is_context_grouped'])
        total_context_messages = sum(msg['message_count'] for msg in context_groups)
        
        print(f'   📊 맥락 묶기 완료!')
        print(f'      📥 원본 메시지: {original_count:,}개')
        print(f'      🔗 맥락 그룹: {len(context_groups):,}개')
        print(f'      📝 묶인 그룹: {grouped_count:,}개')
        print(f'      📊 총 포함 메시지: {total_context_messages:,}개')
        print(f'      🎯 압축 비율: {(len(context_groups)/original_count*100):.1f}%')
    
    def analyze_filtering_quality(self):
        """필터링 품질 분석 (새로운 기능)"""
        print(f'\n🔍 필터링 품질 분석:')
        print('=' * 60)
        
        # 필터링 이유별 통계
        reason_stats = {}
        for msg in self.collected_messages:
            for reason in msg.get('filter_reasons', []):
                # 이유에서 패턴 추출
                if ':' in reason:
                    reason_type = reason.split(':')[0]
                else:
                    reason_type = reason
                
                reason_stats[reason_type] = reason_stats.get(reason_type, 0) + 1
        
        print('🏷️ 필터링 이유별 통계:')
        for reason, count in sorted(reason_stats.items(), key=lambda x: x[1], reverse=True):
            print(f'   • {reason}: {count}개')
        
        # 메시지 길이 분석
        lengths = [msg.get('total_length', 0) for msg in self.collected_messages]
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            print(f'\n📏 메시지 길이 분석:')
            print(f'   • 평균 길이: {avg_length:.1f}자')
            print(f'   • 최단: {min(lengths)}자')
            print(f'   • 최장: {max(lengths)}자')
        
        # 샘플 메시지 표시 (품질 확인용)
        print(f'\n📋 필터링된 샘플 메시지 (품질 확인):')
        print('-' * 60)
        for i, msg in enumerate(self.collected_messages[:5]):
            print(f'\n{i+1}. [{msg["channel"]:12s}] {msg["author"]:15s}')
            print(f'   💬 "{msg["content"][:80]}..."')
            print(f'   🎯 필터링 이유: {", ".join(msg.get("filter_reasons", ["없음"]))[:50]}...')
            print(f'   🕐 {msg["created_at"].strftime("%m-%d %H:%M")} | 길이: {msg.get("total_length", 0)}자')
        
        if len(self.collected_messages) > 5:
            print(f'   ... 및 {len(self.collected_messages) - 5}개 추가 그룹')

async def collect_discord_messages():
    """Discord 메시지 수집 메인 함수"""
    print("🔗 Discord 메시지 수집을 시작합니다...")
    
    # 환경변수에서 Discord 토큰 가져오기
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ 오류: DISCORD_TOKEN이 설정되지 않았습니다!")
        return []
    
    # 메시지 수집기 실행
    collector = MessageCollector()
    collected_messages = []
    
    try:
        await collector.start(token)
        collected_messages = collector.collected_messages.copy()
        print("✅ 메시지 수집 완료")
        
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
    
    return collected_messages
