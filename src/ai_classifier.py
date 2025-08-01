import openai
import os
import json
import asyncio
import re  # 🚨 누락된 import 추가
from datetime import datetime
import pytz

class ScheduleClassifier:
    def __init__(self):
        """AI 일정 분류기 초기화"""
        # OpenAI API 키 설정 (v0.28.1 방식)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        # v0.28.1 방식으로 API 키 설정
        openai.api_key = api_key
        print("✅ OpenAI API 키 설정 완료 (v0.28.1)")
        
        # 분류 결과 저장
        self.schedules = []
        self.non_schedules = []
        
    def create_classification_prompt(self, messages):
        """메시지 분류를 위한 프롬프트 생성 (관대한 버전)"""
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        prompt = f"""당신은 음악 동아리 Discord 메시지에서 일정을 찾는 AI입니다.

**현재 시간**: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (한국시간)

**🎯 일정 분류 원칙: 관대하게 접근하세요**

**✅ 이런 것들은 모두 일정입니다**:
1. **미래의 활동 언급**: "내일 리허설", "오늘 합주", "다음 연습"
2. **시간이 포함된 모든 것**: "8시", "2시 20분", "몇시"
3. **일정 관련 단어**: 합주, 리허설, 연습, 콘서트, 공연, 콜타임, 세팅
4. **확인/제안**: "하죠?", "어때요?", "맞죠?", "할까요?"
5. **공지/알림**: "~입니다", "~해요", "~합시다"
6. **현재 진행형**: "오늘 리허설이 끝나면", "지금 연습 중"

**실제 일정 예시들 (모두 일정으로 분류해야 함)**:
- "내일 저희 리허설 즐겁게 잘 했으면 좋겠어서 공지를 함 쓰겠음니다!" → 일정
- "오늘 2시 20분 콜타임입니다" → 일정
- "오늘 합주는 8시 그대로 하죠?" → 일정
- "내일 리허설 있어" → 일정
- "일단 오늘 리허설이 끝나면" → 일정
- "다음 합주 언제 해?" → 일정
- "합주연습은 합니다" → 일정

**❌ 명백히 일정이 아닌 것만**:
1. **과거 완료**: "어제 연습했어", "지난번 좋았어"
2. **일반 대화**: "점심 뭐 먹을까", "날씨 좋네"
3. **기술 질문**: "녹음 파일 어디 있어?", "장비 어떻게 써?"

**분류 기준**:
- 확신도 85% 이상이면 일정으로 분류
- 의심스러우면 일정으로 분류 (False Negative 절대 방지)
- 음악 활동 관련이면 대부분 일정 가능성 높음

JSON 형식으로 답변 (특수문자 사용 금지):

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
      "confidence": 0.92,
      "extracted_info": {{
        "when": "시간정보",
        "what": "행동",
        "where": "장소"
      }},
      "reason": "일정 분류 이유"
    }}
  ],
  "non_schedules": [
    {{
      "message_id": "ID",
      "content": "내용",
      "reason": "제외 이유"
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
        """메시지들을 AI로 분류 (관대한 버전)"""
        print(f"🤖 AI 분석 시작: {len(messages)}개 메시지")
        
        if not messages:
            print("❌ 분류할 메시지가 없습니다.")
            return
        
        # 10개씩 배치 처리
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
                # AI 분석 요청
                prompt = self.create_classification_prompt(batch_messages)
                
                try:
                    # v0.28.1 방식으로 ChatCompletion 호출
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "당신은 일정 분류 전문가입니다. 의심스러우면 일정으로 분류하세요. False Negative를 절대 방지하세요."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,  # 약간 높여서 더 관대하게
                        max_tokens=2500,
                        presence_penalty=0,
                        frequency_penalty=0
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as api_error:
                    print(f"  ❌ OpenAI API 호출 오류: {api_error}")
                    print(f"     배치 {batch_num + 1} 건너뛰고 계속 진행합니다...")
                    await asyncio.sleep(2)
                    continue
                
                # JSON 추출 및 정리
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                # 🚨 JSON 파싱 오류 방지: 제어 문자 제거
                response_text = ''.join(char for char in response_text if ord(char) >= 32 or char in '\n\r\t')
                
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as json_error:
                    print(f"  ❌ JSON 파싱 실패: {json_error}")
                    print(f"  응답 일부: {response_text[:100]}...")
                    continue
                
                # 결과 검증 (매우 관대한 기준)
                validated_schedules = []
                if 'schedules' in result:
                    for schedule in result['schedules']:
                        confidence = schedule.get('confidence', 0)
                        content = schedule.get('content', '').lower()
                        
                        # 🚨 관대한 확신도 기준: 85% 이상
                        if confidence < 0.85:
                            print(f"    ⚠️ 낮은 확신도로 제외: {confidence:.1%} - {content[:30]}...")
                            continue
                        
                        # 🚨 매우 제한적인 제외 패턴 (명백히 잘못된 것만)
                        clear_past_patterns = [
                            r'어제.*어땠',       # "어제 연습 어땠어"
                            r'지난.*어땠',       # "지난번 어땠어"  
                            r'점심.*뭐.*먹',     # "점심 뭐 먹을까"
                            r'날씨.*좋',         # "날씨 좋네"
                        ]
                        
                        is_excluded = False
                        for pattern in clear_past_patterns:
                            if re.search(pattern, content):
                                print(f"    ⚠️ 명백한 과거/일반대화로 제외: {content[:30]}...")
                                is_excluded = True
                                break
                        
                        if not is_excluded:
                            validated_schedules.append(schedule)
                
                # 검증된 일정 저장
                self.schedules.extend(validated_schedules)
                print(f"  ✅ 검증된 일정: {len(validated_schedules)}개")
                
                if 'non_schedules' in result:
                    self.non_schedules.extend(result['non_schedules'])
                    print(f"  ❌ 일정 아님: {len(result['non_schedules'])}개")
                
                # API 호출 간격
                await asyncio.sleep(1.5)
                
            except Exception as e:
                print(f"  ❌ 배치 처리 오류: {e}")
                continue
        
        # 최종 결과 출력
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
            print(f"\n📋 발견된 일정들:")
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
            print(f"\n💡 일정으로 분류된 메시지가 없습니다.")
            print(f"   ⚠️ 최근 7일간 실제 일정이 없거나 AI가 여전히 보수적일 수 있습니다.")

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
