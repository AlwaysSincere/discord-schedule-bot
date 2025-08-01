import openai
import os
import json
import asyncio
import re
from datetime import datetime
import pytz

class ScheduleClassifier:
    def __init__(self):
        """AI 일정 분류기 초기화"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        openai.api_key = api_key
        print("✅ OpenAI API 키 설정 완료 (v0.28.1)")
        
        self.schedules = []
        self.non_schedules = []
        
    def create_classification_prompt(self, messages):
        """메시지 분류를 위한 프롬프트 생성 (정밀 조정 버전)"""
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        prompt = f"""당신은 음악 동아리 Discord 메시지에서 **실제 구체적인 일정**을 분류하는 전문가입니다.

**현재 시간**: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (한국시간)

**✅ 반드시 일정으로 분류해야 하는 것들**:
1. **구체적 시간 + 행동**: "오늘 8시 합주", "2시 20분 콜타임입니다"
2. **확인형 질문**: "오늘 합주 맞죠?", "시간 그대로 하죠?"
3. **일정 공지**: "콜타임입니다", "리허설입니다" (시간 포함)
4. **미래 일정 언급**: "내일 리허설", "8월 8일 리허설"

**❌ 절대 일정이 아닌 것들**:
1. **단순 대답**: "합니다", "맞습니다" (구체적 제안 없이)
   예: "아 합주연습은합니다" → 단순 대답
2. **일반 질문**: "~할 시간 있나요?", "어떻게 해요?"
   예: "기타 바꿀 시간 있갰죠?" → 일반 질문
3. **순서/방법 설명**: "순서대로", "먼저", "방법은"
   예: "다음 리허설은 순서대로 라이트 먼저" → 순서 설명
4. **시간 설명**: "~은 2시간 정도", "~은 15분"
   예: "서곡은 2시간 정도" → 시간 설명
5. **식사/안주 이야기**: "드실", "먹을", "마실"
   예: "합주끝나고 드실 안주랑" → 안주 이야기
6. **기술/장비 논의**: "세팅", "장비", "녹화", "촬영" (일정 맥락 없이)

**정확한 분류를 위한 체크리스트**:
□ 구체적인 시간이나 날짜가 있는가?
□ 명확한 행동 계획이 있는가? 
□ 단순 대답이나 질문이 아닌가?
□ 순서 설명이나 시간 설명이 아닌가?

**실제 분류 예시**:
✅ "오늘 2시 20분 콜타임입니다" → 일정 (공지+시간)
✅ "오늘합주는8시 그대로 하죠?" → 일정 (확인+시간)
✅ "8월 8일 리허설때도 촬영 필요하신가요?" → 일정 (날짜+행동)
❌ "아 합주연습은합니다" → 단순 대답
❌ "공연날은 기타 바꿀 시간 있갰죠?" → 일반 질문
❌ "서곡은 2시간 정도" → 시간 설명
❌ "합주끝나고 드실 안주랑" → 안주 이야기

**분류 기준**:
- 확신도 92% 이상이어야 일정으로 분류
- 의심스러우면 일정 아님으로 분류 (정확도 우선)

JSON 형식으로 답변:

```json
{{
  "schedules": [
    {{
      "message_id": "ID",
      "content": "내용",
      "author": "작성자",
      "channel": "채널",
      "created_at": "시간",
      "schedule_type": "합주|리허설|연습|공연|콜타임",
      "confidence": 0.95,
      "extracted_info": {{
        "when": "구체적 시간",
        "what": "구체적 행동",
        "where": "장소"
      }},
      "reason": "일정 분류 상세 이유"
    }}
  ],
  "non_schedules": [
    {{
      "message_id": "ID",
      "content": "내용",
      "reason": "제외 이유 (단순대답|일반질문|순서설명|시간설명|안주이야기 등)"
    }}
  ]
}}
```

**분석할 메시지들**:
"""
        
        # 메시지 목록 추가
        for i, msg in enumerate(messages[:10]):
            context_info = f" [맥락그룹: {msg.get('message_count', 1)}개 메시지]" if msg.get('is_context_grouped', False) else ""
            
            # 특수문자 제거하여 JSON 오류 방지
            content = msg['content'].replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
            
            prompt += f"""
{i+1}. ID: {msg['id']}
   내용: "{content}"
   작성자: {msg['author']}
   채널: {msg['channel']}
   시간: {msg['created_at'].strftime('%Y-%m-%d %H:%M')}
   맥락: {context_info}
