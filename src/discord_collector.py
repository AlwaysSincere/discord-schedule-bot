# Discord message collector
import discord
import os
import asyncio

# Discord 봇 클래스 정의
class ScheduleBot(discord.Client):
    def __init__(self):
        # Discord 봇 초기화
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용 읽기 권한
        intents.guilds = True           # 서버 정보 접근 권한
        super().__init__(intents=intents)
    
    async def on_ready(self):
        """봇이 성공적으로 로그인했을 때 실행되는 함수"""
        print(f'🎉 봇이 성공적으로 로그인했습니다!')
        print(f'봇 이름: {self.user}')
        print(f'봇 ID: {self.user.id}')
        
        # 봇이 참가한 서버 목록 출력
        print(f'\n📋 참가한 서버 목록:')
        for guild in self.guilds:
            print(f'  - {guild.name} (ID: {guild.id})')
        
        # 간단한 테스트: 첫 번째 서버의 채널 목록 확인
        if self.guilds:
            first_guild = self.guilds[0]
            print(f'\n📝 "{first_guild.name}" 서버의 채널 목록:')
            for channel in first_guild.text_channels:
                print(f'  - #{channel.name} (ID: {channel.id})')
        
        # 테스트 완료 후 봇 종료
        print(f'\n✅ 연결 테스트 완료! 봇을 종료합니다.')
        await self.close()

# 메인 실행 함수
async def test_discord_connection():
    """Discord 봇 연결을 테스트하는 함수"""
    print("🔗 Discord 연결 테스트를 시작합니다...")
    
    # 환경변수에서 Discord 토큰 가져오기
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ 오류: DISCORD_TOKEN이 설정되지 않았습니다!")
        print("GitHub Secrets에 DISCORD_TOKEN을 설정했는지 확인해주세요.")
        return
    
    # 봇 인스턴스 생성 및 실행
    bot = ScheduleBot()
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ 로그인 실패: Discord 토큰이 잘못되었습니다!")
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")

# 이 파일이 직접 실행될 때만 테스트 수행
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Discord Schedule Bot - 연결 테스트")
    print("=" * 50)
    
    # 비동기 함수 실행
    asyncio.run(test_discord_connection())
