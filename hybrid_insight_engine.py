# -*- coding: utf-8 -*-
# hybrid_insight_engine.py - GPT 3단계 검증 + Claude 4가지 경쟁 전략

import os
import json
import asyncio
import re
from datetime import datetime
from openai import OpenAI
from anthropic import Anthropic

# API 클라이언트
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


# ==================== STEP 1: GPT-4o 3단계 전처리 ====================

def preprocess_with_gpt(target_store, target_reviews, competitors, competitor_reviews, statistical_comparison):
    """GPT-4o: 3단계 전처리 (1:분류 → 2:부정 재검증 → 3:추출)"""
    
    print(f"\n{'='*60}")
    print(f"⚡ STEP 1: GPT-4o 전처리 (3단계 검증)")
    print(f"{'='*60}")
    
    # 150개 리뷰
    sample_reviews = target_reviews[:150]
    print(f"   📝 분석 리뷰: {len(sample_reviews)}개")
    
    # ========== 1단계: 리뷰별 긍/부정 분류 (넓게) ==========
    print(f"\n   🔍 1단계: 긍정/부정 분류 (부정 넓게 잡기)...")
    
    reviews_for_classification = "\n".join([
        f"[리뷰#{i+1}] {r['content'][:200]}" 
        for i, r in enumerate(sample_reviews)
    ])
    
    classification_prompt = f"""당신은 리뷰 분석 전문가입니다. {len(sample_reviews)}개 리뷰를 긍정/부정/중립로 분류하세요.

🎯 **1단계 목표**: 부정 가능성이 있는 것들을 **넓게** 잡기 (놓치지 말 것!)

## 부정 판단 (하나라도 해당하면 부정)

- "맛없", "별로", "실망", "아쉽", "후회", "최악", "비추"
- "불친절", "퉁명", "무뚝뚝"
- "비싸", "비쌈", "가격대비", "부담"
- "미지근", "식", "차갑"
- "더럽", "지저분", "벌레", "냄새"
- "웨이팅길", "오래기다"
- "~해주세요" + ㅜㅜ, ㅠㅠ (개선 요청)
- "~신경써주세요" (현재 안 좋다는 뜻)
- "그나마", "그럭저럭", "나쁘진않"
- "차라리 ~가세요", "다른데 가세요"
- "???" + 불만 문맥
- 혼합: "맛있는데 비싸요" → 부정

## 리뷰
{reviews_for_classification}

## JSON 출력

{{
  "분류결과": [
    {{"review_id": 1, "sentiment": "부정", "snippet": "맛을 신경써주세요"}},
    {{"review_id": 2, "sentiment": "긍정", "snippet": "완전 맛있어요"}}
  ],
  "요약": {{"부정": 45, "긍정": 92, "중립": 13}}
}}
"""
    
    try:
        # 1단계 실행
        response_1 = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "리뷰 분석 전문가. 부정 신호를 놓치지 마세요."},
                {"role": "user", "content": classification_prompt}
            ],
            temperature=0.0,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )
        
        classification_result = json.loads(response_1.choices[0].message.content)
        summary = classification_result.get('요약', {})
        
        print(f"      ✅ 1단계 완료")
        print(f"         부정: {summary.get('부정', 0)}개")
        print(f"         긍정: {summary.get('긍정', 0)}개")
        print(f"         중립: {summary.get('중립', 0)}개")
        
        # ========== 2단계: 부정 리뷰만 재검증 (오탐 제거!) ==========
        print(f"\n   🛡️  2단계: 부정 리뷰 재검증 (오탐 제거)...")
        
        classified_reviews = classification_result.get('분류결과', [])
        negative_reviews_for_verification = []
        
        for item in classified_reviews:
            if item['sentiment'] == "부정":
                review_id = item['review_id']
                review_content = sample_reviews[review_id - 1]['content']
                negative_reviews_for_verification.append({
                    "review_id": review_id,
                    "content": review_content[:250]
                })
        
        verification_text = "\n".join([
            f"[리뷰#{r['review_id']}] {r['content']}"
            for r in negative_reviews_for_verification
        ])
        
        verification_prompt = f"""🚨 **CRITICAL 미션**: 부정으로 분류된 {len(negative_reviews_for_verification)}개 리뷰를 재검증하세요.

**목표**: 오탐(False Positive) 제거 - 긍정을 부정으로 잘못 분류한 것 찾기!

## 오탐 사례 (반드시 제외!)

### ❌ 제외해야 할 것들
1. **단순 기대/바람** (현재 불만 아님)
   - "매장 넓혀주세요 ㅎㅎ" → 긍정 (기대)
   - "집 근처에 있으면 좋겠어요" → 긍정 (바람)
   - "다른 메뉴도 나왔으면" → 긍정 (제안)

2. **긍정 + 무해한 제안**
   - "완전 맛있어요! 양 좀 더 많았으면" → 긍정
   - "분위기 좋아요~ 주차장 있었으면" → 긍정

3. **단순 사실 나열**
   - "웨이팅 있었어요" (불만 없음) → 중립

### ✅ 유지해야 할 진짜 부정
1. **명백한 불만**
   - "맛없어요", "별로예요", "실망했어요"
   - "비싸요", "불친절해요", "더러워요"

2. **개선 요청 + 불만 표시**
   - "맛을 신경써주세요ㅜㅜ" → 부정 (현재 별로)
   - "청결 좀 해주세요..." → 부정 (현재 더러움)

3. **조롱/비추천**
   - "차라리 ~가세요", "돈 아까워요"

4. **혼합 (단점 포함)**
   - "맛있는데 비싸요" → 부정 유지

## 재검증 대상 리뷰
{verification_text}

## JSON 출력

{{
  "재검증_결과": [
    {{"review_id": 1, "최종판정": "부정", "이유": "맛 불만 명시"}},
    {{"review_id": 5, "최종판정": "긍정으로변경", "이유": "단순 기대 표현, 불만 없음"}},
    {{"review_id": 8, "최종판정": "부정", "이유": "가격 불만 + 조롱"}}
  ],
  "요약": {{
    "진짜부정": 38,
    "오탐제거": 7
  }}
}}

**규칙**: 50개 중 1개 오탐도 안됨! 확실한 부정만 남기기!
"""
        
        response_2 = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "엄격한 검증자. 오탐을 절대 허용하지 마세요."},
                {"role": "user", "content": verification_prompt}
            ],
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        verification_result = json.loads(response_2.choices[0].message.content)
        verification_summary = verification_result.get('요약', {})
        
        print(f"      ✅ 2단계 완료")
        print(f"         진짜 부정: {verification_summary.get('진짜부정', 0)}개")
        print(f"         오탐 제거: {verification_summary.get('오탐제거', 0)}개")
        
        # ========== 3단계: 검증된 부정으로 장단점 추출 ==========
        print(f"\n   📊 3단계: 장단점 추출...")
        
        # 최종 부정/긍정 리스트 생성
        verified_negatives = []
        positives = []
        
        verification_map = {
            item['review_id']: item['최종판정']
            for item in verification_result.get('재검증_결과', [])
        }
        
        for item in classified_reviews:
            review_id = item['review_id']
            sentiment = item['sentiment']
            review_content = sample_reviews[review_id - 1]['content'][:250]
            
            # 재검증 결과 반영
            if review_id in verification_map:
                final_sentiment = verification_map[review_id]
                if "긍정" in final_sentiment or "중립" in final_sentiment:
                    sentiment = "긍정"  # 오탐 제거됨
            
            if sentiment == "부정":
                verified_negatives.append(f"[리뷰#{review_id}] {review_content}")
            elif sentiment == "긍정":
                positives.append(f"[리뷰#{review_id}] {review_content}")
        
        negative_text = "\n\n".join(verified_negatives[:50])
        positive_text = "\n\n".join(positives[:50])
        
        extraction_prompt = f"""리뷰 분석 전문가입니다. 검증된 부정/긍정 리뷰에서 장단점을 추출하세요.

## 검증된 부정 리뷰 ({len(verified_negatives)}개)
{negative_text}

## 긍정 리뷰 ({len(positives)}개)
{positive_text}

## JSON 출력

{{
  "치명적_단점": [
    {{
      "aspect": "음식 온도 관리",
      "severity": "high",
      "count": 5,
      "percentage": 3.3,
      "samples": ["[리뷰#5] 커피가 미지근", "[리뷰#12] 음식 식어서"],
      "impact": "재방문 의사 타격"
    }}
  ],
  "단점": [
    {{"aspect": "가격", "count": 8, "percentage": 5.3, "samples": ["[리뷰#20] 비싸요"]}}
  ],
  "장점": [
    {{"aspect": "맛", "count": 65, "percentage": 43.3, "samples": ["[리뷰#3] 맛있어요"]}}
  ]
}}

**규칙**: 비율 = (count / 150) * 100, 리뷰 번호 필수
"""
        
        response_3 = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "리뷰 분석 전문가. JSON만 출력."},
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response_3.choices[0].message.content)
        print(f"      ✅ 3단계 완료")
        print(f"         🔴 치명적 단점: {len(result.get('치명적_단점', []))}개")
        print(f"         ⚠️  일반 단점: {len(result.get('단점', []))}개")
        print(f"         ✅ 장점: {len(result.get('장점', []))}개")
        
        return result
        
    except Exception as e:
        print(f"   ❌ GPT 전처리 실패: {e}")
        return {"치명적_단점": [], "단점": [], "장점": []}


