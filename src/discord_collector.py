import discord
import os
import asyncio
from datetime import datetime, timedelta
import pytz

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
    
    async def collect_recent_messages(self):
        """최근 10일간 메시지 수집 (테스트용 대용량 데이터)"""
        print(f'\n📥 메시지 수집을 시작합니다...')
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        ten_days_ago = now - timedelta(days=10)  # 10일 전부터 수집
        
        print(f'📅 수집 기간: {ten_days_ago.strftime("%Y-%m-%d %H:%M")} ~ {now.strftime("%Y-%m-%d %H:%M")} (한국시간)')
        print(f'📊 수집 범위: 최근 10일간 (대용량 테스트 모드)')
        
        # 일정 관련 키워드 (1차 필터링용) - 최적화된 버전
        schedule_keywords = [
            # 핵심 일정 키워드 (높은 정확도)
            '회의', '미팅', '약속', '모임',
            
            # 음악 관련 (동아리 특화 - 높은 정확도)
            '합주', '리허설', '연습', '공연', '콘서트', '연주',
            '세팅', '사운드체크', '무대',
            
            # 장소 관련 (구체적)
            '연습실', '공연장', '스튜디오',
            
            # 시간 표현 (구체적인 것만)
            '몇시', '시에', '오전', '오후',
            
            # 질문/제안 (구체적인 표현)
            '언제', '할까', '어때', '가능',
            
            # 일정 관련 (직접적)
            '일정', '계획', '예약'
        ]
        
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
                    
                    # 최근 10일간 메시지 가져오기 (대용량)
                    message_batch = []
                    async for message in channel.history(after=ten_days_ago, limit=None):
                        total_messages += 1
                        channel_count += 1
                        
                        # 봇 메시지는 제외
                        if message.author.bot:
                            continue
                        
                        # 배치 처리를 위해 임시 저장
                        message_batch.append(message)
                        
                        # 1000개씩 배치 처리 (메모리 효율성)
                        if len(message_batch) >= 1000:
                            batch_filtered = self.process_message_batch(message_batch, schedule_keywords, kst)
                            channel_filtered += batch_filtered
                            filtered_messages += batch_filtered
                            message_batch = []
                    
                    # 남은 메시지들 처리
                    if message_batch:
                        batch_filtered = self.process_message_batch(message_batch, schedule_keywords, kst)
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
        print(f'\n📊 10일간 메시지 수집 완료!')
        print(f'   📥 전체 메시지: {total_messages:,}개')
        print(f'   🔍 필터링된 메시지: {filtered_messages:,}개')
        print(f'   📈 필터링 비율: {(filtered_messages/total_messages*100):.2f}%' if total_messages > 0 else '   비율: 0%')
        
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
            print(f'\n📈 대용량 데이터 분석 준비 완료!')
            print(f'   🎯 AI 분석 대상: {len(self.collected_messages)}개 맥락 그룹')
            
            # 상세 키워드 분석 (대용량 최적화된 버전)
            self.analyze_keywords_and_messages(schedule_keywords)
        else:
            print(f'\n💡 필터링된 메시지가 없습니다. 키워드를 조정해보세요.')
    
    def process_message_batch(self, message_batch, schedule_keywords, kst):
        """메시지 배치를 처리하여 키워드 필터링"""
        batch_filtered = 0
        
        for message in message_batch:
            # 1차 필터링: 일정 관련 키워드만으로 필터링
            message_text = message.content.lower()
            found_keywords = [kw for kw in schedule_keywords if kw in message_text]
            
            if found_keywords:  # 키워드가 포함된 메시지만 수집
                batch_filtered += 1
                
                # 메시지 정보 저장
                message_data = {
                    'id': message.id,
                    'content': message.content,
                    'author': str(message.author),
                    'channel': f'#{message.channel.name}',
                    'guild': message.guild.name,
                    'created_at': message.created_at.astimezone(kst),
                    'keywords_found': found_keywords
                }
                self.collected_messages.append(message_data)
        
        return batch_filtered
    
    def group_context_messages(self):
        """연속 메시지를 묶어서 맥락 파악 개선 (대용량 최적화)"""
        print(f'\n🔗 맥락 묶기 처리 중 (대용량 데이터)...')
        
        if len(self.collected_messages) > 1000:
            print(f'⚠️  대용량 데이터({len(self.collected_messages):,}개) 처리 중입니다. 시간이 소요될 수 있습니다.')
        
        # 시간순으로 정렬 (모든 채널의 모든 메시지)
        print(f'   📊 시간순 정렬 중...')
        all_messages_sorted = sorted(self.collected_messages, key=lambda x: x['created_at'])
        
        # 작성자별로 그룹핑 (성능 최적화)
        print(f'   👥 작성자별 그룹핑 중...')
        author_messages = {}
        for msg in all_messages_sorted:
            author = msg['author']
            if author not in author_messages:
                author_messages[author] = []
            author_messages[author].append(msg)
        
        # 맥락 그룹 생성
        print(f'   🔄 맥락 그룹 생성 중...')
        context_groups = []
        processed_message_ids = set()
        
        progress_counter = 0
        total_messages = len(all_messages_sorted)
        
        for msg in all_messages_sorted:
            progress_counter += 1
            
            # 진행률 표시 (1000개마다)
            if progress_counter % 1000 == 0 or progress_counter == total_messages:
                progress = progress_counter / total_messages * 100
                print(f'      🔄 진행률: {progress:5.1f}% ({progress_counter:,}/{total_messages:,})')
            
            # 이미 처리된 메시지는 건너뛰기
            if msg['id'] in processed_message_ids:
                continue
            
            # 키워드가 포함된 메시지만 맥락 묶기 시작점으로 사용
            if not msg['keywords_found']:
                continue
            
            author = msg['author']
            msg_time = msg['created_at']
            
            # 해당 작성자의 이후 5개 메시지 찾기 (시간 제한: 10분 이내)
            context_messages = [msg]
            processed_message_ids.add(msg['id'])
            
            author_msg_list = author_messages.get(author, [])
            msg_index = next((i for i, m in enumerate(author_msg_list) if m['id'] == msg['id']), -1)
            
            if msg_index >= 0:
                # 이후 최대 5개 메시지 수집
                for i in range(msg_index + 1, min(msg_index + 6, len(author_msg_list))):
                    next_msg = author_msg_list[i]
                    time_diff = (next_msg['created_at'] - msg_time).total_seconds() / 60  # 분 단위
                    
                    # 10분 이내의 메시지만 포함
                    if time_diff <= 10:
                        context_messages.append(next_msg)
                        processed_message_ids.add(next_msg['id'])
                    else:
                        break
            
            # 맥락 그룹 생성 (1개여도 포함 - 키워드가 있으니까)
            if len(context_messages) >= 1:
                combined_content = ' '.join([m['content'] for m in context_messages])
                all_keywords = []
                for m in context_messages:
                    all_keywords.extend(m['keywords_found'])
                
                context_group = {
                    'id': f"context_{msg['id']}",
                    'content': combined_content,
                    'original_content': msg['content'],
                    'author': author,
                    'channel': msg['channel'],
                    'guild': msg['guild'],
                    'created_at': msg['created_at'],
                    'keywords_found': list(set(all_keywords)),  # 중복 제거
                    'message_count': len(context_messages),
                    'context_messages': context_messages,
                    'is_context_grouped': len(context_messages) > 1
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
        
        # AI 분석 예상 비용 계산
        estimated_batches = (len(context_groups) + 14) // 15  # 15개씩 배치
        estimated_cost_won = estimated_batches * 5  # 배치당 약 5원 예상
        print(f'      💰 예상 AI 분석 비용: 약 {estimated_cost_won:,}원 ({estimated_batches}배치)')
    
    def analyze_keywords_and_messages(self, schedule_keywords):
        """키워드별 분석 및 샘플 메시지 출력 (대용량 데이터 대응)"""
        
        # 키워드별 통계 수집
        keyword_stats = {}
        for keyword in schedule_keywords:
            keyword_stats[keyword] = []
        
        # 각 메시지에서 발견된 키워드 분류
        for msg in self.collected_messages:
            for keyword in msg['keywords_found']:
                if keyword in keyword_stats:
                    keyword_stats[keyword].append(msg)
        
        # 키워드별 통계 출력
        print(f'\n📈 키워드별 사용 통계 (10일간):')
        print('=' * 80)
        
        # 사용량 순으로 정렬
        sorted_keywords = sorted(keyword_stats.items(), key=lambda x: len(x[1]), reverse=True)
        
        # 상위 15개 키워드만 표시
        for i, (keyword, messages) in enumerate(sorted_keywords[:15]):
            if len(messages) > 0:
                print(f'🔑 {i+1:2d}. "{keyword}": {len(messages):3d}개 그룹')
        
        # 나머지 키워드 요약
        remaining_keywords = sorted_keywords[15:]
        if remaining_keywords:
            total_remaining = sum(len(messages) for _, messages in remaining_keywords)
            print(f'🔑     ... 기타 {len(remaining_keywords)}개 키워드: {total_remaining}개 그룹')
        
        print(f'\n📋 주요 키워드별 샘플 메시지 (상위 5개):')
        print('=' * 80)
        
        # 상위 5개 키워드만 상세 분석
        for keyword, messages in sorted_keywords[:5]:
            if len(messages) == 0:
                continue
                
            print(f'\n🔍 키워드: "{keyword}" ({len(messages)}개 그룹)')
            print('-' * 60)
            
            # 샘플 5개만 표시
            sample_messages = messages[:5]
            for i, msg in enumerate(sample_messages):
                # 맥락 그룹인지 단일 메시지인지 구분
                if msg.get('is_context_grouped', False):
                    # 맥락이 묶인 경우
                    print(f'   {i+1}. 🔗[맥락그룹] [{msg["channel"]:12s}] {msg["author"]:15s}')
                    print(f'      📝 "{msg["content"][:80]}..."')
                    print(f'      📊 {msg["message_count"]}개 메시지 | 🕐 {msg["created_at"].strftime("%m-%d %H:%M")}')
                else:
                    # 단일 메시지인 경우
                    highlighted_content = msg['content'][:80]
                    for kw in msg['keywords_found']:
                        highlighted_content = highlighted_content.replace(kw, f'【{kw}】')
                    
                    print(f'   {i+1}. [{msg["channel"]:12s}] {msg["author"]:15s}')
                    print(f'      💬 "{highlighted_content}..."')
                    print(f'      🕐 {msg["created_at"].strftime("%m-%d %H:%M")}')
            
            if len(messages) > 5:
                print(f'      ... 및 {len(messages) - 5}개 추가 메시지')
        
        # 채널별 통계 (상위 10개만)
        print(f'\n📊 채널별 상위 10개 (10일간):')
        print('=' * 80)
        
        channel_stats = {}
        for msg in self.collected_messages:
            channel = msg['channel']
            if channel not in channel_stats:
                channel_stats[channel] = {
                    'groups': [],
                    'total_messages': 0,
                    'grouped_count': 0
                }
            
            channel_stats[channel]['groups'].append(msg)
            channel_stats[channel]['total_messages'] += msg.get('message_count', 1)
            if msg.get('is_context_grouped', False):
                channel_stats[channel]['grouped_count'] += 1
        
        # 그룹 수 순으로 정렬하여 상위 10개만
        sorted_channels = sorted(channel_stats.items(), key=lambda x: len(x[1]['groups']), reverse=True)
        
        for i, (channel, stats) in enumerate(sorted_channels[:10]):
            groups = stats['groups']
            grouped_count = stats['grouped_count']
            total_msg_count = stats['total_messages']
            
            print(f'{i+1:2d}. 📝 {channel:20s}: {len(groups):3d}개 그룹 (총 {total_msg_count:,}개 메시지)')
            
            # 해당 채널의 주요 키워드 (상위 3개)
            channel_keywords = {}
            for msg in groups:
                for keyword in msg['keywords_found']:
                    channel_keywords[keyword] = channel_keywords.get(keyword, 0) + 1
            
            if channel_keywords:
                top_keywords = sorted(channel_keywords.items(), key=lambda x: x[1], reverse=True)[:3]
                keywords_str = ', '.join([f'{kw}({count})' for kw, count in top_keywords])
                print(f'     🔑 주요 키워드: {keywords_str}')
        
        if len(sorted_channels) > 10:
            remaining_channels = len(sorted_channels) - 10
            remaining_groups = sum(len(stats['groups']) for _, stats in sorted_channels[10:])
            print(f'     ... 기타 {remaining_channels}개 채널: {remaining_groups}개 그룹')
        
        # 키워드 타당성 평가 가이드 (요약)
        print(f'\n💡 10일간 데이터 분석 완료!')
        print('=' * 80)
        print(f'🎯 발견된 패턴:')
        print(f'   📊 총 {len(self.collected_messages):,}개 맥락 그룹 생성')
        print(f'   🔑 활성 키워드: {len([k for k, m in sorted_keywords if len(m) > 0])}개')
        print(f'   📝 주요 채널: {min(10, len(sorted_channels))}개')
        print(f'   💰 예상 AI 분석 비용: 약 {((len(self.collected_messages) + 14) // 15 * 5):,}원')
        print()
        print(f'🚀 AI 분석 단계로 진행할 준비가 완료되었습니다!')
        print(f'📝 대용량 데이터로 더 정확한 일정 분류 성능을 확인할 수 있습니다.')

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
        collected_messages = collector.collected_messages.copy()  # 복사본 생성
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

# 이 파일이 직접 실행될 때만 테스트 수행
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Discord Schedule Bot - 메시지 수집 테스트")
    print("=" * 60)
    
    # 비동기 함수 실행
    messages = asyncio.run(collect_discord_messages())
    
    print(f"\n🎯 최종 결과: {len(messages)}개의 메시지를 수집했습니다!")
    
    if messages:
        print("\n🔍 상세 분석을 위해 AI 분석 단계로 넘어갈 준비가 되었습니다.")
    else:
        print("\n💡 메시지가 수집되지 않았습니다. 설정을 확인해보세요.")