"""
        
        return prompt
    
    async def classify_messages(self, messages):
        """메시지들을 AI로 분류 (정밀 조정 버전)"""
        print(f"🤖 AI 분석 시작: {len(messages)}개 메시지")
        
        if not messages:
            print("❌ 분류할 메시지가 없습니다.")
            return
        
        batch_size = 10
        total_batches = (len(messages) + batch_size - 1) // batch_size
        
        print(f"📊 배치 처리: {total_batches}개 배치 (배치당 {batch_size}개씩)")
        print(f"💰 예상 비용: 약 {total_batches * 6:,}원")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(messages))
            batch_messages = messages[start_idx:end_idx]
            
            print(f"\n📊 배치 {batch_num + 1}/{total_batches}: {len(batch_messages)}개 메시지 분석 중...")
            
            try:
                prompt = self.create_classification_prompt(batch_messages)
                
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "당신은 정밀한 일정 분류 전문가입니다. 확신도 92% 이상인 명확한 일정만 분류하세요."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,  # 낮춰서 더 정확하게
                        max_tokens=2500,
                        presence_penalty=0,
                        frequency_penalty=0
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as api_error:
                    print(f"  ❌ OpenAI API 호출 오류: {api_error}")
                    await asyncio.sleep(2)
                    continue
                
                # JSON 추출 및 정리
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                # JSON 파싱 오류 방지
                response_text = ''.join(char for char in response_text if ord(char) >= 32 or char in '\n\r\t')
                
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as json_error:
                    print(f"  ❌ JSON 파싱 실패: {json_error}")
                    continue
                
                # 엄격한 후처리 검증
                validated_schedules = []
                if 'schedules' in result:
                    for schedule in result['schedules']:
                        confidence = schedule.get('confidence', 0)
                        content = schedule.get('content', '').lower()
                        
                        # 확신도 기준 상향: 92% 이상
                        if confidence < 0.92:
                            print(f"    ⚠️ 낮은 확신도로 제외: {confidence:.1%} - {content[:30]}...")
                            continue
                        
                        # 엄격한 후처리 필터링
                        false_positive_patterns = [
                            r'.*끝나고.*드실',        # "합주끝나고 드실 안주랑"
                            r'.*은\s*합니다$',       # "합주연습은합니다"  
                            r'.*시간\s*있.*\?',      # "시간 있나요?"
                            r'.*순서대로',           # "순서대로"
                            r'.*은\s*\d+시간',       # "서곡은 2시간"
                            r'.*은\s*\d+분',         # "인터미션은 15분"
                            r'안주', r'드실', r'먹을',  # 식사 관련
                        ]
                        
                        is_false_positive = False
                        for pattern in false_positive_patterns:
                            if re.search(pattern, content):
                                print(f"    ⚠️ False Positive 필터로 제외: {pattern} - {content[:30]}...")
                                is_false_positive = True
                                break
                        
                        if not is_false_positive:
                            validated_schedules.append(schedule)
                
                # 검증된 일정만 저장
                self.schedules.extend(validated_schedules)
                print(f"  ✅ 검증된 일정: {len(validated_schedules)}개")
                
                if 'non_schedules' in result:
                    self.non_schedules.extend(result['non_schedules'])
                    print(f"  ❌ 일정 아님: {len(result['non_schedules'])}개")
                
                await asyncio.sleep(1.5)
                
            except Exception as e:
                print(f"  ❌ 배치 처리 오류: {e}")
                continue
        
        self.print_results()
    
    def print_results(self):
        """분석 결과 출력"""
        total_messages = len(self.schedules) + len(self.non_schedules)
        
        print(f"\n🎯 AI 분석 완료!")
        print(f"=" * 70)
        print(f"   📅 일정으로 분류: {len(self.schedules)}개")
        print(f"   💬 일정 아님: {len(self.non_schedules)}개")
        
        if total_messages > 0:
            schedule_ratio = len(self.schedules) / total_messages * 100
            print(f"   📊 일정 비율: {schedule_ratio:.1f}%")
        else:
            print(f"   📊 일정 비율: 0% (분석된 메시지 없음)")
        
        if self.schedules:
            print(f"\n📋 발견된 일정들 (정밀 검증 완료):")
            print("=" * 70)
            for i, schedule in enumerate(self.schedules):
                print(f"\n📅 일정 #{i+1}:")
                print(f"   💬 내용: {schedule.get('content', '')}")
                print(f"   👤 작성자: {schedule.get('author', 'Unknown')}")
                print(f"   🎯 유형: {schedule.get('schedule_type', 'Unknown')}")
                print(f"   🕐 언제: {schedule.get('extracted_info', {}).get('when', '미상')}")
                print(f"   📍 무엇: {schedule.get('extracted_info', {}).get('what', '미상')}")
                print(f"   🎯 확신도: {schedule.get('confidence', 0):.1%}")
                print(f"   💭 이유: {schedule.get('reason', '')}")
        else:
            print(f"\n💡 확실한 일정이 발견되지 않았습니다.")
            print(f"   🎯 정밀 검증으로 확실한 일정만 통과시킵니다.")

async def classify_schedule_messages(messages):
    """메시지 분류 메인 함수"""
    print("🤖 AI 일정 분류를 시작합니다...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 오류: OPENAI_API_KEY가 설정되지 않았습니다!")
        return [], []
    
    classifier = ScheduleClassifier()
    await classifier.classify_messages(messages)
    
    return classifier.schedules, classifier.non_schedules