# ==================== STEP 2: Claude 인사이트 (4가지 경쟁 전략) ====================

def analyze_with_claude(preprocessed, target_store, competitors, competitor_reviews, statistical_comparison):
    """Claude: 4가지 경쟁 전략 도출"""
    
    print(f"\n{'='*60}")
    print(f"🧠 STEP 2: Claude 4가지 경쟁 전략")
    print(f"{'='*60}")
    
    # 경쟁사 샘플 리뷰
    comp_summary = []
    for comp in competitors[:3]:
        comp_revs = competitor_reviews.get(comp.place_id, [])[:3]
        if comp_revs:
            comp_summary.append(f"**{comp.name}**\n" + "\n".join([
                f"- {r['content'][:150]}" for r in comp_revs
            ]))
    
    comp_text = "\n\n".join(comp_summary)
    
    # 통계 요약
    stats_text = ""
    if statistical_comparison:
        stats_text = "## 📊 통계 비교 (우리 vs 경쟁사)\n\n"
        
        if '우리의_강점' in statistical_comparison:
            stats_text += "### ✅ 우리가 경쟁사보다 잘하는 것\n\n"
            for topic, stat in list(statistical_comparison['우리의_강점'].items())[:3]:
                stats_text += f"- **{topic}**: 우리 {stat['our']['rate']*100:.1f}% vs 경쟁사 {stat['comp']['rate']*100:.1f}% (✅ +{stat['gap']*100:.1f}%p 우위)\n"
            stats_text += "\n"
        
        if '우리의_약점' in statistical_comparison:
            stats_text += "### ⚠️ 우리가 경쟁사보다 부족한 것\n\n"
            for topic, stat in list(statistical_comparison['우리의_약점'].items())[:3]:
                stats_text += f"- **{topic}**: 우리 {stat['our']['rate']*100:.1f}% vs 경쟁사 {stat['comp']['rate']*100:.1f}% (⚠️ -{abs(stat['gap'])*100:.1f}%p 열위)\n"
            stats_text += "\n"
    
    # 프롬프트
    prompt = f"""🚨 외식업 전략 컨설턴트입니다. **4가지 경쟁 전략**을 도출하세요.

🔥 CRITICAL: 
1. 3단계 검증을 거친 데이터 (오탐 제거됨)
2. 절대 지어내지 마세요
3. 실제 리뷰만 사용

## 우리 가게 ({target_store['name']})

### 🔴 치명적 단점
{json.dumps(preprocessed.get('치명적_단점', []), ensure_ascii=False, indent=2)}

### ⚠️ 일반 단점
{json.dumps(preprocessed.get('단점', []), ensure_ascii=False, indent=2)}

### ✅ 장점
{json.dumps(preprocessed.get('장점', []), ensure_ascii=False, indent=2)}

{stats_text}

## 경쟁사 샘플 리뷰
{comp_text}

---

## 🎯 4가지 전략 분석

### 1️⃣ 긴급_개선 (우리 약점 × 경쟁사 강점)
- **정의**: 우리는 못하는데 경쟁사는 잘하는 것
- **의미**: 🚨 가장 시급하게 개선해야 할 항목
- **예시**: 우리 "주차 어려움" + 경쟁사 "주차 편해요"

### 2️⃣ 차별화_포인트 (우리 강점 × 경쟁사 약점)
- **정의**: 우리는 잘하는데 경쟁사는 못하는 것
- **의미**: 💎 마케팅 강조 포인트
- **예시**: 우리 "빠른 서빙" + 경쟁사 "느린 서비스"

### 3️⃣ 배울_점 (경쟁사만의 강점)
- **정의**: 경쟁사가 특히 잘하는 것
- **의미**: 📚 벤치마킹 대상

### 4️⃣ 시장_공통약점 (경쟁사의 약점)
- **정의**: 경쟁사가 공통으로 못하는 것
- **의미**: 🎯 시장 기회

---

## JSON 출력 (4가지 전략 필수!)

{{
  "후킹_문구": "⚠️ 음식 온도 관리 실패로 고객 5명 불만",
  
  "치명적_단점_상세": [
    {{
      "aspect": "음식 온도 관리",
      "severity": "high",
      "description": "음식이 미지근하거나 식어서 제공",
      "reviews": ["[리뷰#1] 커피가 미지근", "[리뷰#5] 음식 식어서"],
      "action": "즉시: 주방 온도계 + 10분 내 서빙 규칙"
    }}
  ],
  
  "우리_장점_파이": {{"맛": 43.3, "분위기": 21.3}},
  
  "우리_단점": {{
    "is_many": true,
    "pie_data": {{"가격": 5.3, "대기": 2.7}},
    "list_data": [
      {{"aspect": "가격", "count": 8, "percentage": 5.3, "reviews": ["[리뷰#20] 비싸요"]}}
    ]
  }},
  
  "경쟁_전략": {{
    "긴급_개선": [
      {{
        "aspect": "주차 편의성",
        "priority": "high",
        "our_weakness": {{
          "description": "우리는 주차 불편 불만 많음",
          "reviews": ["[리뷰#15] 주차 어려워요"],
          "mention_rate": 8.7
        }},
        "competitor_strength": {{
          "description": "경쟁사는 주차 편리 칭찬 많음",
          "reviews": ["경쟁사A: 주차 편해요"],
          "mention_rate": 15.3
        }},
        "action": "🚨 긴급: 제휴 주차장 확보",
        "impact": "고객 유입 20% 증가 예상"
      }}
    ],
    
    "차별화_포인트": [
      {{
        "aspect": "서빙 속도",
        "our_strength": {{
          "description": "우리는 빠른 서빙 칭찬 많음",
          "reviews": ["[리뷰#8] 음식 빨리 나와요"],
          "mention_rate": 12.0
        }},
        "competitor_weakness": {{
          "description": "경쟁사는 느린 서비스 불만 많음",
          "reviews": ["경쟁사A: 음식 늦게 나옴"],
          "mention_rate": 18.7
        }},
        "marketing_message": "💎 '5분 안에 나오는 OO' 슬로건 활용",
        "channel": "인스타그램 릴스"
      }}
    ],
    
    "배울_점": [
      {{
        "aspect": "메뉴 다양성",
        "competitor_strength": {{
          "description": "경쟁사는 선택지 많음",
          "reviews": ["경쟁사A: 메뉴 다양해요"]
        }},
        "our_status": "우리는 메뉴 언급 거의 없음",
        "suggestion": "📚 시즌 메뉴 2개 추가",
        "timeline": "2개월 내"
      }}
    ],
    
    "시장_공통약점": [
      {{
        "aspect": "웨이팅 관리",
        "competitor_weakness": {{
          "description": "경쟁사들 긴 대기시간 공통 불만",
          "reviews": ["경쟁사A: 1시간 대기"],
          "mention_rate": 22.3
        }},
        "opportunity": "🎯 예약 시스템 도입 시 시장 선점 가능",
        "action": "네이버 예약 도입"
      }}
    ]
  }},
  
  "체크리스트": [
    "🚨 주차 제휴 3곳 확보 (긴급)",
    "💎 '5분 서빙' 릴스 제작 (차별화)",
    "📚 시즌 메뉴 2개 테스트",
    "🎯 네이버 예약 도입"
  ]
}}

**규칙**: 4가지 전략 모두 작성, 실제 리뷰만 사용
"""
    
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=10000,
            temperature=0.0,
            system="외식업 전략 컨설턴트. 4가지 경쟁 전략 필수 도출. JSON만 출력.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        print(f"   ✅ 인사이트 생성 완료")
        print(f"      🚨 긴급 개선: {len(result.get('경쟁_전략', {}).get('긴급_개선', []))}개")
        print(f"      💎 차별화: {len(result.get('경쟁_전략', {}).get('차별화_포인트', []))}개")
        print(f"      📚 배울 점: {len(result.get('경쟁_전략', {}).get('배울_점', []))}개")
        print(f"      🎯 시장 기회: {len(result.get('경쟁_전략', {}).get('시장_공통약점', []))}개")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Claude 분석 실패: {e}")
        return None


