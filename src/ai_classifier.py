import openai
import os
import json
import asyncio
from datetime import datetime
import pytz

class ScheduleClassifier:
    def __init__(self):
        """AI 일정 분류기 초기화"""
        # OpenAI API 키 설정
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        # OpenAI 클라이언트 초기화 (버전 호환성 개선)
        try:
            self.client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 실패: {e}")
            # 이전 버전 호환성을 위한 대체 방법
            openai.api_key = api_key
            self.client = None
        
        # 분류 결과 저장
        self.schedules = []
        self.non_schedules = []
        
    def create_classification_prompt(self, messages):
        """메시지 분류를 위한 프롬프트 생성"""
        
        # 현재 시간 (한국 시간대)
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        prompt = f"""당신은 음악 동아리 Discord 메시지에서 일정을 분류하는 전문 AI입니다.

**현재 시간**: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (한국시간)

**음악 동아리 "✨동아리 밴드✨" 특성**:
- 합주, 리허설, 공연 준비가 주요 활동
- 연습실, 스튜디오에서 활동
- 크레비쥬 공연 등 정기 이벤트 있음
- 멤버들이 끊어서 채팅하는 경우 많음 (맥락 그룹으로 합쳐서 제공)

**분류 기준**:
✅ **일정으로 분류해야 할 것들**:
- 합주, 리허설, 연습 일정 (예: "오늘합주는8시", "리허설 언제")
- 공연, 콘서트 준비 관련 (예: "공연 준비 모임", "콘서트 세팅")
- 회의, 모임 약속 (예: "회의 언제 할까", "밴드 회의")
- 구체적 시간/날짜 제안 (예: "3시에 연습실", "월요일 스튜디오")
- 일정 확인/조율 (예: "시간 괜찮나요?", "언제 가능하세요?")

❌ **일정이 아닌 것들**:
- 일반 잡담 (예: "아침밥 뭐 먹을까", "게임 어때요")
- 과거 활동 후기 (예: "어제 연습 어땠어")
- 단순 질문/대화 (예: "괜찮은 거 같나요?")
- 개인적 계획 공유 (예: "오늘 헬스장 가야지")

**맥락 그룹 처리**:
- 여러 메시지가 합쳐진 경우, 전체 맥락을 고려하여 판단
- 끊어진 메시지들이 합쳐져서 완전한 일정 제안이 된 경우 일정으로 분류

다음 메시지들을 분석해서 JSON 형식으로 답변해주세요:

```json
{{
  "schedules": [
    {{
      "message_id": "메시지ID",
      "content": "전체 메시지 내용",
      "author": "작성자",
      "channel": "채널명",
      "created_at": "작성시간",
      "schedule_type": "합주|리허설|연습|공연|회의|모임|기타",
      "confidence": 0.95,
      "extracted_info": {{
        "when": "언제 (예: 오늘 8시, 내일 오후)",
        "what": "무엇을 (예: 합주, 리허설, 회의)",
        "where": "어디서 (예: 연습실, 스튜디오)"
      }},
      "reason": "일정으로 분류한 이유",
      "is_context_group": true,
      "message_count": 3
    }}
  ],
  "non_schedules": [
    {{
      "message_id": "메시지ID", 
      "content": "메시지 내용",
      "reason": "일정이 아닌 이유"
    }}
  ]
}}
```

**분석할 메시지들**:
"""
        
        # 메시지 목록 추가 (최대 20개씩 처리)
        for i, msg in enumerate(messages[:20]):
            # 맥락 그룹 정보 포함
            is_context_group = msg.get('is_context_grouped', False)
            message_count = msg.get('message_count', 1)
            context_info = f" [맥락그룹: {message_count}개 메시지]" if is_context_group else ""
            
            prompt += f"""
{i+1}. ID: {msg['id']}
   내용: "{msg['content']}"
   작성자: {msg['author']}
   채널: {msg['channel']}
   시간: {msg['created_at'].strftime('%Y-%m-%d %H:%M')}
   키워드: {msg.get('keywords_found', [])}
   맥락: {context_info}
"""
        
        return prompt
    
    async def classify_messages(self, messages):
        """메시지들을 AI로 분류"""
        print(f"🤖 AI 분석 시작: {len(messages)}개 메시지")
        
        if not messages:
            print("❌ 분류할 메시지가 없습니다.")
            return
        
        # 20개씩 배치 처리 (API 제한 고려)
        batch_size = 20
        total_batches = (len(messages) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(messages))
            batch_messages = messages[start_idx:end_idx]
            
            print(f"📊 배치 {batch_num + 1}/{total_batches}: {len(batch_messages)}개 메시지 분석 중...")
            
            try:
                # AI 분석 요청
                prompt = self.create_classification_prompt(batch_messages)
                
                try:
                    if self.client:
                        # 새로운 클라이언트 방식
                        response = self.client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "당신은 정확한 일정 분류 전문가입니다. 한국어 메시지를 분석하여 JSON 형식으로 응답해주세요."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.1,  # 일관된 결과를 위해 낮게 설정
                            max_tokens=2000
                        )
                        response_text = response.choices[0].message.content.strip()
                    else:
                        # 이전 방식 (호환성)
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "당신은 정확한 일정 분류 전문가입니다. 한국어 메시지를 분석하여 JSON 형식으로 응답해주세요."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.1,
                            max_tokens=2000
                        )
                        response_text = response.choices[0].message.content.strip()
                    
                except Exception as api_error:
                    print(f"  ❌ OpenAI API 호출 오류: {api_error}")
                    print(f"     재시도하거나 다른 방식을 시도합니다...")
                    continue
                
                # JSON 추출 (```json 태그 제거)
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                result = json.loads(response_text)
                
                # 결과 저장
                if 'schedules' in result:
                    self.schedules.extend(result['schedules'])
                    print(f"  ✅ 일정 발견: {len(result['schedules'])}개")
                
                if 'non_schedules' in result:
                    self.non_schedules.extend(result['non_schedules'])
                    print(f"  ❌ 일정 아님: {len(result['non_schedules'])}개")
                
                # API 호출 간격 (비용 절약 및 제한 방지)
                await asyncio.sleep(1)
                
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON 파싱 오류: {e}")
                print(f"  응답 내용: {response_text[:200]}...")
                
            except Exception as e:
                print(f"  ❌ AI 분석 오류: {e}")
        
        # 최종 결과 출력
        self.print_results()
    
    def print_results(self):
        """분석 결과 출력"""
        print(f"\n🎯 AI 분석 완료!")
        print(f"   📅 일정으로 분류: {len(self.schedules)}개")
        print(f"   💬 일정 아님: {len(self.non_schedules)}개")
        print(f"   📊 일정 비율: {len(self.schedules)/(len(self.schedules)+len(self.non_schedules))*100:.1f}%")
        
        if self.schedules:
            print(f"\n📋 발견된 일정들:")
            for i, schedule in enumerate(self.schedules[:5]):  # 상위 5개만 표시
                print(f"   {i+1}. [{schedule.get('channel', 'Unknown')}] {schedule.get('content', '')[:50]}...")
                print(f"      🎯 유형: {schedule.get('schedule_type', 'Unknown')}")
                print(f"      🕐 언제: {schedule.get('extracted_info', {}).get('when', '미상')}")
                print(f"      📍 무엇: {schedule.get('extracted_info', {}).get('what', '미상')}")
                print(f"      🎯 확신도: {schedule.get('confidence', 0):.2f}")
                print()
        
        if len(self.schedules) > 5:
            print(f"   ... 및 {len(self.schedules) - 5}개 추가 일정")

