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
        """메시지 분류를 위한 프롬프트 생성 (개선된 버전)"""
        
        # 현재 시간 (한국 시간대)
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        prompt = f"""당신은 음악 동아리 Discord 메시지에서 일정을 분류하는 전문 AI입니다.

**현재 시간**: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (한국시간)

**음악 동아리 "✨동아리 밴드✨" 특성**:
- 합주, 리허설, 공연 준비가 주요 활동
- 연습실, 스튜디오에서 활동
- 크레비쥬 공연 등 정기 이벤트 있음
- 멤버들이 끊어서 채팅하는 경우 많음

**❗ 중요: 다음은 일정이 아닙니다 ❗**:
1. **과거 이야기**: "어제 연습 어땠어", "지난번 공연 좋았어"
2. **단순 질문**: "혹시 ~ 있나요?", "~ 어떻게 생각해요?"
3. **녹음/영상 문의**: "~ 녹음된 거 있어?", "영상 봤어?"
4. **일반 대화**: "점심 뭐 먹을까", "날씨 좋네"
5. **감상/후기**: "~ 어땠어", "좋았어", "재밌었어"
6. **완료된 일**: "~ 끝났어", "~ 했어"

**✅ 일정으로 분류해야 할 것들**:
1. **구체적 제안**: "내일 3시에 연습실에서 합주해요"
2. **시간 조율**: "언제 만날까요?", "몇 시가 좋을까요?"
3. **일정 확인**: "내일 리허설 맞죠?", "시간 변경 어때요?"
4. **공지성 일정**: "오늘 2시 20분 콜타임입니다"
5. **계획 제안**: "다음주에 연습 어때요?"

**분류 기준 (더 엄격하게)**:
- 미래 시점의 구체적인 행동 계획이 있어야 함
- 시간이나 날짜가 언급되거나 암묵적으로 포함되어야 함
- 확신도가 85% 미만이면 일정 아님으로 분류
- 과거형 동사나 완료형이 주가 되면 일정 아님

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
        "when": "언제 (구체적으로: 오늘 2시 20분, 내일 오후)",
        "what": "무엇을 (예: 합주, 리허설, 콜타임)",
        "where": "어디서 (예: 연습실, 스튜디오)"
      }},
      "reason": "일정으로 분류한 상세 이유",
      "is_context_group": true,
      "message_count": 3
    }}
  ],
  "non_schedules": [
    {{
      "message_id": "메시지ID", 
      "content": "메시지 내용",
      "reason": "일정이 아닌 구체적 이유 (과거형/질문/완료 등)"
    }}
  ]
}}
```

**분석할 메시지들**:
"""
        
        # 메시지 목록 추가 (최대 15개씩 처리 - 더 정확한 분석을 위해 줄임)
        for i, msg in enumerate(messages[:15]):
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
        """메시지들을 AI로 분류 (개선된 버전)"""
        print(f"🤖 AI 분석 시작: {len(messages)}개 메시지")
        
        if not messages:
            print("❌ 분류할 메시지가 없습니다.")
            return
        
        # 15개씩 배치 처리 (더 정확한 분석을 위해 배치 크기 줄임)
        batch_size = 15
        total_batches = (len(messages) + batch_size - 1) // batch_size
        
        print(f"📊 배치 처리: {total_batches}개 배치 (배치당 {batch_size}개씩)")
        print(f"💰 예상 비용: 약 {total_batches * 5:,}원")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(messages))
            batch_messages = messages[start_idx:end_idx]
            
            print(f"\n📊 배치 {batch_num + 1}/{total_batches}: {len(batch_messages)}개 메시지 분석 중...")
            
            try:
                # AI 분석 요청 (v0.28.1 방식)
                prompt = self.create_classification_prompt(batch_messages)
                
                try:
                    # v0.28.1 방식으로 ChatCompletion 호출 (더 안정적인 설정)
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "당신은 한국어 일정 분류 전문가입니다. 과거형 질문과 미래 일정을 정확히 구분해주세요. 확신도가 낮으면 일정이 아닌 것으로 분류하세요."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,  # 일관된 결과를 위해 낮게 설정
                        max_tokens=3000,  # 더 상세한 분석을 위해 증가
                        presence_penalty=0,
                        frequency_penalty=0
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as api_error:
                    print(f"  ❌ OpenAI API 호출 오류: {api_error}")
                    print(f"     배치 {batch_num + 1} 건너뛰고 계속 진행합니다...")
                    await asyncio.sleep(2)  # 오류 후 대기 시간 증가
                    continue
                
                # JSON 추출 (```json 태그 제거)
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                result = json.loads(response_text)
                
                # 결과 검증 및 필터링
                validated_schedules = []
                if 'schedules' in result:
                    for schedule in result['schedules']:
                        confidence = schedule.get('confidence', 0)
                        content = schedule.get('content', '').lower()
                        
                        # 추가 검증: 확신도 기반 필터링
                        if confidence < 0.85:
                            print(f"    ⚠️ 낮은 확신도로 제외: {confidence:.1%} - {content[:30]}...")
                            continue
                        
                        # 과거형 패턴 재검증
                        past_patterns = ['었어', '했어', '됐어', '끝났어', '좋았어', '어땠어']
                        question_patterns = ['있나요', '있어?', '어때요', '어떻게']
                        
                        if any(pattern in content for pattern in past_patterns):
                            print(f"    ⚠️ 과거형 패턴으로 제외: {content[:30]}...")
                            continue
                            
                        if any(pattern in content for pattern in question_patterns) and confidence < 0.9:
                            print(f"    ⚠️ 질문형+낮은확신도로 제외: {content[:30]}...")
                            continue
                        
                        validated_schedules.append(schedule)
                
                # 검증된 일정만 저장
                self.schedules.extend(validated_schedules)
                print(f"  ✅ 검증된 일정: {len(validated_schedules)}개")
                
                if 'non_schedules' in result:
                    self.non_schedules.extend(result['non_schedules'])
                    print(f"  ❌ 일정 아님: {len(result['non_schedules'])}개")
                
                # API 호출 간격 (비용 절약 및 제한 방지)
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
            print(f"   🔍 키워드 필터링이 너무 엄격하거나 실제 일정이 없을 수 있습니다.")
        
        # 주요 제외 이유 분석
        if self.non_schedules:
            print(f"\n❌ 제외된 메시지들의 주요 이유:")
            exclude_reasons = {}
            for non_schedule in self.non_schedules[:10]:  # 상위 10개만 분석
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