# ==================== STEP 3: HTML 리포트 ====================

def generate_visual_report(preprocessed, claude_result, target_store, competitors):
    """HTML 리포트 (4가지 전략 시각화)"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    hooking = claude_result.get('후킹_문구', '⚠️ 즉시 개선이 필요한 단점 발견')
    
    # 치명적 단점
    critical_weaknesses = claude_result.get('치명적_단점_상세', [])
    critical_html = ""
    if critical_weaknesses:
        critical_html = """
        <div class="critical-section">
            <h2>🚨 치명적 단점 (즉시 조치!)</h2>
"""
        for item in critical_weaknesses:
            aspect = item.get('aspect', '항목')
            description = item.get('description', '')
            reviews = item.get('reviews', [])
            action = item.get('action', '조치 필요')
            
            critical_html += f"""
            <div class="critical-item">
                <h3>🔴 {aspect}</h3>
                <p class="description">{description}</p>
                <div class="review-samples">
                    <strong>실제 고객 리뷰:</strong>
"""
            for review in reviews[:3]:
                critical_html += f'                    <div class="review-quote critical-review">💬 {review}</div>\n'
            
            critical_html += f"""
                </div>
                <div class="action-box">
                    <strong>✅ 즉시 조치:</strong> {action}
                </div>
            </div>
