import openai
import os
import json
import asyncio
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
        """메시지 분류를 위한 프롬프트 생성 (균형잡힌 버전)"""
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        prompt = f"""당신은 음악 동아리 Discord 메시지에서 일정을 분류하는 전문 AI입니다.

**현재 시간**: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (한국시간)

**✅ 일정으로 분류해야 하는 것들**:
1. **구체적 시간 + 행동**: "오늘 8시 합주", "2시 20분 콜타임입니다", "내일 리허설"
2. **확인형 질문**: "오늘 합주 맞죠?", "시간 그대로 하죠?", "합주는 8시 그대로 하죠?"
3. **일정 공지**: "콜타임입니다", "리허설입니다", "합주 있습니다"
4. **일정 제안**: "~하죠", "~해요", "~합시다" (시간/날짜 포함시)
5. **일정 언급**: "오늘 합주였지", "내일 리허설 있어"

**❌ 일정이 아닌 것들**:
1. **과거 후기**: "어제 연습 어땠어", "지난번 좋았어", "연습 잘했어"
2. **막연한 질문**: "연습 언제 해?", "다음에 뭐 해?", "언제 만날까?"
3. **일반 대화**: "점심 뭐 먹을까", "날씨 좋네", "고생했어"
4. **기술적 논의**: "녹음 파일 어디 있어?", "장비 어떻게 써?"

**분류 기준 (균형잡힌 접근)**:
- 확신도 90% 이상이면 일정으로 분류
- 구체적 시간/날짜가 있으면 일정 가능성 높음
- 행동(합주, 리허설, 콜타임 등)이 명시되면 일정 가능성 높음
- 의심스러우면 일정으로 분류 (False Negative 방지)

**실제 일정 예시들**:
- "오늘 2시 20분 콜타임입니다" → 일정 (공지+시간)
- "오늘 합주는 8시 그대로 하죠?" → 일정 (확인+시간)
- "내일 리허설 있어" → 일정 (날짜+행동)
- "오늘 합주였지" → 일정 (당일 확인)
- "일단 오늘 리허설이 끝나면" → 일정 (현재 진행중인 일정 언급)

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
      "schedule_type": "합주|리허설|연습|공연|회의|콜타임|기타",
      "confidence": 0.92,
      "extracted_info": {{
        "when": "구체적인 시간 (예: 오늘 8시, 내일, 2시 20분)",
        "what": "구체적인 행동 (예: 합주, 리허설, 콜타임)",
        "where": "장소 (알 수 없으면 미정)"
      }},
      "reason": "일정으로 분류한 이유"
    }}
  ],
  "non_schedules": [
    {{
      "message_id": "메시지ID",
      "content": "메시지 내용",
      "reason": "제외 이유"
    }}
  ]
}}
```

**분석할 메시지들**:
"""
        
        # 메시지 목록 추가
        for i, msg in enumerate(messages[:10]):  # 10개로 늘려서 더 많은 컨텍스트 제공
            context_info = f" [맥락그룹: {msg.get('message_count', 1)}개 메시지]" if msg.get('is_context_grouped', False) else ""
            
            prompt += f"""
{i+1}. ID: {msg['id']}
   내용: "{msg['content']}"
   작성자: {msg['author']}
   채널: {msg['channel']}
   시간: {msg['created_at'].strftime('%Y-%m-%d %H:%M')}
   맥락: {context_info}
"""
        
        return prompt
    
    async def classify_messages(self, messages):
        """메시지들을 AI로 분류 (균형잡힌 버전)"""
        print(f"🤖 AI 분석 시작: {len(messages)}개 메시지")
        
        if not messages:
            print("❌ 분류할 메시지가 없습니다.")
            return
        
        # 10개씩 배치 처리 (더 많은 컨텍스트 제공)
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
                            {"role": "system", "content": "당신은 한국어 일정 분류 전문가입니다. False Negative를 방지하기 위해 의심스러우면 일정으로 분류하세요."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,  # 약간 높여서 더 유연한 분류
                        max_tokens=2500,  # 배치 크기 증가로 토큰 수 증가
                        presence_penalty=0,
                        frequency_penalty=0
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as api_error:
                    print(f"  ❌ OpenAI API 호출 오류: {api_error}")
                    print(f"     배치 {batch_num + 1} 건너뛰고 계속 진행합니다...")
                    await asyncio.sleep(2)
                    continue
                
                # JSON 추출
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                result = json.loads(response_text)
                
                # 결과 검증 (완화된 기준)
                validated_schedules = []
                if 'schedules' in result:
                    for schedule in result['schedules']:
                        confidence = schedule.get('confidence', 0)
                        content = schedule.get('content', '').lower()
                        
                        # 완화된 확신도 기준: 90% 이상
                        if confidence < 0.90:
                            print(f"    ⚠️ 낮은 확신도로 제외: {confidence:.1%} - {content[:30]}...")
                            continue
                        
                        # 완화된 패턴 필터링 (명백히 잘못된 것만 제외)
                        clear_exclude_patterns = [
                            r'어제.*어땠',       # "어제 연습 어땠어"
                            r'지난.*어땠',       # "지난번 어땠어"  
                            r'.*었어\s*\?',      # "좋았어?"
                            r'녹음.*있어\?',     # "녹음 있어?"
                            r'점심.*뭐.*먹',     # "점심 뭐 먹을까"
                        ]
                        
                        is_excluded = False
                        for pattern in clear_exclude_patterns:
                            if re.search(pattern, content):
                                print(f"    ⚠️ 명백한 비일정으로 제외: {pattern} - {content[:30]}...")
                                is_excluded = True
                                break
                        
                        if is_excluded:
                            continue
                            
                        validated_schedules.append(schedule)
                
                # 검증된 일정 저장
                self.schedules.extend(validated_schedules)
                print(f"  ✅ 검증된 일정: {len(validated_schedules)}개")
                
                if 'non_schedules' in result:
                    self.non_schedules.extend(result['non_schedules'])
                    print(f"  ❌ 일정 아님: {len(result['non_schedules'])}개")
                
                # API 호출 간격
                await asyncio.sleep(1.5)
                
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON 파싱 오류: {e}")
                print(f"  응답 내용: {response_text[:200]}...")
                
            except Exception as e:
                print(f"  ❌ AI 분석 오류: {e}")
        
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
            if len(self.non_schedules) > 50:
                print(f"   🔍 최근 7일간 일정이 적을 수 있습니다.")
            else:
                print(f"   ⚠️ 필터링이 너무 엄격하거나 실제 일정이 없을 수 있습니다.")

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