async def classify_schedule_messages(messages):
    """메시지 분류 메인 함수"""
    print("🤖 AI 일정 분류를 시작합니다...")
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 오류: OPENAI_API_KEY가 설정되지 않았습니다!")
        return [], []
    
    # 분류기 실행
    classifier = ScheduleClassifier()
    await classifier.classify_messages(messages)
    
    return classifier.schedules, classifier.non_schedules

# 테스트용 메인 함수
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI Schedule Classifier - 테스트")
    print("=" * 60)
    
    # 샘플 메시지로 테스트
    sample_messages = [
        {
            'id': '12345',
            'content': '내일 오후 3시에 연습실에서 합주 어떠세요?',
            'author': '홍길동',
            'channel': '#📅일정',
            'created_at': datetime.now(pytz.timezone('Asia/Seoul')),
            'keywords_found': ['내일', '연습']
        },
        {
            'id': '12346', 
            'content': '점심 뭐 먹을까요?',
            'author': '김철수',
            'channel': '#💬잡담',
            'created_at': datetime.now(pytz.timezone('Asia/Seoul')),
            'keywords_found': []
        }
    ]
    
    async def test():
        schedules, non_schedules = await classify_schedule_messages(sample_messages)
        print(f"\n🎯 테스트 결과: 일정 {len(schedules)}개, 비일정 {len(non_schedules)}개")
    
    asyncio.run(test())