"""
        critical_html += "        </div>"
    
    # 장점 파이
    strengths_pie = claude_result.get('우리_장점_파이', {})
    
    # 단점
    weaknesses = claude_result.get('우리_단점', {})
    is_many = weaknesses.get('is_many', False)
    
    weaknesses_html = ""
    if is_many:
        pie_data = weaknesses.get('pie_data', {})
        list_data = weaknesses.get('list_data', [])
        
        weaknesses_html = f"""
        <div class="chart-container">
            <h3>📉 단점 분포</h3>
            <canvas id="weaknesses-chart"></canvas>
        </div>
        <div class="weakness-details">
            <h3>📝 실제 고객 리뷰</h3>
"""
        for item in list_data:
            aspect = item.get('aspect', '항목')
            count = item.get('count', 0)
            percentage = item.get('percentage', 0)
            reviews = item.get('reviews', [])
            
            weaknesses_html += f"""
            <div class="weakness-item">
                <div class="weakness-header">
                    <strong>{aspect}</strong>
                    <span class="badge">{count}건 ({percentage:.1f}%)</span>
                </div>
                <div class="review-samples">
"""
            for review in reviews[:3]:
                weaknesses_html += f'                    <div class="review-quote">💬 {review}</div>\n'
            
            weaknesses_html += """
                </div>
            </div>
