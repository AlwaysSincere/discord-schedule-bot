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
        """최근 24시간 메시지 수집"""
        print(f'\n📥 메시지 수집을 시작합니다...')
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        yesterday = now - timedelta(days=1)
        
        print(f'📅 수집 기간: {yesterday.strftime("%Y-%m-%d %H:%M")} ~ {now.strftime("%Y-%m-%d %H:%M")} (한국시간)')
        
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
        
        # 모든 서버의 모든 채널에서 메시지 수집
        for guild in self.guilds:
            print(f'\n🏢 서버: {guild.name}')
            
            for channel in guild.text_channels:
                try:
                    # 채널 접근 권한 확인
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue
                    
                    print(f'  📝 #{channel.name} 확인 중...', end='')
                    
                    channel_count = 0
                    channel_filtered = 0
                    
                    # 최근 24시간 메시지 가져오기
                    async for message in channel.history(after=yesterday, limit=None):
                        total_messages += 1
                        channel_count += 1
                        
                        # 봇 메시지는 제외
                        if message.author.bot:
                            continue
                        
                        # 1차 필터링: 일정 관련 키워드만으로 필터링
                        message_text = message.content.lower()
                        has_keyword = any(keyword in message_text for keyword in schedule_keywords)
                        
                        if has_keyword:  # 키워드가 포함된 메시지만 수집
                            filtered_messages += 1
                            channel_filtered += 1
                            
                            # 메시지 정보 저장
                            message_data = {
                                'id': message.id,
                                'content': message.content,
                                'author': str(message.author),
                                'channel': f'#{channel.name}',
                                'guild': guild.name,
                                'created_at': message.created_at.astimezone(kst),
                                'keywords_found': [kw for kw in schedule_keywords if kw in message_text]
                            }
                            self.collected_messages.append(message_data)
                    
                    print(f' {channel_count}개 메시지 (필터링: {channel_filtered}개)')
                    
                except discord.Forbidden:
                    print(f' ❌ 접근 권한 없음')
                except Exception as e:
                    print(f' ❌ 오류: {e}')
        
        # 수집 결과 요약
        print(f'\n📊 수집 완료!')
        print(f'   전체 메시지: {total_messages}개')
        print(f'   필터링된 메시지: {filtered_messages}개')
        print(f'   필터링 비율: {(filtered_messages/total_messages*100):.1f}%' if total_messages > 0 else '   비율: 0%')
        
        # 맥락 묶기 처리
        if self.collected_messages:
            self.group_context_messages()
            self.analyze_keywords_and_messages(schedule_keywords)
        else:
            print(f'\n💡 필터링된 메시지가 없습니다. 키워드를 조정해보세요.')
    
    def group_context_messages(self):
        """연속 메시지를 묶어서 맥락 파악 개선"""
        print(f'\n🔗 맥락 묶기 처리 중...')
        
        # 시간순으로 정렬 (모든 채널의 모든 메시지)
        all_messages_sorted = sorted(self.collected_messages, key=lambda x: x['created_at'])
        
        # 작성자별로 그룹핑
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
            
            # 맥락 그룹 생성 (2개 이상 메시지가 있을 때만)
            if len(context_messages) >= 1:  # 1개여도 포함 (키워드가 있으니까)
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
        
        print(f'   📥 원본 메시지: {original_count}개')
        print(f'   🔗 맥락 그룹: {len(context_groups)}개')
        print(f'   📝 묶인 그룹: {grouped_count}개')
        print(f'   📊 총 포함 메시지: {total_context_messages}개')
        print(f'   🎯 압축 비율: {(len(context_groups)/original_count*100):.1f}%')
    
    def analyze_keywords_and_messages(self, schedule_keywords):
        """키워드별 분석 및 모든 메시지 출력"""
        
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
        print(f'\n📈 키워드별 사용 통계:')
        print('=' * 80)
        
        # 사용량 순으로 정렬
        sorted_keywords = sorted(keyword_stats.items(), key=lambda x: len(x[1]), reverse=True)
        
        for keyword, messages in sorted_keywords:
            if len(messages) > 0:
                print(f'🔑 "{keyword}": {len(messages)}개 메시지')
        
        print(f'\n📋 키워드별 상세 메시지 분석:')
        print('=' * 80)
        
        # 키워드별로 메시지들 출력
        for keyword, messages in sorted_keywords:
            if len(messages) == 0:
                continue
                
            print(f'\n🔍 키워드: "{keyword}" ({len(messages)}개 그룹)')
            print('-' * 60)
            
            for i, msg in enumerate(messages):
                # 맥락 그룹인지 단일 메시지인지 구분
                if msg.get('is_context_grouped', False):
                    # 맥락이 묶인 경우
                    print(f'   {i+1:2d}. 🔗 [맥락 그룹] [{msg["channel"]:12s}] {msg["author"]:15s}')
                    print(f'       📝 묶인 내용: "{msg["content"][:100]}..."')
                    print(f'       📊 {msg["message_count"]}개 메시지 묶음 | 키워드: {msg["keywords_found"]}')
                    print(f'       🕐 {msg["created_at"].strftime("%m-%d %H:%M")}')
                    
                    # 원본 메시지들 표시
                    print(f'       📋 원본 메시지들:')
                    for j, orig_msg in enumerate(msg['context_messages']):
                        highlighted_content = orig_msg['content']
                        for kw in orig_msg['keywords_found']:
                            highlighted_content = highlighted_content.replace(kw, f'【{kw}】')
                        print(f'          {j+1}. "{highlighted_content}"')
                else:
                    # 단일 메시지인 경우
                    highlighted_content = msg['content']
                    for kw in msg['keywords_found']:
                        highlighted_content = highlighted_content.replace(kw, f'【{kw}】')
                    
                    print(f'   {i+1:2d}. [{msg["channel"]:12s}] {msg["author"]:15s}')
                    print(f'       💬 "{highlighted_content}"')
                    print(f'       🕐 {msg["created_at"].strftime("%m-%d %H:%M")} | 키워드: {msg["keywords_found"]}')
                print()
        
        # 전체 메시지 시간순 정렬 출력
        print(f'\n🕐 전체 맥락 그룹 시간순 정렬:')
        print('=' * 80)
        
        # 시간순으로 정렬 (최신이 위로, reverse=True 유지)
        sorted_messages = sorted(self.collected_messages, key=lambda x: x['created_at'], reverse=True)
        
        for i, msg in enumerate(sorted_messages):
            if msg.get('is_context_grouped', False):
                # 맥락이 묶인 그룹
                print(f'{i+1:3d}. 🔗 {msg["created_at"].strftime("%m-%d %H:%M")} [{msg["channel"]:12s}] {msg["author"]:15s}')
                print(f'     📝 맥락 내용: "{msg["content"][:80]}..."')
                print(f'     📊 {msg["message_count"]}개 메시지 | 🔑 키워드: {msg["keywords_found"]}')
                
                # 묶인 메시지들의 간략 정보
                print(f'     📋 구성 메시지:')
                for j, orig_msg in enumerate(msg['context_messages']):
                    print(f'        {j+1}. "{orig_msg["content"][:30]}..."')
            else:
                # 단일 메시지
                print(f'{i+1:3d}. {msg["created_at"].strftime("%m-%d %H:%M")} [{msg["channel"]:12s}] {msg["author"]:15s}')
                print(f'     💬 "{msg["content"]}"')
                print(f'     🔑 키워드: {msg["keywords_found"]}')
            print()
        
        # 채널별 통계
        print(f'\n📊 채널별 맥락 그룹 분포:')
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
        
        # 그룹 수 순으로 정렬
        sorted_channels = sorted(channel_stats.items(), key=lambda x: len(x[1]['groups']), reverse=True)
        
        for channel, stats in sorted_channels:
            groups = stats['groups']
            grouped_count = stats['grouped_count']
            total_msg_count = stats['total_messages']
            
            print(f'📝 {channel}: {len(groups)}개 그룹 (총 {total_msg_count}개 메시지)')
            print(f'     🔗 맥락 묶인 그룹: {grouped_count}개')
            
            # 해당 채널의 키워드 통계
            channel_keywords = {}
            for msg in groups:
                for keyword in msg['keywords_found']:
                    channel_keywords[keyword] = channel_keywords.get(keyword, 0) + 1
            
            if channel_keywords:
                top_keywords = sorted(channel_keywords.items(), key=lambda x: x[1], reverse=True)[:3]
                keywords_str = ', '.join([f'{kw}({count})' for kw, count in top_keywords])
                print(f'     🔑 주요 키워드: {keywords_str}')
            print()
        
        # 키워드 타당성 평가 가이드
        print(f'\n💡 키워드 + 맥락 묶기 평가 가이드:')
        print('=' * 80)
        print(f'✅ 유지해야 할 키워드: 대부분의 메시지가 실제 일정 관련')
        print(f'⚠️  검토 필요 키워드: 일정/비일정이 섞여 있음')  
        print(f'❌ 제거 고려 키워드: 대부분이 일반 대화나 잡담')
        print(f'➕ 추가 고려 키워드: 자주 등장하지만 현재 키워드에 없는 표현들')
        print()
        print(f'🔗 맥락 묶기 효과:')
        print(f'   📝 끊어진 메시지들이 하나의 완전한 문장으로 연결됨')
        print(f'   🎯 AI 분석 정확도 향상 (맥락 파악 개선)')
        print(f'   💰 API 비용 절약 (메시지 수 압축)')
        print()
        print(f'🎯 각 키워드별 맥락 그룹들을 검토하여 키워드 리스트를 최적화하세요!')
        print(f'📝 맥락이 잘 묶였는지, 불필요한 메시지가 포함되지 않았는지 확인하세요.')
        print(f'🚀 OpenAI API 사용 전 1차 필터링 + 맥락 묶기 품질을 향상시킬 수 있습니다.')

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
    
    try:
        await collector.start(token)
        return collector.collected_messages
    except discord.LoginFailure:
        print("❌ 로그인 실패: Discord 토큰이 잘못되었습니다!")
        return []
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        return []
    finally:
        # 연결이 완전히 종료되었는지 확인
        if not collector.is_closed():
            await collector.close()
        print("🔌 Discord 연결이 안전하게 종료되었습니다.")

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
