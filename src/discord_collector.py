# src/discord_collector.py (개선된 버전)
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
        """봇이 로그인한 후 메시지 수집 시작 (진척도 개선)"""
        print(f'🎉 봇 로그인 성공: {self.user}')
        
        try:
            # 메시지 수집 실행 (진척도 표시 개선)
            await self.collect_recent_messages_with_progress()
        except Exception as e:
            print(f"❌ 메시지 수집 중 오류: {e}")
        finally:
            # 수집 완료 후 봇 안전 종료
            print("🔌 봇 연결을 종료합니다...")
            await self.close()
    
    def is_likely_schedule(self, message_text):
        """메시지가 일정일 가능성을 판단 (기존과 동일)"""
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
        
        # 데이터 기반 키워드 시스템 (점수 방식)
        score = 0
        matched_keywords = []
        
        # 고효율 키워드 (10점)
        high_precision = ['합니다', '그래서', '공연', '연습', '세팅']
        for keyword in high_precision:
            if keyword in text:
                score += 10
                matched_keywords.append(f"고효율:{keyword}")
        
        # 핵심 일정 키워드 (5점)
        core_schedule = ['합주', '리허설', '콘서트', '라이트', '더스트', '현합']
        for keyword in core_schedule:
            if keyword in text:
                score += 5
                matched_keywords.append(f"핵심:{keyword}")
        
        # 시간 관련 키워드 (3점)
        time_related = ['오늘', '내일', '이번', '언제', '몇시', '시간']
        for keyword in time_related:
            if keyword in text:
                score += 3
                matched_keywords.append(f"시간:{keyword}")
        
        # 보조 키워드 (1점)
        support = ['저희', 'mtr', '우리', 'everyone', '같습니다', '끝나고']
        for keyword in support:
            if keyword in text:
                score += 1
                matched_keywords.append(f"보조:{keyword}")
        
        # 시간 패턴 보너스 (5점)
        time_patterns = re.findall(r'\d{1,2}시\s*\d{0,2}분?|\d{1,2}:\d{2}', text)
        if time_patterns:
            score += 5
            matched_keywords.append(f"시간패턴:{time_patterns}")
        
        # 필터링 기준: 8점 이상
        is_schedule = score >= 8
        reason = f"점수:{score} " + ", ".join(matched_keywords[:3]) + "..."
        
        return is_schedule, reason
    
    async def estimate_channel_sizes(self):
        """각 채널의 메시지 수를 미리 추정 (새로운 기능)"""
        print(f'\n📏 채널별 메시지 수 추정 중...')
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        sixty_days_ago = now - timedelta(days=60)
        
        channel_estimates = {}
        total_estimated = 0
        
        for guild in self.guilds:
            print(f'  🏢 {guild.name} 분석 중...')
            
            for channel in guild.text_channels:
                if not channel.permissions_for(guild.me).read_message_history:
                    continue
                
                try:
                    # 최근 100개 메시지로 전체 추정
                    sample_messages = []
                    sample_count = 0
                    
                    async for message in channel.history(limit=100):
                        if message.created_at.astimezone(kst) < sixty_days_ago:
                            break
                        sample_count += 1
                        sample_messages.append(message)
                    
                    if sample_count > 0:
                        # 평균 메시지 간격 계산
                        if len(sample_messages) >= 2:
                            time_span = (sample_messages[0].created_at - sample_messages[-1].created_at).total_seconds()
                            avg_interval = time_span / len(sample_messages)
                            total_seconds = (now - sixty_days_ago).total_seconds()
                            estimated_count = int(total_seconds / avg_interval) if avg_interval > 0 else sample_count
                        else:
                            estimated_count = sample_count
                        
                        # 안전 계수 적용 (추정 오차 고려)
                        estimated_count = min(estimated_count * 2, 50000)  # 최대 5만개로 제한
                        
                        channel_estimates[f"{guild.name}#{channel.name}"] = estimated_count
                        total_estimated += estimated_count
                    
                except Exception as e:
                    print(f'    ⚠️ #{channel.name}: 추정 실패 ({str(e)[:30]}...)')
        
        # 추정 결과 출력
        print(f'\n📊 채널별 추정 메시지 수:')
        sorted_channels = sorted(channel_estimates.items(), key=lambda x: x[1], reverse=True)
        
        for channel_name, estimate in sorted_channels:
            percentage = (estimate / total_estimated * 100) if total_estimated > 0 else 0
            print(f'   📝 {channel_name:<30}: {estimate:>6,}개 ({percentage:4.1f}%)')
        
        print(f'\n   📊 총 추정: {total_estimated:,}개 메시지')
        print(f'   ⏱️  예상 소요 시간: {total_estimated/1000:.1f}분')
        
        return channel_estimates, total_estimated