"""
        weaknesses_html += "        </div>"
    else:
        list_data = weaknesses.get('list_data', [])
        weaknesses_html = """
        <div class="weakness-list">
            <h3>📉 단점</h3>
"""
        for item in list_data:
            aspect = item.get('aspect', '항목')
            count = item.get('count', 0)
            percentage = item.get('percentage', 0)
            reviews = item.get('reviews', [])
            
            weaknesses_html += f"""
            <div class="weakness-item">
                <div class="weakness-header">
                    <strong>{aspect}</strong>
                    <span class="badge">{count}건 ({percentage:.1f}%)</span>
                </div>
                <div class="review-samples">
"""
            for review in reviews[:3]:
                weaknesses_html += f'                    <div class="review-quote">💬 {review}</div>\n'
            
            weaknesses_html += """
                </div>
            </div>
"""
        weaknesses_html += "        </div>"
    
    # 🔥 NEW: 4가지 경쟁 전략
    strategy_html = ""
    if '경쟁_전략' in claude_result:
        strategies = claude_result['경쟁_전략']
        
        strategy_html = """
        <div class="section strategy-section">
            <h2>🎯 4가지 경쟁 전략</h2>
            <p class="strategy-intro">우리 가게와 경쟁사를 비교하여 도출한 전략적 인사이트입니다.</p>
"""
        
        # 1️⃣ 긴급 개선
        urgent = strategies.get('긴급_개선', [])
        if urgent:
            strategy_html += """
            <div class="strategy-category urgent">
                <h3>🚨 1️⃣ 긴급 개선 (우리 약점 × 경쟁사 강점)</h3>
                <p class="category-desc">우리는 못하는데 경쟁사는 잘하는 것 → 가장 시급하게 개선해야 합니다!</p>
"""
            for item in urgent:
                strategy_html += f"""
                <div class="strategy-item urgent-item">
                    <h4>🔴 {item['aspect']}</h4>
                    <div class="priority-badge">{item.get('priority', 'high').upper()} PRIORITY</div>
                    
                    <div class="comparison-box">
                        <div class="our-side weakness-side">
                            <strong>😰 우리 현황 (약점)</strong>
                            <p>{item['our_weakness']['description']}</p>
                            <div class="review-samples">
"""
                for review in item['our_weakness'].get('reviews', [])[:3]:
                    strategy_html += f'                                <div class="review-quote weakness-review">💬 {review}</div>\n'
                
                strategy_html += f"""
                            </div>
                            <div class="stat">언급률: {float(item['our_weakness'].get('mention_rate', 0)):.1f}%</div>
                        </div>
                        
                        <div class="vs-divider">VS</div>
                        
                        <div class="comp-side strength-side">
                            <strong>😎 경쟁사 현황 (강점)</strong>
                            <p>{item['competitor_strength']['description']}</p>
                            <div class="review-samples">
"""
                for review in item['competitor_strength'].get('reviews', [])[:3]:
                    strategy_html += f'                                <div class="review-quote strength-review">💬 {review}</div>\n'
                
                strategy_html += f"""
                            </div>
                            <div class="stat">언급률: {float(item['competitor_strength'].get('mention_rate', 0)):.1f}%</div>
                        </div>
                    </div>
                    
                    <div class="action-box urgent-action">
                        <strong>✅ 즉시 조치:</strong> {item.get('action', '')}
                    </div>
                    <div class="impact-box">
                        <strong>📈 예상 효과:</strong> {item.get('impact', '')}
                    </div>
                </div>
"""
            strategy_html += "            </div>"
        
        # 2️⃣ 차별화 포인트
        differentiation = strategies.get('차별화_포인트', [])
        if differentiation:
            strategy_html += """
            <div class="strategy-category differentiation">
                <h3>💎 2️⃣ 차별화 포인트 (우리 강점 × 경쟁사 약점)</h3>
                <p class="category-desc">우리는 잘하는데 경쟁사는 못하는 것 → 마케팅에서 강조하세요!</p>
