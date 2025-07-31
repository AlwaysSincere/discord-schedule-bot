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
        """메시지 분류를 위한 프롬프트 생성 (엄격한 False Positive 감소 버전)"""
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        prompt = f"""당신은 Discord 메시지에서 **실제 구체적인 일정**만을 찾는 전문가입니다.

**현재 시간**: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (한국시간)

**🚨 절대 일정이 아닌 것들 (엄격하게 제외)**:
1. **단순 대답/응답**: "합니다", "맞습니다", "그렇습니다" (구체적 제안 없이)
   예: "아 합주연습은합니다" → 단순 대답, 일정 아님
2. **질문/의문문**: "~있나요?", "~어때요?", "~괜찮나요?", "~할까요?"
   예: "공연날은 기타 바꿀 시간 있갰죠?" → 질문, 일정 아님
3. **순서/방법 설명**: "순서대로", "먼저", "그다음에", "~는"
   예: "다음 리허설은 순서대로 라이트 먼저" → 순서 설명, 일정 아님
4. **과거형/완료형**: "했어", "됐어", "끝났어", "좋았어"
5. **막연한 미래**: "언젠가", "나중에", "다음에", "공연날은"
6. **감정/바람 표현**: "잘 했으면", "즐겁게", "좋겠어서"
7. **일반적 언급**: "리허설이 끝나면", "공연이 있으면"

**✅ 반드시 일정인 것들만**:
1. **시간 + 구체적 행동**: "오늘 8시 합주", "2시 20분 콜타임입니다"
2. **명확한 제안**: "~하죠?", "~해요", "~합시다" (시간 포함)
3. **확인형 질문**: "오늘 합주 맞죠?", "시간 그대로 하죠?"  
4. **공지/알림**: "콜타임입니다", "리허설입니다" (시간/날짜 포함)

**분류 기준 (극도로 엄격)**:
- 확신도 95% 이상만 일정으로 분류
- 의심스러우면 무조건 일정 아님으로 분류
- 구체적 시간/날짜 + 구체적 행동이 모두 있어야 함
- 단순 대답, 질문, 설명은 무조건 일정 아님

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
      "confidence": 0.95,
      "extracted_info": {{
        "when": "구체적인 시간 (예: 오늘 8시, 2시 20분)",
        "what": "구체적인 행동 (예: 합주, 리허설, 콜타임)",
        "where": "장소 (알 수 없으면 미정)"
      }},
      "reason": "일정으로 분류한 구체적 이유"
    }}
  ],
  "non_schedules": [
    {{
      "message_id": "메시지ID",
      "content": "메시지 내용",
      "reason": "제외 이유 (단순대답|질문|순서설명|과거형|막연한미래 등)"
    }}
  ]
}}
```

**분석할 메시지들**:
"""
        
        # 메시지 목록 추가 (정확도를 위해 8개로 제한)
        for i, msg in enumerate(messages[:8]):
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
        """메시지들을 AI로 분류 (개선된 정확도 버전)"""
        print(f"🤖 AI 분석 시작: {len(messages)}개 메시지")
        
        if not messages:
            print("❌ 분류할 메시지가 없습니다.")
            return
        
        # 8개씩 배치 처리 (정확도 향상을 위해 배치 크기 감소)
        batch_size = 8
        total_batches = (len(messages) + batch_size - 1) // batch_size
        
        print(f"📊 배치 처리: {total_batches}개 배치 (배치당 {batch_size}개씩)")
        print(f"💰 예상 비용: 약 {total_batches * 5:,}원")
        
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
                            {"role": "system", "content": "당신은 한국어 일정 분류 전문가입니다. False Positive를 최소화하여 확실한 일정만 분류하세요."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,  # 일관된 결과를 위해 낮게 설정
                        max_tokens=2000,  # 배치 크기 감소로 토큰 수 조정
                        presence_penalty=0,
                        frequency_penalty=0
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as api_error:
                    print(f"  ❌ OpenAI API 호출 오류: {api_error}")
                    print(f"     배치 {batch_num + 1} 건너뛰고 계속 진행합니다...")
                    await asyncio.sleep(2)
                    continue
                
                # JSON 추출 (```json 태그 제거)
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                result = json.loads(response_text)
                
                # 결과 검증 및 필터링 (더 엄격하게)
                validated_schedules = []
                if 'schedules' in result:
                    for schedule in result['schedules']:
                        confidence = schedule.get('confidence', 0)
                        content = schedule.get('content', '').lower()
                        
                        # 추가 검증: 확신도 95% 이상만 통과
                        if confidence < 0.95:
                            print(f"    ⚠️ 낮은 확신도로 제외: {confidence:.1%} - {content[:30]}...")
                            continue
                        
                        # 엄격한 False Positive 필터링
                        exclude_patterns = [
                            '합니다$', '그렇습니다$', '맞습니다$',  # 단순 대답
                            r'\?$', '있나요', '어때요', '괜찮나요',  # 질문
                            '순서대로', '먼저', '그다음',  # 순서 설명
                            '했어$', '됐어$', '끝났어$',  # 과거형
                            '좋겠어', '즐겁게', '잘 했으면',  # 감정
                        ]
                        
                        is_excluded = False
                        for pattern in exclude_patterns:
                            if re.search(pattern, content):
                                print(f"    ⚠️ 패턴 매칭으로 제외: {pattern} - {content[:30]}...")
                                is_excluded = True
                                break
                        
                        if is_excluded:
                            continue
                            
                        validated_schedules.append(schedule)
                
                # 검증된 일정만 저장
                self.schedules.extend(validated_schedules)
                print(f"  ✅ 검증된 일정: {len(validated_schedules)}개")
                
                if 'non_schedules' in result:
                    self.non_schedules.extend(result['non_schedules'])
                    print(f"  ❌ 일정 아님: {len(result['non_schedules'])}개")
                
                # API 호출 간격 (안정성을 위해)
                await asyncio.sleep(1.5)
                
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON 파싱 오류: {e}")
                print(f"  응답 내용: {response_text[:200]}...")
                
            except Exception as e:
                print(f"  ❌ AI 분석 오류: {e}")
        
        # 최종 결과 출력
        self.print_results()
    
    def print_results(self):
        """분석 결과 출력 (개선된 버전)"""
        total_messages = len(self.schedules) + len(self.non_schedules)
        
        print(f"\n🎯 AI 분석 완료!")
        print(f"=" * 70)
        print(f"   📅 일정으로 분류: {len(self.schedules)}개")
        print(f"   💬 일정 아님: {len(self.non_schedules)}개")
        
        # 0으로 나누기 방지
        if total_messages > 0:
            schedule_ratio = len(self.schedules) / total_messages * 100
            print(f"   📊 일정 비율: {schedule_ratio:.1f}%")
        else:
            print(f"   📊 일정 비율: 0% (분석된 메시지 없음)")
        
        if self.schedules:
            print(f"\n📋 발견된 일정들 (상세):")
            print("=" * 70)
            for i, schedule in enumerate(self.schedules):
                print(f"\n📅 일정 #{i+1}:")
                print(f"   💬 내용: {schedule.get('content', '')}")
                print(f"   👤 작성자: {schedule.get('author', 'Unknown')}")
                print(f"   📝 채널: {schedule.get('channel', 'Unknown')}")
                print(f"   🎯 유형: {schedule.get('schedule_type', 'Unknown')}")
                print(f"   🕐 언제: {schedule.get('extracted_info', {}).get('when', '미상')}")
                print(f"   📍 무엇: {schedule.get('extracted_info', {}).get('what', '미상')}")
                print(f"   📍 어디서: {schedule.get('extracted_info', {}).get('where', '미상')}")
                print(f"   🎯 확신도: {schedule.get('confidence', 0):.1%}")
                print(f"   💭 이유: {schedule.get('reason', '')}")
                
                # 맥락 그룹 정보
                if schedule.get('is_context_group', False):
                    print(f"   🔗 맥락 그룹: {schedule.get('message_count', 1)}개 메시지")
        else:
            print(f"\n💡 일정으로 분류된 메시지가 없습니다.")
            print(f"   🔍 엄격한 필터링으로 인해 확실한 일정만 통과했습니다.")
        
        # 제외된 메시지 요약
        if self.non_schedules:
            print(f"\n❌ 제외된 메시지들의 주요 이유:")
            exclude_reasons = {}
            for non_schedule in self.non_schedules[:15]:  # 상위 15개만 분석
                reason = non_schedule.get('reason', '기타')
                exclude_reasons[reason] = exclude_reasons.get(reason, 0) + 1
            
            for reason, count in sorted(exclude_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {reason}: {count}개")

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