async def collect_recent_messages_with_progress(self):
    """진척도 표시가 개선된 메시지 수집 (진행 바 및 배치 처리 추가)"""
    print(f'\n📥 개선된 메시지 수집을 시작합니다...')
    
    # 1단계: 채널별 메시지 수 추정
    channel_estimates, total_estimated = await self.estimate_channel_sizes()
    
    if total_estimated == 0:
        print("❌ 수집할 메시지가 없습니다.")
        return
    
    # 2단계: 실제 수집 시작
    print(f'\n📥 실제 메시지 수집 시작...')
    print(f'📊 예상 총량: {total_estimated:,}개')
    
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    sixty_days_ago = now - timedelta(days=60)
    
    total_processed = 0
    total_filtered = 0
    
    for guild in self.guilds:
        print(f'\n🏢 서버: {guild.name}')
        
        guild_channels = [ch for ch in guild.text_channels 
                         if ch.permissions_for(guild.me).read_message_history]
        
        for i, channel in enumerate(guild_channels):
            channel_key = f"{guild.name}#{channel.name}"
            estimated_for_channel = channel_estimates.get(channel_key, 0)
            
            print(f'  📝 [{i+1:2d}/{len(guild_channels):2d}] #{channel.name:<20s} ', end='')
            print(f'(예상: {estimated_for_channel:,}개)')
            
            try:
                channel_processed = 0
                channel_filtered = 0
                last_progress_update = 0
                batch_size = 500  # 배치 크기 설정 (대량 채널 병목 완화)
                batch_messages = []
                start_time = datetime.now(kst)
                
                # 메시지 수집 with 진행 바
                async for message in channel.history(after=sixty_days_ago, limit=None):
                    if message.author.bot:
                        continue
                    
                    total_processed += 1
                    channel_processed += 1
                    batch_messages.append(message)
                    
                    # 배치 단위로 처리
                    if len(batch_messages) >= batch_size or channel_processed == estimated_for_channel:
                        # 배치 내 메시지 필터링
                        for message in batch_messages:
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
                        
                        # 진행 바 및 상태 업데이트
                        progress_pct = (channel_processed / estimated_for_channel * 100) if estimated_for_channel > 0 else 0
                        bar_length = 20  # 진행 바 길이
                        filled = int(bar_length * progress_pct / 100)
                        bar = '=' * filled + '-' * (bar_length - filled)
                        
                        # 예상 남은 시간 계산
                        elapsed_time = (datetime.now(kst) - start_time).total_seconds()
                        if channel_processed > 0:
                            time_per_message = elapsed_time / channel_processed
                            remaining_messages = estimated_for_channel - channel_processed
                            est_remaining_time = remaining_messages * time_per_message
                        else:
                            est_remaining_time = 0
                        
                        # 진행 정보 출력
                        print(f'\r    📈 [{bar}] {progress_pct:3.0f}% ({channel_processed:,}/{estimated_for_channel:,}) ', end='')
                        print(f'| 필터: {channel_filtered:3d} ({(channel_filtered/channel_processed*100):.1f}%) ', end='')
                        print(f'| 남은 시간: {est_remaining_time:.0f}s', flush=True)
                        
                        batch_messages = []  # 배치 초기화
                        last_progress_update = channel_processed
                        await asyncio.sleep(0.1)  # API 부하 방지
                
                # 마지막 배치 처리
                if batch_messages:
                    for message in batch_messages:
                        is_schedule, reason = self.is_likely_schedule(message.content)
                        
                        if is_schedule:
                            total_filtered += 1
                            channel_filtered += 1
                            
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
                    
                    # 최종 진행 바 업데이트
                    progress_pct = (channel_processed / estimated_for_channel * 100) if estimated_for_channel > 0 else 100
                    bar_length = 20
                    filled = int(bar_length * progress_pct / 100)
                    bar = '=' * filled + '-' * (bar_length - filled)
                    print(f'\r    📈 [{bar}] {progress_pct:3.0f}% ({channel_processed:,}/{estimated_for_channel:,}) ', end='')
                    print(f'| 필터: {channel_filtered:3d} ({(channel_filtered/channel_processed*100):.1f}%) ', end='')
                    print(f'| 완료', flush=True)
                
                # 채널 완료 결과
                filter_rate = f"{(channel_filtered/channel_processed*100):.1f}%" if channel_processed > 0 else "0%"
                print(f'    ✅ 완료: {channel_processed:,}개 → {channel_filtered:3d}개 ({filter_rate})')
                
                # 전체 진척도 표시
                overall_progress = (total_processed / total_estimated * 100) if total_estimated > 0 else 0
                print(f'    📊 전체 진척: {overall_progress:.1f}% ({total_processed:,}/{total_estimated:,})')
                
            except discord.Forbidden:
                print('❌ 접근 권한 없음')
            except Exception as e:
                print(f'❌ 오류: {str(e)[:50]}...')
    
    # 수집 완료 결과
    print(f'\n📊 메시지 수집 완료!')
    print('=' * 70)
    print(f'   📥 실제 처리: {total_processed:,}개 (예상: {total_estimated:,}개)')
    print(f'   🔍 필터링 결과: {total_filtered:,}개')
    print(f'   📈 필터링 비율: {(total_filtered/total_processed*100):.2f}%' if total_processed > 0 else '   비율: 0%')
    print(f'   🎯 AI 분석 예상 비용: 약 {((total_filtered + 14) // 15 * 5):,}원')
    
    # 맥락 묶기 처리
    if self.collected_messages:
        await self.group_context_messages()
        print(f'   🔗 최종 AI 분석 대상: {len(self.collected_messages)}개 맥락 그룹')    

    async def group_context_messages(self):
        """맥락 묶기 처리 (기존과 동일하지만 async로 변경)"""
        print(f'\n🔗 맥락 묶기 처리 중...')
        
        # 시간순으로 정렬
        all_messages_sorted = sorted(self.collected_messages, key=lambda x: x['created_at'])
        
        # 맥락 그룹 생성 (기존 로직과 동일)
        context_groups = []
        processed_message_ids = set()
        
        for msg in all_messages_sorted:
            if msg['id'] in processed_message_ids:
                continue
            
            # 같은 작성자의 연속 메시지들을 그룹화
            context_messages = [msg]
            processed_message_ids.add(msg['id'])
            
            # 5분 이내의 같은 작성자 메시지들 수집
            for other_msg in all_messages_sorted:
                if (other_msg['author'] == msg['author'] and 
                    other_msg['id'] not in processed_message_ids and
                    (other_msg['created_at'] - msg['created_at']).total_seconds() <= 300):
                    context_messages.append(other_msg)
                    processed_message_ids.add(other_msg['id'])
            
            # 맥락 그룹 생성
            combined_content = ' '.join([m['content'] for m in context_messages])
            
            context_group = {
                'id': f"context_{msg['id']}",
                'content': combined_content,
                'author': msg['author'],
                'channel': msg['channel'],
                'created_at': msg['created_at'],
                'message_count': len(context_messages),
                'is_context_grouped': len(context_messages) > 1,
                'total_length': len(combined_content),
            }
            context_groups.append(context_group)
        
        # 원본 메시지 리스트를 맥락 그룹으로 교체
        self.collected_messages = context_groups
        
        print(f'   ✅ 맥락 묶기 완료: {len(context_groups)}개 그룹')

async def collect_discord_messages():
    """Discord 메시지 수집 메인 함수 (진척도 개선)"""
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
        # 안전한 연결 종료
        try:
            if not collector.is_closed():
                await collector.close()
            print("🔌 Discord 연결이 안전하게 종료되었습니다.")
        except Exception as close_error:
            print(f"⚠️ 연결 종료 중 오류 (무시 가능): {close_error}")
        
        await asyncio.sleep(1)
    
    return collected_messages