"""
            for item in differentiation:
                strategy_html += f"""
                <div class="strategy-item differentiation-item">
                    <h4>💎 {item['aspect']}</h4>
                    
                    <div class="comparison-box">
                        <div class="our-side strength-side">
                            <strong>🌟 우리 강점</strong>
                            <p>{item['our_strength']['description']}</p>
                            <div class="review-samples">
"""
                for review in item['our_strength'].get('reviews', [])[:3]:
                    strategy_html += f'                                <div class="review-quote strength-review">💬 {review}</div>\n'
                
                strategy_html += f"""
                            </div>
                            <div class="stat">언급률: {float(item['our_strength'].get('mention_rate', 0)):.1f}%</div>
                        </div>
                        
                        <div class="vs-divider">VS</div>
                        
                        <div class="comp-side weakness-side">
                            <strong>😓 경쟁사 약점</strong>
                            <p>{item['competitor_weakness']['description']}</p>
                            <div class="review-samples">
"""
                for review in item['competitor_weakness'].get('reviews', [])[:3]:
                    strategy_html += f'                                <div class="review-quote weakness-review">💬 {review}</div>\n'
                
                strategy_html += f"""
                            </div>
                            <div class="stat">언급률: {float(item['competitor_weakness'].get('mention_rate', 0)):.1f}%</div>
                        </div>
                    </div>
                    
                    <div class="action-box marketing-action">
                        <strong>💎 마케팅 메시지:</strong> {item.get('marketing_message', '')}
                    </div>
                    <div class="channel-box">
                        <strong>📢 추천 채널:</strong> {item.get('channel', '')}
                    </div>
                </div>
"""
            strategy_html += "            </div>"
        
        # 3️⃣ 배울 점
        learning = strategies.get('배울_점', [])
        if learning:
            strategy_html += """
            <div class="strategy-category learning">
                <h3>📚 3️⃣ 배울 점 (경쟁사만의 강점)</h3>
                <p class="category-desc">경쟁사가 특히 잘하는 것 → 벤치마킹하세요!</p>
"""
            for item in learning:
                strategy_html += f"""
                <div class="strategy-item learning-item">
                    <h4>📚 {item['aspect']}</h4>
                    
                    <div class="learning-content">
                        <div class="comp-strength-box">
                            <strong>🏆 경쟁사 강점</strong>
                            <p>{item['competitor_strength']['description']}</p>
                            <div class="review-samples">
"""
                for review in item['competitor_strength'].get('reviews', [])[:3]:
                    strategy_html += f'                                <div class="review-quote">💬 {review}</div>\n'
                
                strategy_html += f"""
                            </div>
                        </div>
                        
                        <div class="our-status-box">
                            <strong>📍 우리 현황</strong>
                            <p>{item.get('our_status', '')}</p>
                        </div>
                    </div>
                    
                    <div class="action-box learning-action">
                        <strong>💡 제안:</strong> {item.get('suggestion', '')}
                    </div>
                    <div class="timeline-box">
                        <strong>⏰ 기간:</strong> {item.get('timeline', '')}
                    </div>
                </div>
"""
            strategy_html += "            </div>"
        
        # 4️⃣ 시장 공통 약점
        market = strategies.get('시장_공통약점', [])
        if market:
            strategy_html += """
            <div class="strategy-category market">
                <h3>🎯 4️⃣ 시장 기회 (경쟁사 공통 약점)</h3>
                <p class="category-desc">경쟁사가 공통으로 못하는 것 → 우리가 선점하면 유리합니다!</p>
"""
            for item in market:
                strategy_html += f"""
                <div class="strategy-item market-item">
                    <h4>🎯 {item['aspect']}</h4>
                    
                    <div class="market-weakness-box">
                        <strong>⚠️ 시장 공통 약점</strong>
                        <p>{item['competitor_weakness']['description']}</p>
                        <div class="review-samples">
"""
                for review in item['competitor_weakness'].get('reviews', [])[:3]:
                    strategy_html += f'                            <div class="review-quote">💬 {review}</div>\n'
                
                strategy_html += f"""
                        </div>
                        <div class="stat">평균 언급률: {float(item['competitor_weakness'].get('mention_rate', 0)):.1f}%</div>
                    </div>
                    
                    <div class="opportunity-box">
                        <strong>🚀 기회:</strong> {item.get('opportunity', '')}
                    </div>
                    <div class="action-box market-action">
                        <strong>✅ 실행:</strong> {item.get('action', '')}
                    </div>
                </div>
"""
            strategy_html += "            </div>"
        
        strategy_html += "        </div>"
    
    # 체크리스트
    checklist = claude_result.get('체크리스트', [])
    checklist_html = """
        <div class="section">
            <h2>✅ 2주 긴급 체크리스트</h2>
            <p style="color: #ff6b6b; font-weight: bold; margin-bottom: 15px;">
                🚨 표시는 치명적 단점 해결 긴급 조치
            </p>
            <ul class="checklist">
"""
    for item in checklist:
        style = ' style="background: #fff5f5; border-left: 4px solid #ff6b6b;"' if '🚨' in item else ''
        checklist_html += f'                <li{style}><input type="checkbox"> {item}</li>\n'
    
    checklist_html += """
            </ul>
        </div>
"""
    
    # HTML 전체
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{target_store['name']} 분석 리포트</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ font-size: 32px; margin-bottom: 10px; color: #333; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        
        .hooking-banner {{ 
            background: linear-gradient(135deg, #ff6b6b 0%, #ff5252 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin: 20px 0 40px;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 4px 15px rgba(255,107,107,0.4);
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
        }}
        
        .critical-section {{ 
            background: #fff5f5;
            padding: 30px;
            border-radius: 12px;
            margin: 30px 0;
            border-left: 6px solid #ff6b6b;
        }}
        
        .critical-item {{ 
            background: white;
            padding: 25px;
            margin: 20px 0;
            border-radius: 8px;
            border: 2px solid #ff6b6b;
        }}
        
        .critical-item h3 {{ 
            color: #ff6b6b;
            font-size: 22px;
            margin-bottom: 15px;
        }}
        
        .description {{ 
            color: #555;
            line-height: 1.6;
            margin-bottom: 15px;
        }}
        
        .action-box {{ 
            background: #e3f2fd;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            border-left: 4px solid #2196f3;
        }}
        
        .urgent-action {{ background: #fff3e0; border-left-color: #ff9800; }}
        .marketing-action {{ background: #f3e5f5; border-left-color: #9c27b0; }}
        .learning-action {{ background: #e8f5e9; border-left-color: #4caf50; }}
        .market-action {{ background: #e1f5fe; border-left-color: #03a9f4; }}
        
        .impact-box, .channel-box, .timeline-box, .opportunity-box {{
            background: #fafafa;
            padding: 12px;
            border-radius: 6px;
            margin-top: 10px;
            font-size: 14px;
        }}
        
        .critical-review {{ 
            background: #fff5f5 !important;
            border-left: 3px solid #ff6b6b !important;
        }}
        
        .section {{ margin: 40px 0; padding: 30px; background: #fafafa; border-radius: 8px; }}
        h2 {{ font-size: 24px; margin-bottom: 20px; color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }}
        h3 {{ font-size: 20px; margin: 20px 0 15px; color: #555; }}
        h4 {{ font-size: 18px; margin: 15px 0 10px; color: #667eea; }}
        
        .strategy-section {{ background: linear-gradient(to bottom, #f8f9fa, #ffffff); }}
        .strategy-intro {{ color: #666; margin-bottom: 30px; font-size: 15px; }}
        
        .strategy-category {{ margin: 30px 0; padding: 25px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        .strategy-category.urgent {{ border-left: 5px solid #ff6b6b; }}
        .strategy-category.differentiation {{ border-left: 5px solid #9c27b0; }}
        .strategy-category.learning {{ border-left: 5px solid #4caf50; }}
        .strategy-category.market {{ border-left: 5px solid #03a9f4; }}
        
        .category-desc {{ color: #666; margin-bottom: 20px; padding: 12px; background: #f9f9f9; border-radius: 6px; font-size: 14px; }}
        
        .strategy-item {{ 
            background: #fafafa;
            padding: 25px;
            margin: 20px 0;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }}
        
        .urgent-item {{ border-color: #ff6b6b; }}
        .differentiation-item {{ border-color: #9c27b0; }}
        .learning-item {{ border-color: #4caf50; }}
        .market-item {{ border-color: #03a9f4; }}
        
        .priority-badge {{
            display: inline-block;
            background: #ff6b6b;
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        
        .comparison-box {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            align-items: stretch;
        }}
        
        .our-side, .comp-side {{
            flex: 1;
            padding: 20px;
            border-radius: 8px;
        }}
        
        .weakness-side {{ background: #ffebee; border: 2px solid #ef5350; }}
        .strength-side {{ background: #e8f5e9; border: 2px solid #66bb6a; }}
        
        .vs-divider {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #999;
            font-size: 18px;
            min-width: 50px;
        }}
        
        .learning-content {{ margin: 20px 0; }}
        .comp-strength-box, .our-status-box, .market-weakness-box {{
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        
        .comp-strength-box {{ background: #e8f5e9; border-left: 4px solid #4caf50; }}
        .our-status-box {{ background: #fff3e0; border-left: 4px solid #ff9800; }}
        .market-weakness-box {{ background: #ffebee; border-left: 4px solid #f44336; }}
        
        .stat {{
            margin-top: 12px;
            padding: 8px 12px;
            background: white;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .chart-container {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        canvas {{ max-height: 400px; }}
        
        .weakness-item {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ffa726; }}
        .weakness-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .badge {{ background: #ffa726; color: white; padding: 4px 12px; border-radius: 12px; font-size: 14px; }}
        
        .review-samples {{ margin-top: 15px; padding: 15px; background: #f9f9f9; border-radius: 6px; }}
        .review-quote {{ 
            padding: 10px;
            margin: 8px 0;
            background: white;
            border-left: 3px solid #667eea;
            font-style: italic;
            color: #555;
            font-size: 14px;
        }}
        
        .weakness-review {{ border-left-color: #f44336; }}
        .strength-review {{ border-left-color: #4caf50; }}
        
        .checklist {{ list-style: none; }}
        .checklist li {{ padding: 12px; margin: 8px 0; background: white; border-radius: 6px; }}
        .checklist input[type="checkbox"] {{ margin-right: 10px; transform: scale(1.3); }}
        
        @media (max-width: 768px) {{
            .comparison-box {{ flex-direction: column; }}
            .vs-divider {{ transform: rotate(90deg); margin: 10px 0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏪 {target_store['name']} 분석 리포트</h1>
        <div class="meta">
            📅 {timestamp} | 📍 {target_store.get('district', '미상')} | 🍽️ {target_store.get('industry', '미상')}
        </div>
        
        <div class="hooking-banner">
            {hooking}
        </div>
        
        {critical_html}
        
        <div class="section">
            <h2>✅ 우리 가게 장점</h2>
            <div class="chart-container">
                <canvas id="strengths-chart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>⚠️ 개선 필요 항목</h2>
            {weaknesses_html}
        </div>
        
        {strategy_html}
        
        {checklist_html}
    </div>
    
    <script>
        const strengthsCtx = document.getElementById('strengths-chart').getContext('2d');
        new Chart(strengthsCtx, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(list(strengths_pie.keys()))},
                datasets: [{{
                    data: {json.dumps(list(strengths_pie.values()))},
                    backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }},
                    title: {{ display: true, text: '장점 분포 (%)', font: {{ size: 16 }} }}
                }}
            }}
        }});
        
        {f'''
        const weaknessesCtx = document.getElementById('weaknesses-chart').getContext('2d');
        new Chart(weaknessesCtx, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(list(weaknesses.get('pie_data', {}).keys()))},
                datasets: [{{
                    data: {json.dumps(list(weaknesses.get('pie_data', {}).values()))},
                    backgroundColor: ['#ff6b6b', '#feca57', '#48dbfb']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }},
                    title: {{ display: true, text: '단점 언급률 (%)', font: {{ size: 16 }} }}
                }}
            }}
        }});
        ''' if is_many else ''}
    </script>
</body>
</html>
"""
    
    return html


# ==================== 메인 실행 ====================

async def generate_hybrid_report(target_store, target_reviews, competitors, 
                                 competitor_reviews, statistical_comparison=None):
    """하이브리드 리포트 생성 (3단계 검증 + 4가지 경쟁 전략)"""
    
    print(f"\n{'='*60}")
    print(f"🚀 하이브리드 인사이트 시스템")
    print(f"{'='*60}")
    print(f"   ✅ GPT 3단계 검증 (오탐 제거)")
    print(f"   🎯 Claude 4가지 경쟁 전략")
    print(f"      1. 긴급 개선 (우리 약점 × 경쟁사 강점)")
    print(f"      2. 차별화 포인트 (우리 강점 × 경쟁사 약점)")
    print(f"      3. 배울 점 (경쟁사 강점)")
    print(f"      4. 시장 기회 (경쟁사 약점)")
    
    # STEP 1: GPT 전처리
    preprocessed = preprocess_with_gpt(
        target_store, target_reviews, competitors, 
        competitor_reviews, statistical_comparison
    )
    
    # STEP 2: Claude 인사이트
    claude_result = analyze_with_claude(
        preprocessed, target_store, competitors, 
        competitor_reviews, statistical_comparison
    )
    
    if not claude_result:
        return None
    
    # STEP 3: HTML 리포트
    print(f"\n{'='*60}")
    print(f"📊 STEP 3: HTML 리포트 생성")
    print(f"{'='*60}")
    
    html_report = generate_visual_report(
        preprocessed, claude_result, target_store, competitors
    )
    
    # 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{target_store['name'].replace(' ', '_')}_{timestamp}.html"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"   ✅ 리포트 저장: {filename}")
        print(f"   🔥 후킹: {claude_result.get('후킹_문구', '')[:50]}...")
        print(f"   🚨 치명적 단점: {len(claude_result.get('치명적_단점_상세', []))}개")
        print(f"   🎯 경쟁 전략: 4가지 도출 완료")
        print(f"   💡 브라우저로 열어보세요!")
        
        return html_report
        
    except Exception as e:
        print(f"   ❌ 파일 저장 실패: {e}")
        return None