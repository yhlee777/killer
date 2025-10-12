# -*- coding: utf-8 -*-
# gpt_insight_engine.py - GPT 기반 인사이트 생성 (실전 인사이트 강화 + 완전 개선판)

import os
import json
from datetime import datetime
from openai import OpenAI

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다!")

client = OpenAI(api_key=api_key)


class PromptTemplates:
    """프롬프트 템플릿 관리 (실전 인사이트 강화)"""
    
    @staticmethod
    def advanced_analysis(target_store, target_stats, comp_stats_aggregated, 
                         sample_our_reviews, sample_comp_reviews, statistical_comparison):
        """고급 분석 프롬프트 (9가지 검증된 인사이트 기반)"""
        
        # 통계 비교 텍스트 (신뢰 배지 추가)
        def get_confidence_badge(stat):
            """신뢰도 배지 반환"""
            # count가 있으면 사용, 없으면 rate * 예상 표본 수로 추정
            n_our = stat['our'].get('count', 0)
            n_comp = stat['comp'].get('count', 0)
            
            # count가 0이면 rate로부터 추정 (target_stats, comp_stats_aggregated의 total_reviews 사용)
            if n_our == 0 and stat['our']['rate'] > 0:
                n_our = int(stat['our']['rate'] * target_stats.get('total_reviews', 100))
            if n_comp == 0 and stat['comp']['rate'] > 0:
                n_comp = int(stat['comp']['rate'] * comp_stats_aggregated.get('total_reviews', 100))
            
            n_total = n_our + n_comp
            ci_width = stat['ci'][1] - stat['ci'][0]
            p_val = stat['p_value']
            
            if n_total >= 100 and ci_width < 0.15 and p_val < 0.05:
                return "🟢"  # n 충분/CI 좁음/유의
            elif p_val >= 0.05 and p_val <= 0.10:
                return "🟡"  # 경계
            elif n_total < 50:
                return "⚪️"  # 참고(표본 적음)
            else:
                return "🟢" if p_val < 0.05 else "⚪️"
        
        stats_section = ""
        if statistical_comparison:
            stats_section = "\n## 📊 4단계 통계 분석\n\n"
            
            if statistical_comparison.get('우리의_약점'):
                stats_section += "### 🔥 1. 우리의 유의미한 약점 (즉시 개선)\n\n"
                for topic, stat in statistical_comparison['우리의_약점'].items():
                    gap_sign = "+" if stat['gap'] > 0 else ""
                    badge = get_confidence_badge(stat)
                    
                    # n 계산 (count가 있으면 사용, 없으면 rate * total_reviews로 추정)
                    n_our = stat['our'].get('count', int(stat['our']['rate'] * target_stats.get('total_reviews', 100)))
                    n_comp = stat['comp'].get('count', int(stat['comp']['rate'] * comp_stats_aggregated.get('total_reviews', 100)))
                    
                    stats_section += f"**⚠️ {topic}** {badge}\n"
                    stats_section += f"- 우리: {stat['our']['rate']*100:.1f}%(n={n_our}) vs 경쟁사: {stat['comp']['rate']*100:.1f}%(n={n_comp})\n"
                    stats_section += f"- GAP: {gap_sign}{stat['gap']:.3f} [95% CI: {stat['ci'][0]:.3f} ~ {stat['ci'][1]:.3f}]; P={stat['p_value']:.3f}\n\n"
            
            if statistical_comparison.get('우리의_강점'):
                stats_section += "### ✅ 2. 우리의 유의미한 강점 (유지/확대)\n\n"
                for topic, stat in statistical_comparison['우리의_강점'].items():
                    gap_sign = "+" if stat['gap'] > 0 else ""
                    badge = get_confidence_badge(stat)
                    
                    # n 계산 (count가 있으면 사용, 없으면 rate * total_reviews로 추정)
                    n_our = stat['our'].get('count', int(stat['our']['rate'] * target_stats.get('total_reviews', 100)))
                    n_comp = stat['comp'].get('count', int(stat['comp']['rate'] * comp_stats_aggregated.get('total_reviews', 100)))
                    
                    stats_section += f"**✨ {topic}** {badge}\n"
                    stats_section += f"- 우리: {stat['our']['rate']*100:.1f}%(n={n_our}) vs 경쟁사: {stat['comp']['rate']*100:.1f}%(n={n_comp})\n"
                    stats_section += f"- GAP: {gap_sign}{stat['gap']:.3f} [95% CI: {stat['ci'][0]:.3f} ~ {stat['ci'][1]:.3f}]; P={stat['p_value']:.3f}\n\n"
            
            if statistical_comparison.get('경쟁사의_약점_우리의_기회'):
                stats_section += "### 💡 3. 경쟁사의 약점 = 우리의 차별화 기회\n\n"
                for topic, stat in statistical_comparison['경쟁사의_약점_우리의_기회'].items():
                    stats_section += f"**🎯 {topic}**: {stat['interpretation']}\n"
                    stats_section += f"- 기회: 마케팅 포인트로 활용!\n\n"
            
            if statistical_comparison.get('경쟁사의_강점_배울점'):
                stats_section += "### 📚 4. 경쟁사의 강점 = 벤치마킹 대상\n\n"
                for topic, stat in statistical_comparison['경쟁사의_강점_배울점'].items():
                    stats_section += f"**🔍 {topic}**: {stat['interpretation']}\n"
                    stats_section += f"- 배울 점: 전략 연구 필요\n\n"
        
        # 샘플 리뷰 (번호 추가 - 검증용!)
        our_reviews_text = ""
        for idx, r in enumerate(sample_our_reviews[:70], 1):
            our_reviews_text += f"[리뷰#{idx}] {r['content'][:250]}\n"
        
        comp_reviews_text = {}
        for comp_name, reviews in sample_comp_reviews.items():
            comp_text = ""
            for idx, r in enumerate(reviews[:5], 1):  # 5개로 축소
                comp_text += f"[리뷰#{idx}] {r['content'][:250]}\n"
            comp_reviews_text[comp_name] = comp_text
        
        # 🔍 디버깅: 경쟁사 리뷰 프롬프트 포함 확인
        total_comp_reviews = sum(len(reviews) for reviews in sample_comp_reviews.values())
        total_comp_text_length = sum(len(text) for text in comp_reviews_text.values())
        
        print(f"\n   🔍 디버깅: 프롬프트 생성 확인")
        print(f"      └─ 우리 리뷰: {len(sample_our_reviews)}개")
        print(f"      └─ 경쟁사 리뷰: {total_comp_reviews}개")
        print(f"      └─ 경쟁사 텍스트 길이: {total_comp_text_length:,} 글자")
        
        if total_comp_reviews == 0:
            print(f"      ⚠️  경고: 경쟁사 리뷰가 프롬프트에 포함되지 않습니다!")
        elif total_comp_text_length == 0:
            print(f"      ⚠️  경고: 경쟁사 리뷰 텍스트가 비어있습니다!")
        else:
            print(f"      ✅ 프롬프트 생성 완료")
        
        prompt = f"""# 🏪 {target_store['name']} 경쟁사 분석 (실전 인사이트 강화)

## 기본 정보
- **지역**: {target_store['district']}
- **업종**: {target_store['industry']}
- **우리 리뷰 수**: {target_stats['total_reviews']}개
- **경쟁사 리뷰 수**: {comp_stats_aggregated['total_reviews']}개

{stats_section}

## 📈 키워드 통계

### 우리 가게
- 맛_긍정: {target_stats['keyword_counts'].get('맛_긍정', 0)}회 | 맛_부정: {target_stats['keyword_counts'].get('맛_부정', 0)}회
- 서비스_긍정: {target_stats['keyword_counts'].get('서비스_긍정', 0)}회 | 서비스_부정: {target_stats['keyword_counts'].get('서비스_부정', 0)}회
- 분위기_긍정: {target_stats['keyword_counts'].get('분위기_긍정', 0)}회 | 분위기_부정: {target_stats['keyword_counts'].get('분위기_부정', 0)}회
- 재방문_긍정: {target_stats['keyword_counts'].get('재방문_긍정', 0)}회
- 대기_언급: {target_stats['keyword_counts'].get('대기_언급', 0)}회 (낮을수록 좋음!)

### 경쟁사 평균
- 맛_긍정: {comp_stats_aggregated['keyword_counts'].get('맛_긍정', 0)}회 | 맛_부정: {comp_stats_aggregated['keyword_counts'].get('맛_부정', 0)}회
- 서비스_긍정: {comp_stats_aggregated['keyword_counts'].get('서비스_긍정', 0)}회 | 서비스_부정: {comp_stats_aggregated['keyword_counts'].get('서비스_부정', 0)}회
- 분위기_긍정: {comp_stats_aggregated['keyword_counts'].get('분위기_긍정', 0)}회 | 분위기_부정: {comp_stats_aggregated['keyword_counts'].get('분위기_부정', 0)}회
- 재방문_긍정: {comp_stats_aggregated['keyword_counts'].get('재방문_긍정', 0)}회
- 대기_언급: {comp_stats_aggregated['keyword_counts'].get('대기_언급', 0)}회

## 💬 샘플 리뷰 (검증용 - 리뷰 번호 포함!)

🚨 **CRITICAL**: 아래 리뷰 목록만 사용! 없는 내용 절대 금지!

⚠️ **분석 우선순위**: 부정 리뷰(별점 1-2점)를 먼저 분석하세요!

### 우리 가게 리뷰 (70개 샘플 - 부정 리뷰 우선 정렬됨)
{our_reviews_text}

### 경쟁사 리뷰 (각 5개 샘플)
{chr(10).join([f"**{name}**:{chr(10)}{text}" for name, text in comp_reviews_text.items()])}

---

## 🎯 업종/지역 경쟁에서 통하는 검증된 인사이트 9가지

당신의 분석은 반드시 아래 9가지 프레임워크를 따라야 합니다:

### 1️⃣ 대기(웨이팅) 언급률: 낮으면 곧 기회
- **시사점**: 대기 언급률이 경쟁사보다 낮으면 "빠른 입장 = 차별화 메시지"가 먹힘
- **메시지**: "지금 오시면 바로 입장 💨", "평일 저녁 10분 컷"
- **액션**: 네이버 톡채널/인스타 스토리에 "실시간 자리 여유" 고정템플릿
- **KPI**: 클릭→방문 전환율, 오가닉 저장수

### 2️⃣ '재방문 의향' 시그널: 작아도 강력
- **시사점**: "또 올게요/재방문" 문구 비율이 경쟁사 대비 높으면 충성도 루프 설계 타이밍
- **액션**: 2회차 방문 쿠폰(영수증 하단 QR), 적립 2→5회 업그레이드 혜택
- **KPI**: 30일 내 2회 방문률, LTV

### 3️⃣ 맛의 방향성: "단맛/짠맛/향" 같은 취향 좌표
- **시사점**: "달다/싱겁다/향이 강하다" 같은 극성 표현은 포지셔닝 힌트
- **액션**: 대표 메뉴 1-2개는 당도·염도 옵션 명시("SWEET- / NORMAL / SWEET+")
- **KPI**: 옵션 선택 분포, 관련 불만 리뷰 감소율

### 4️⃣ '시그니처 단일화'가 필요한 순간
- **시사점**: 맛 긍정은 넓게 퍼져 있는데 특정 메뉴의 고밀도 찬사가 모이면 그걸 전면 배치
- **액션**: 메뉴판 상단/썸네일, 해시태그를 시그니처 1종으로 몰빵
- **KPI**: 시그니처 점유율, 객단가 상승

### 5️⃣ 온도/식감 클레임은 즉시 하드픽스
- **시사점**: "미지근/눅눅/탁하다(커피)" 같은 피드백은 미세공정 개선으로 바로 꺾임
- **액션**: 추출/굽기 타임스탬프 룰(예: 10분 내 제공), 테이블별 온도/물성 체크리스트
- **KPI**: 동일 키워드 재발률 50%↓

### 6️⃣ 피크타임 서비스 편차
- **시사점**: "바쁠 때 불친절/대기 길다"가 주말/저녁에 몰리면 인력/동선 이슈
- **액션**: 피크타임에 셀프 워터/픽업 셰도우 스테이션 설치, 캐셔 분리
- **KPI**: 피크타임 불만 비중, 체류시간

### 7️⃣ 분위기/공간 키워드의 돈 되는 쓰임새
- **시사점**: "자연광/포토스팟/좌석 간격" 같은 긍정이 많으면 촬영 유도 동선이 이익
- **액션**: 포토스팟 1곳 '브랜드 프레이밍'(로고 작은 네온/벽)
- **KPI**: UGC(태그된 사진) 주당 증가

### 8️⃣ 가격 불만이 "가성비"가 아니라 "구성"일 때
- **시사점**: '비싸다'보다 "양·구성 대비 비싸다"면 심리 앵커 문제
- **액션**: 세트/트리오 구성(메인+사이드 소형+음료 소형)으로 앵커 가격 세팅
- **KPI**: 세트 믹스율, 가격 불만 재발률

### 9️⃣ 경쟁사 강점 빠르게 흡수하는 '라이트 벤치'
- **시사점**: 경쟁사 리뷰에 "명확한 1가지 강점(예: 매운맛 단계, 비건 옵션)" 반복되면 저비용 샘플 도입
- **액션**: 2주 파일럿(POP 1장 + SNS 2포스트) → 반응 좋으면 정식 편성
- **KPI**: 파일럿 기간 해당 키워드 언급률

---

## 🔍 CRITICAL - 리뷰 인용 검증 프로세스 (6단계 필수!)

약점을 작성하기 **전에**, 반드시 아래 6단계를 따르세요:

### **STEP 1: 샘플 리뷰 목록 다시 읽기**
- 위 "우리 가게 리뷰 (70개 샘플)" 섹션을 **천천히 다시 읽으세요**
- 각 리뷰에 [리뷰#N] 번호가 있습니다

### **STEP 2: 키워드로 찾기**
- 예: "서비스" 약점 작성 시 → "불친절", "서비스", "직원" 키워드 검색
- 샘플 리뷰에서 해당 키워드가 포함된 리뷰를 찾으세요

### **STEP 3: 정확히 일치하는 문장 찾기**
- ❌ 비슷한 내용 (금지!)
- ❌ 의역 (금지!)
- ✅ **정확히 똑같은 문장만** 사용 가능

### **STEP 4: 리뷰 번호와 함께 원문 그대로 복사**
- "[리뷰#15] 직원분이 불친절해서 기분이 안 좋았어요"
- 리뷰 번호 [리뷰#N] 반드시 포함!

### **STEP 5: 자기 검증**
- 다시 한번 확인: "이 문장이 샘플 리뷰 목록에 **정말** 있나?"
- **100% 확신**할 수 있을 때만 사용
- **조금이라도 불확실하면 → 해당 약점 항목 완전 삭제!**

### **STEP 6: 개수 확인 + 스케일 맞추기**
- **비율(언급률) 기반 비교 필수!**
- 부정 리뷰 **0개** → "전반적으로 양호" 작성, 경쟁사 분석에 집중
- 부정 리뷰 **1-2개** → 있는 만큼만 인용, 과장 금지
  - 예: "1명의 고객이 서비스 불만 언급 (전체의 1.4%)"
  - 반드시 **비율**과 **절대수** 함께 표기
- 부정 리뷰 **3개 이상** → 3개 이상 인용, 명확한 약점
  - 예: "5명의 고객이 가격 불만 언급 (전체의 7.1%)"

---

## 🎯 스케일 맞추기 (CRITICAL!)

### 신뢰도 기준
1. **최소 표본**: 전체 리뷰 < 30개 → "참고용"으로 다운그레이드
2. **비율 기반 비교**: 절대 횟수가 아니라 언급률(%)로 비교
   - ✅ "대기 언급률 5% vs 경쟁사 15%"
   - ❌ "대기 언급 3회 vs 경쟁사 8회" (표본 크기 다르면 무의미)
3. **증거→결론 체인**: 각 주장 옆에 (언급률, GAP, 샘플 인용 1-2개) 필수

### 리포트 문장 템플릿 (그대로 사용!)
```
- 대기: "우리 대기 언급률 x% vs 경쟁사 y%로 -Δ(y-x). 실제 리뷰: [리뷰#12] '저녁에 예약 없이도 바로 입장'. → '즉시 입장' 메시지 운영 추천."

- 재방문: "재방문 의향 문구 x%, 경쟁사 y% 대비 +Δ. 샘플: [리뷰#19] '다음에 또 올게요'. → 2회차 쿠폰 즉시 도입."

- 맛(취향): "단맛 언급의 양극화. [리뷰#25] '끝맛이 달다(불호)' vs [리뷰#8] '디저트 찐맛집'. → 당도 옵션 표기로 분기 해결."
```

---

## 📋 분석 지시사항 (4단계 구조 + 9가지 인사이트 적용)

### 🔥 핵심 원칙
1. **통계적 유의성 기반**: P < 0.05인 항목만 "확실함"으로 표시
2. **스케일 맞추기**: 비율(언급률%)로 비교, 최소 표본 n≥30
3. **통계 표기 형식 통일**: 
   - ✅ "우리 X.X%(n=N1) vs 경쟁사 Y.Y%(n=N2); GAP ±Z.Z%p; 95% CI [L, U]; P=0.XX 🟢"
   - 신뢰 배지: 🟢(신뢰), 🟡(경계), ⚪️(참고)
4. **진실성 우선**: 
   - **부정 리뷰 0개** → "전반적으로 양호" 표시, 경쟁사 데이터에 집중
   - **부정 리뷰 1~2개** → 있는 그대로 언급 + 비율 표기 (과장 금지)
   - **부정 리뷰 3개 이상** → 약점으로 리포트 + 비율 표기
5. **TOP3와 약점 섹션 일관성**:
   - TOP3에 언급된 항목은 반드시 약점 섹션에 존재해야 함
   - 약점이 없으면 TOP3에도 약점 개선을 넣지 말 것
6. **9가지 인사이트 프레임워크 적용**: 대기/재방문/맛방향/시그니처/온도/피크타임/분위기/가격/벤치
7. **실행 가능성 필터**: 사장님이 3개월 내 해결 가능한 것만
   - ✅ 포함: 맛/서비스/가격/청결/메뉴/대기/재방문/온도/음료상태
   - ❌ 제외: 주차/건물크기(좁음)/위치/소음(건물구조)/계단/엘리베이터
8. **대기 해석**: 대기 언급이 **적을수록 좋음** (낮을수록 강점)
9. **증거 기반**: 모든 주장에 구체적 수치(언급률+GAP)와 **실제 리뷰 원문** 인용

### 분석 요구사항

1. **우리의 약점** (🔥 최우선)
   - **9가지 인사이트 중 해당 항목 우선 분석**:
     - 온도/식감 → 즉시 하드픽스
     - 피크타임 서비스 → 인력/동선
     - 가격 구성 → 앵커 문제
   - **CRITICAL - 부정 리뷰 처리 규칙**:
     - **0개**: "전반적으로 양호" 표시, 경쟁사 분석에 집중
     - **1~2개**: 있는 그대로 언급 + 비율 (예: "1명, 전체의 1.4%")
     - **3개 이상**: 약점으로 명확히 리포트 + 비율
   - **실행 가능성 필터** 적용
   - P < 0.05 & GAP < -0.10 인 항목 우선
   - **반드시 실제 리뷰 원문 인용** + **리뷰 번호 [리뷰#N] 필수!**
   - 즉시 실행 가능한 개선 방안 제시 (2주 러닝 기준)

2. **우리의 강점** (✅ 유지/확대)
   - **9가지 인사이트 중 해당 항목 활용**:
     - 대기 낮음 → "즉시 입장" 메시지
     - 재방문 높음 → 충성도 루프
     - 분위기 좋음 → UGC 유도
   - P < 0.05 & GAP > +0.10 인 항목
   - 실제 리뷰 2개 인용 (리뷰 번호 포함!)
   - 마케팅 활용 방안 (2주 내 실행 가능)

3. **경쟁사의 약점 = 우리의 기회** (💡 차별화) **← CRITICAL: 반드시 작성!**
   - 경쟁사가 약한 부분
   - 우리가 상대적으로 강한 부분
   - **즉시 입장/빠른 서비스** 같은 차별화 메시지 예시
   - **통계 필수**: 우리 X.X%(n=N1) vs 경쟁사 Y.Y%(n=N2); GAP; CI; P값
   - **경쟁사 리뷰를 반드시 분석하여 최소 1개 이상 작성**

4. **경쟁사의 강점 = 배울 점** (📚 벤치마킹) **← CRITICAL: 반드시 작성!**
   - **인사이트 9번(라이트 벤치) 적용**
   - 경쟁사가 강한 부분
   - 2주 파일럿으로 테스트 가능한 항목
   - 구체적 벤치마킹 방법 (메뉴 슬롯/판매 비중 목표/테스트 기간)
   - **통계 필수**: 경쟁사 X.X%(n=N1) vs 우리 Y.Y%(n=N2); GAP; CI; P값
   - **경쟁사 리뷰를 반드시 분석하여 최소 1개 이상 작성**

**🚨 CRITICAL**: 경쟁사 분석(3번, 4번)은 **필수**입니다. 경쟁사 리뷰가 제공되었으므로 반드시 분석하여 작성하세요. 비워두면 안 됩니다! 모든 통계에 n(표본수)과 신뢰 배지를 포함하세요!

### 출력 형식 (JSON)

```json
{{
  "summary": {{
    "top_priorities": ["우선과제 1 (2주 내 실행)", "우선과제 2", "우선과제 3"],
    "overall_assessment": "한 줄 요약 (주인장 설득용)",
    "biggest_opportunity": "가장 큰 기회 (차별화 포인트)"
  }},
  
  "우리의_약점": [
    {{
      "aspect": "온도/식감",
      "priority": 1,
      "statistical_evidence": "우리: 4.3%(n=69) vs 경쟁사: 2.1%(n=711); GAP +2.2%p; 95% CI [0.1, 4.3]; P=0.04 🟢",
      "description": "3명의 고객이 음료 온도/음식 식감 불만 언급",
      "insight_framework": "인사이트#5: 온도/식감 클레임은 즉시 하드픽스",
      "sample_reviews": [
        "[리뷰#15] 커피가 미지근하게 나왔어요",
        "[리뷰#28] 빵이 눅눅했습니다",
        "[리뷰#41] 파스타가 식어서 나왔어요"
      ],
      "action": {{
        "title": "타임스탬프 룰 도입",
        "how": "추출/조리 후 10분 내 제공 룰, 테이블별 온도 체크리스트",
        "cost": "무료 (운영 개선)",
        "difficulty": "낮음",
        "timeline": "2주",
        "kpi": "온도/식감 키워드 재발률 50%↓"
      }}
    }}
  ],
  
  "우리의_강점": [
    {{
      "aspect": "대기 시간",
      "statistical_evidence": "우리: 0.0%(n=69) vs 경쟁사: 1.6%(n=711); GAP -1.6%p; 95% CI [-3.0, -0.2]; P=0.03 🟢",
      "description": "웨이팅이 적어 즉시 입장 가능",
      "insight_framework": "인사이트#1: 대기 낮음 = 차별화 메시지",
      "sample_reviews": [
        "[리뷰#8] 저녁에도 바로 입장할 수 있어서 좋았어요",
        "[리뷰#19] 예약 없이 가도 대기 없어요"
      ],
      "marketing_tip": "SNS 고정 문구: '지금 오시면 바로 입장 💨 좌석 여유 있어요 (오늘 16:00 업데이트)'",
      "action": {{
        "title": "실시간 입장 알림",
        "how": "인스타 스토리/네이버 톡채널에 '자리 여유' 템플릿",
        "timeline": "2주",
        "kpi": "클릭→방문 전환율, 오가닉 저장수"
      }}
    }}
  ],
  
  "경쟁사의_약점_우리의_기회": [
    {{
      "aspect": "대기 시간",
      "statistical_evidence": "우리: 0.0%(n=69) vs 경쟁사: 1.6%(n=711); GAP -1.6%p; 95% CI [-3.0, -0.2]; P=0.03 🟢",
      "description": "경쟁사는 대기 언급이 있지만 우리는 즉시 입장 가능",
      "opportunity": "빠른 입장을 차별화 포인트로 활용",
      "marketing_message": "지금 오시면 바로 입장 💨 웨이팅 NO",
      "sample_comp_reviews": [
        "[경쟁사A 리뷰#3] 주말 저녁에 1시간 대기했어요"
      ]
    }}
  ],
  
  "경쟁사의_강점_배울점": [
    {{
      "aspect": "맛의 다양성",
      "statistical_evidence": "경쟁사: 8.5%(n=711) vs 우리: 2.9%(n=69); GAP +5.6%p; 95% CI [0.8, 10.4]; P=0.02 🟢",
      "description": "경쟁사는 메뉴 다양성에 대한 긍정 언급이 많음",
      "insight_framework": "인사이트#9: 경쟁사 강점 빠르게 흡수하는 라이트 벤치",
      "benchmark": "시그니처/시즌/도전 메뉴 3슬롯 구성",
      "action_plan": "2주 파일럿: 신규 3슬롯(시그니처 25%, 시즌 15%, 도전 10%), 고객 반응 측정 후 정식 편성",
      "sample_comp_reviews": [
        "[경쟁사B 리뷰#5] 메뉴가 다양해서 매번 다른 걸 먹어봐요"
      ]
    }}
  ],
  
  "action_items": [
    {{
      "title": "2주 액션 1",
      "category": "9가지 인사이트 프레임워크 기반",
      "why": "이유 (데이터 근거)",
      "how": "실행 방법 (구체적)",
      "cost": "비용 (무료/저/중/고)",
      "difficulty": "난이도 (낮음/보통/높음)",
      "timeline": "2주",
      "kpi": "측정 가능한 KPI"
    }}
  ]
}}
```

**🚨 FINAL CHECK 🚨**

JSON을 제출하기 전에, **마지막으로 확인**하세요:

1. **TOP3와 약점 섹션 일관성**: TOP3에 언급된 항목이 약점 섹션에 있나요? 약점이 없으면 TOP3에서 제외했나요?
2. **통계 표기 형식**: 모든 statistical_evidence에 "우리 X.X%(n=N1) vs 경쟁사 Y.Y%(n=N2); GAP ±Z.Z%p; 95% CI [L, U]; P=0.XX 🟢" 형식을 사용했나요?
3. **경쟁사 섹션 필수 항목**: "경쟁사의_약점_우리의_기회"와 "경쟁사의_강점_배울점"에 각각 최소 1개 이상 항목이 있나요?
4. **신뢰 배지**: 모든 통계에 🟢/🟡/⚪️ 배지가 있나요?
5. **리뷰 번호**: 모든 `sample_reviews`에 **리뷰 번호([리뷰#N])**가 있나요?
6. **원문 그대로**: 모든 `sample_reviews`가 **원문 그대로**인가요?
7. **비율 표기**: 부정 리뷰 개수와 **비율(%)** 모두 표기했나요?
8. **9가지 인사이트**: **9가지 인사이트 프레임워크**를 적용했나요?
9. **실행 가능성**: 실행 불가능한 약점(주차/건물/위치)을 **제외**했나요?
10. **2주 액션**: 모든 액션에 **2주 타임라인 + 측정 가능한 KPI**가 있나요?

**모두 YES면 제출, 하나라도 NO면 수정!**

당신의 분석은 사장님의 실제 비즈니스 결정에 영향을 줍니다.
**거짓 정보 = 사업 실패**일 수 있습니다.
100% 확신할 수 있는 내용만 포함하세요!
"""
        
        return prompt


class InsightAnalyzer:
    """GPT 기반 인사이트 분석기"""
    
    def __init__(self, model="gpt-4o", temperature=0.0, max_tokens=8000):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def analyze(self, prompt):
        """GPT 분석 실행"""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 데이터 기반 비즈니스 분석 전문가입니다.

**🚨 절대 규칙 🚨**:
1. 실제 리뷰 원문만 인용! 절대 지어내지 말것!
2. 제공된 샘플 리뷰에 없는 내용은 언급 금지!
3. 리뷰를 요약하거나 의역하지 말고 원문 그대로!
4. 리뷰 번호 [리뷰#N] 반드시 포함!
5. 불확실하면 해당 항목을 제외!
6. **경쟁사 분석(3번, 4번) 필수 작성!** - 경쟁사 리뷰가 제공되었으므로 반드시 분석하여 최소 1개 이상 작성
7. **TOP3와 약점 섹션 일관성 필수!** - TOP3에 언급된 항목은 반드시 약점 섹션에 존재해야 함

**핵심 원칙**:
1. 통계적 유의성(P-value) 필수 고려
2. **통계 표기 형식 통일**: "우리 X.X%(n=N1) vs 경쟁사 Y.Y%(n=N2); GAP ±Z.Z%p; 95% CI [L, U]; P=0.XX 🟢"
3. **신뢰 배지 사용**: 🟢(n 충분/CI 좁음/유의), 🟡(경계 P≈0.05~0.10), ⚪️(참고/표본 적음)
4. **스케일 맞추기**: 비율(언급률%)로 비교, 최소 표본 n≥30
5. **진실성 우선**: 
   - 부정 리뷰 0개 → "전반적으로 양호" + 경쟁사 집중
   - 부정 리뷰 1~2개 → 과장하지 말고 사실만 + 비율
   - 부정 리뷰 3개 이상 → 명확한 약점 + 비율
6. **9가지 검증된 인사이트 프레임워크 적용**:
   - 대기/재방문/맛방향/시그니처/온도/피크타임/분위기/가격/벤치
7. **실행 가능성 필터**: 사장님이 3개월 내 해결 가능한 것만
   - ✅ 포함: 맛/서비스/가격/청결/메뉴/대기/재방문/온도
   - ❌ 제외: 주차/건물크기/위치/소음(건물)/계단
8. 대기는 "낮을수록 좋음"
9. 모든 주장에 증거 제시 (우리 X%(n=N1) vs 경쟁사 Y%(n=N2); GAP; CI; P; 배지; 샘플 1-2개)
10. **실제 리뷰 원문만 인용 (절대 지어내지 말것!)**
11. **리뷰 번호 [리뷰#N] 필수 포함!**
12. 모든 액션에 **2주 타임라인 + 측정 가능한 KPI**
13. **경쟁사 분석(3번, 4번)은 절대 생략 금지! 반드시 작성!**

**통계→결론 체인**:
- 각 주장 옆에 (우리 X%(n=N1) vs 경쟁사 Y%(n=N2); GAP; CI; P; 배지; 샘플 1-2개) 필수
- 예: "대기: 우리 0.0%(n=69) vs 경쟁사 1.6%(n=711); GAP -1.6%p; 95% CI [-3.0, -0.2]; P=0.03 🟢, 샘플: [리뷰#12] '바로 입장'"

**할루시네이션 방지**:
- 제공된 리뷰 목록에서만 인용
- 없는 내용은 절대 만들지 말것
- "~라는 내용" 같은 요약도 금지
- 원문 그대로 복사만 허용
- 리뷰 번호 없으면 무효!

**경쟁사 분석 필수**:
- 경쟁사 리뷰가 제공되었으므로 반드시 분석
- "경쟁사의_약점_우리의_기회" 섹션: 최소 1개 이상, 통계 필수
- "경쟁사의_강점_배울점" 섹션: 최소 1개 이상, 통계 + 2주 파일럿 계획 필수
- 비워두거나 생략하면 안 됨!

**TOP3와 약점 일관성**:
- TOP3에 약점 개선이 있으면, 약점 섹션에도 반드시 해당 항목 존재
- 약점이 없으면 TOP3에서 약점 개선을 빼고 강점 확대/경쟁사 차별화로 구성"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"❌ GPT 분석 실패: {e}")
            return None


def generate_insight_report(target_store, target_reviews, competitors, 
                           competitor_reviews, months_filter=6, 
                           analysis_type="advanced", statistical_comparison=None,
                           search_strategy=None):
    """인사이트 리포트 생성 (실전 인사이트 강화)"""
    from review_preprocessor import generate_review_stats, KEYWORD_DICT_BASE
    
    print(f"\n{'='*60}")
    print(f"🤖 STEP 5: GPT 인사이트 엔진 (실전 인사이트 강화)")
    print(f"{'='*60}")
    print(f"   모델: gpt-4o (temperature=0.0)")
    print(f"   프레임워크: 9가지 검증된 인사이트")
    print(f"   검증: 6단계 + 리뷰 번호 + 비율 표기 필수")
    if search_strategy:
        print(f"   검색 전략: {search_strategy['name']} (β={search_strategy['beta']}, α={search_strategy['alpha']})")
    print(f"   📡 분석 요청 중... (30-60초 소요)")
    
    # 통계 생성
    target_stats = generate_review_stats(target_reviews, target_store['name'])
    
    # 경쟁사 통계 집계
    comp_stats_aggregated = {
        'total_reviews': 0,
        'keyword_counts': {k: 0 for k in KEYWORD_DICT_BASE.keys()}
    }
    
    # ✅ 수정: CompetitorScore 객체는 속성으로 접근
    for comp in competitors:
        comp_revs = competitor_reviews.get(comp.place_id, [])
        if comp_revs:
            comp_stat = generate_review_stats(comp_revs, comp.name)
            comp_stats_aggregated['total_reviews'] += comp_stat['total_reviews']
            for key in KEYWORD_DICT_BASE.keys():
                comp_stats_aggregated['keyword_counts'][key] += comp_stat['keyword_counts'][key]
    
    # 샘플 리뷰 (부정 리뷰 우선)
    def sort_by_rating(review):
        """별점 낮은 순 정렬 (부정 리뷰 우선)"""
        rating = review.get('rating', 5)
        if rating == 0:
            rating = 5
        return rating
    
    target_reviews_sorted = sorted(target_reviews, key=sort_by_rating)
    sample_our_reviews = target_reviews_sorted[:70]
    
    sample_comp_reviews = {}
    # ✅ 수정: CompetitorScore 객체는 속성으로 접근
    for comp in competitors:
        comp_revs = competitor_reviews.get(comp.place_id, [])
        if comp_revs:
            comp_revs_sorted = sorted(comp_revs, key=sort_by_rating)
            sample_comp_reviews[comp.name] = comp_revs_sorted[:5]  # 5개로 축소
    
    # 🔍 디버깅: 경쟁사 리뷰 전달 확인
    print(f"\n   🔍 디버깅: 경쟁사 리뷰 샘플 확인")
    for comp_name, reviews in sample_comp_reviews.items():
        print(f"      └─ {comp_name}: {len(reviews)}개 샘플")
        if reviews:
            print(f"         예시: {reviews[0]['content'][:50]}...")
    
    if not sample_comp_reviews:
        print(f"      ⚠️  경쟁사 리뷰 샘플이 비어있습니다!")
    else:
        print(f"   ✅ 총 {len(sample_comp_reviews)}개 경쟁사 리뷰 샘플 준비 완료")
    
    # 프롬프트 생성
    prompt = PromptTemplates.advanced_analysis(
        target_store=target_store,
        target_stats=target_stats,
        comp_stats_aggregated=comp_stats_aggregated,
        sample_our_reviews=sample_our_reviews,
        sample_comp_reviews=sample_comp_reviews,
        statistical_comparison=statistical_comparison
    )
    
    # GPT 분석
    analyzer = InsightAnalyzer(model="gpt-4o", temperature=0.0, max_tokens=8000)
    result = analyzer.analyze(prompt)
    
    if not result:
        return "❌ 분석 실패"
    
    # 🔍 디버깅: GPT 응답 확인
    print(f"\n   🔍 디버깅: GPT 응답 확인")
    
    # 경쟁사 약점
    if '경쟁사의_약점_우리의_기회' in result:
        opp_list = result['경쟁사의_약점_우리의_기회']
        opp_count = len(opp_list) if isinstance(opp_list, list) else 0
        print(f"      └─ 경쟁사 약점 항목: {opp_count}개")
        
        if opp_count == 0:
            print(f"         ⚠️  경쟁사 약점 섹션이 비어있습니다!")
    else:
        print(f"      ⚠️  '경쟁사의_약점_우리의_기회' 키 없음")
    
    # 경쟁사 강점
    if '경쟁사의_강점_배울점' in result:
        bench_list = result['경쟁사의_강점_배울점']
        bench_count = len(bench_list) if isinstance(bench_list, list) else 0
        print(f"      └─ 경쟁사 강점 항목: {bench_count}개")
        
        if bench_count == 0:
            print(f"         ⚠️  경쟁사 강점 섹션이 비어있습니다!")
    else:
        print(f"      ⚠️  '경쟁사의_강점_배울점' 키 없음")
    
    # 전체 JSON 키 확인
    print(f"      └─ JSON 키 목록: {list(result.keys())}")
    
    # 경쟁사 섹션 모두 비어있으면 경고
    opp_empty = ('경쟁사의_약점_우리의_기회' not in result or 
                 len(result.get('경쟁사의_약점_우리의_기회', [])) == 0)
    bench_empty = ('경쟁사의_강점_배울점' not in result or 
                   len(result.get('경쟁사의_강점_배울점', [])) == 0)
    
    if opp_empty and bench_empty:
        print(f"\n   ⚠️⚠️⚠️  경고: 경쟁사 분석 섹션이 모두 비어있습니다!")
        print(f"   💡 가능한 원인:")
        print(f"      1. GPT가 경쟁사 리뷰를 충분히 분석하지 못함")
        print(f"      2. max_tokens 부족 (현재: 8000)")
        print(f"      3. 프롬프트 구조 문제")
    
    # 마크다운 변환
    report = convert_to_markdown(result, target_store, target_reviews, competitors, search_strategy)
    
    print(f"   ✅ 분석 완료!")
    
    return report


def convert_to_markdown(json_result, target_store, target_reviews, competitors, search_strategy=None):
    """JSON 결과를 마크다운 리포트로 변환"""
    
    timestamp = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
    
    # 검색 전략 텍스트 (개선)
    strategy_text = ""
    strategy_detail = ""
    if search_strategy:
        strategy_name = search_strategy['name']
        beta = search_strategy['beta']
        alpha = search_strategy['alpha']
        
        strategy_text = f"\n**검색 전략**: {strategy_name} (업종 β={beta}, 지역 α={alpha})"
        
        # 전략 설명 박스
        strategy_detail = f"""
---

## 🎯 경쟁사 선정 로직 (적용된 전략: {strategy_name})

### 가중치 설정
- **업종 가중치 (β)**: {beta} - 같은 업종일수록 높은 점수
- **지역 가중치 (α)**: {alpha} - 같은 지역일수록 높은 점수
- **최종 점수**: 업종유사도×β + 지역적합도×α

### 필터링 규칙
- 업종유사도 < 0.5 → 제외 (거리 무관)
- 장벽 존재 (강/대로/쇼핑몰) → 지역 적합도 ×0.8 패널티
- 리뷰 수 < 30개 → 제외 (신뢰도 부족)

### 대체 전략 (참고용)
"""
        
        # 현재 전략이 아닌 다른 전략들 표시
        all_strategies = [
            ("업종 우선", 2.5, 0.5, "같은 업종을 최우선으로, 지역은 넓게 검색"),
            ("지역 우선", 1.0, 1.5, "같은 지역을 최우선으로, 업종은 다양하게"),
            ("균형", 1.8, 0.9, "업종과 지역을 모두 고려 (기본값)")
        ]
        
        for name, b, a, desc in all_strategies:
            if name != strategy_name:
                strategy_detail += f"- **{name}** (β={b}, α={a}): {desc}\n"
    
    md = f"""# 🏪 {target_store['name']} 경쟁사 분석 리포트

**생성일시**: {timestamp}
**지역**: {target_store['district']} | **업종**: {target_store['industry']}
**분석 리뷰**: 우리 가게 {len(target_reviews)}개 (최근 6개월){strategy_text}

---

## 📊 분석 요약

### 🎯 우선과제 TOP3 (2주 내 실행)

"""
    
    for i, priority in enumerate(json_result.get('summary', {}).get('top_priorities', []), 1):
        md += f"{i}. {priority}\n"
    
    md += f"\n**종합 평가**: {json_result.get('summary', {}).get('overall_assessment', '')}\n"
    md += f"**가장 큰 기회**: {json_result.get('summary', {}).get('biggest_opportunity', '')}\n"
    
    # 1. 우리의 약점
    md += f"\n---\n\n## 🔥 1. 우리의 유의미한 약점 (즉시 개선)\n\n"
    
    weaknesses = json_result.get('우리의_약점', [])
    
    if not weaknesses or (len(weaknesses) == 1 and weaknesses[0].get('aspect') == '없음'):
        md += f"### ✨ 전반적으로 양호\n\n"
        md += f"고객 만족도가 높으며, 실행 가능한 약점이 발견되지 않았습니다.\n"
        md += f"경쟁사 대비 우위를 유지하고 있습니다.\n\n"
        md += f"💡 **전략**: 경쟁사의 약점을 활용한 차별화에 집중\n\n"
    else:
        for weakness in weaknesses:
            md += f"### {weakness.get('priority', 1)}. {weakness['aspect']}\n\n"
            
            if weakness.get('insight_framework'):
                md += f"**🎯 인사이트 프레임워크**: {weakness['insight_framework']}\n\n"
            
            md += f"{weakness['description']}\n\n"
            
            # 통계 표시
            if weakness.get('statistical_evidence'):
                md += f"**📊 통계**: {weakness['statistical_evidence']}\n\n"
            
            # 실제 리뷰
            if weakness.get('sample_reviews'):
                md += "**💬 실제 리뷰**:\n"
                for review in weakness['sample_reviews'][:3]:
                    md += f"- \"{review}\"\n"
                md += "\n"
            
            # 참고 사항
            if weakness.get('note'):
                md += f"💡 **참고**: {weakness['note']}\n\n"
            
            # 액션
            if weakness.get('action'):
                action = weakness['action']
                md += f"**🎬 즉시 액션 (2주 러닝)**\n"
                md += f"- **제목**: {action.get('title', '')}\n"
                md += f"- **방법**: {action.get('how', '')}\n"
                md += f"- **비용**: {action.get('cost', '')}\n"
                md += f"- **난이도**: {action.get('difficulty', '')}\n"
                if action.get('timeline'):
                    md += f"- **기간**: {action['timeline']}\n"
                md += f"- **KPI**: {action.get('kpi', '')}\n"
            md += "\n"
    
    # 2. 우리의 강점
    md += f"---\n\n## ✅ 2. 우리의 유의미한 강점 (유지/확대)\n\n"
    for strength in json_result.get('우리의_강점', []):
        md += f"### {strength['aspect']}\n\n"
        
        if strength.get('insight_framework'):
            md += f"**🎯 인사이트 프레임워크**: {strength['insight_framework']}\n\n"
        
        md += f"{strength['description']}\n\n"
        
        # 통계 표시
        if strength.get('statistical_evidence'):
            md += f"**📊 통계**: {strength['statistical_evidence']}\n\n"
        
        # 실제 리뷰
        if strength.get('sample_reviews'):
            md += "**💬 실제 리뷰**:\n"
            for review in strength['sample_reviews'][:2]:
                md += f"- \"{review}\"\n"
            md += "\n"
        
        # 마케팅 팁 (완성 문장)
        if strength.get('marketing_tip'):
            md += f"**📣 마케팅 메시지**: {strength['marketing_tip']}\n\n"
        
        # 액션
        if strength.get('action'):
            action = strength['action']
            md += f"**🎬 즉시 액션 (2주 러닝)**\n"
            md += f"- **제목**: {action.get('title', '')}\n"
            md += f"- **방법**: {action.get('how', '')}\n"
            if action.get('timeline'):
                md += f"- **기간**: {action['timeline']}\n"
            md += f"- **KPI**: {action.get('kpi', '')}\n"
        
        md += "\n"
    
    # 3. 경쟁사의 약점 = 우리의 기회
    md += f"---\n\n## 💡 3. 경쟁사의 약점 = 우리의 차별화 기회\n\n"
    
    comp_opps = json_result.get('경쟁사의_약점_우리의_기회', [])
    if not comp_opps:
        md += "⚠️ 경쟁사 리뷰 분석 결과가 부족합니다. 더 많은 경쟁사 리뷰 데이터가 필요합니다.\n\n"
    else:
        for opp in comp_opps:
            md += f"### 🎯 {opp['aspect']}\n\n"
            md += f"{opp['description']}\n\n"
            
            # 통계 표시 (있으면)
            if opp.get('statistical_evidence'):
                md += f"**📊 통계**: {opp['statistical_evidence']}\n\n"
            
            md += f"**💡 기회**: {opp.get('opportunity', '')}\n"
            if opp.get('marketing_message'):
                md += f"**📣 마케팅 메시지**: \"{opp['marketing_message']}\"\n"
            
            # 경쟁사 리뷰 샘플 (있으면)
            if opp.get('sample_comp_reviews'):
                md += "\n**경쟁사 리뷰 예시**:\n"
                for review in opp['sample_comp_reviews'][:2]:
                    md += f"- {review}\n"
            
            md += "\n"
    
    # 4. 경쟁사의 강점 = 배울 점
    md += f"---\n\n## 📚 4. 경쟁사의 강점 = 우리가 벤치마킹할 점\n\n"
    
    comp_benchs = json_result.get('경쟁사의_강점_배울점', [])
    if not comp_benchs:
        md += "⚠️ 경쟁사 리뷰 분석 결과가 부족합니다. 더 많은 경쟁사 리뷰 데이터가 필요합니다.\n\n"
    else:
        for bench in comp_benchs:
            md += f"### 🔍 {bench['aspect']}\n\n"
            
            if bench.get('insight_framework'):
                md += f"**🎯 인사이트 프레임워크**: {bench['insight_framework']}\n\n"
            
            md += f"{bench['description']}\n\n"
            
            # 통계 표시 (있으면)
            if bench.get('statistical_evidence'):
                md += f"**📊 통계**: {bench['statistical_evidence']}\n\n"
            
            md += f"**📋 벤치마크**: {bench.get('benchmark', '')}\n"
            md += f"**🎬 실행 계획**: {bench.get('action_plan', '')}\n"
            
            # 경쟁사 리뷰 샘플 (있으면)
            if bench.get('sample_comp_reviews'):
                md += "\n**경쟁사 리뷰 예시**:\n"
                for review in bench['sample_comp_reviews'][:2]:
                    md += f"- {review}\n"
            
            md += "\n"
    
    # 액션 아이템
    md += f"---\n\n## 🎬 즉시 실행 가능한 액션 플랜 (2주 러닝)\n\n"
    for i, action in enumerate(json_result.get('action_items', []), 1):
        md += f"### 액션 {i}: {action.get('title', '제목 없음')}\n\n"
        md += f"**📂 카테고리**: {action.get('category', '미분류')}\n\n"
        if action.get('why'):
            md += f"**❓ 왜 필요한가?**\n{action['why']}\n\n"
        if action.get('how'):
            md += f"**🔧 어떻게 실행?**\n{action['how']}\n\n"
        md += f"**💰 비용**: {action.get('cost', '미정')}\n"
        md += f"**🎯 난이도**: {action.get('difficulty', '보통')}\n"
        if action.get('timeline'):
            md += f"**⏱️ 기간**: {action['timeline']}\n"
        md += f"**📊 KPI**: {action.get('kpi', '미정')}\n\n"
    
    # 경쟁사 목록 (명칭 정리)
    md += f"---\n\n## 📌 경쟁사 목록\n\n"
    for i, comp in enumerate(competitors, 1):
        # 명칭 정리: "브랜드카테고리,카테고리2" → "브랜드 (카테고리·카테고리2)"
        comp_name = comp.name
        comp_district = comp.district
        
        # 카테고리 분리 처리
        if ',' in comp_name:
            parts = comp_name.split(',')
            if len(parts) > 1:
                # 첫 번째가 브랜드명, 나머지가 카테고리
                brand = parts[0]
                categories = ' · '.join(parts[1:])
                comp_name = f"{brand} ({categories})"
        
        md += f"{i}. **{comp_name}** - {comp_district} - {comp.review_count}개 리뷰\n"
    
    # 경쟁사 선정 로직 박스 추가
    if strategy_detail:
        md += strategy_detail
    
    # 메타데이터
    md += f"""
---

## 📊 분석 메타데이터

### 기본 정보
- **분석 모델**: GPT-4o (temperature=0.0, 할루시네이션 방지)
- **분석 일시**: {timestamp}
- **데이터 기간**: 최근 6개월
- **우리 리뷰 수**: {len(target_reviews)}개
- **경쟁사 수**: {len(competitors)}개
- **분석 방식**: 통계적 유의성 + 4단계 분류 + 9가지 인사이트 프레임워크

### 통계 표기 형식
모든 통계는 다음 형식으로 표시됩니다:
- **형식**: "우리 X.X%(n=N1) vs 경쟁사 Y.Y%(n=N2); GAP ±Z.Z%p; 95% CI [L, U]; P=0.XX 🟢"
- **n**: 표본 수 (전체 리뷰 중 해당 키워드 언급 가능 리뷰 수)
- **GAP**: 우리와 경쟁사의 차이 (%p = percentage point)
- **95% CI**: 95% 신뢰구간 (차이의 불확실성 범위)
- **P**: P-value (통계적 유의성, P<0.05면 유의미)

### 신뢰 배지 의미
- 🟢 **높은 신뢰도**: 표본 충분(n≥100) & CI 좁음(<0.15) & 통계적 유의(P<0.05)
- 🟡 **경계 신뢰도**: P-value가 0.05~0.10 (유의미할 가능성)
- ⚪️ **참고용**: 표본 부족(n<50) 또는 통계적으로 유의하지 않음

### 9가지 검증된 인사이트 프레임워크
1. **대기(웨이팅) 언급률**: 낮으면 곧 기회 → 빠른 입장 메시지
2. **재방문 의향 시그널**: 작아도 강력 → 충성도 루프 설계
3. **맛의 방향성**: 취향 좌표 → 옵션 명시
4. **시그니처 단일화**: 대표 메뉴 전면 배치
5. **온도/식감 클레임**: 즉시 하드픽스
6. **피크타임 서비스 편차**: 인력/동선 개선
7. **분위기/공간 키워드**: 돈 되는 쓰임새 → UGC 유도
8. **가격 불만**: 구성 문제 → 앵커 가격 세팅
9. **경쟁사 강점**: 라이트 벤치 → 2주 파일럿

### 4단계 분류
1. 🔥 **우리의 약점** → 즉시 개선 (P<0.05 & GAP<-0.10)
2. ✅ **우리의 강점** → 유지/확대 (P<0.05 & GAP>+0.10)
3. 💡 **경쟁사의 약점** → 차별화 기회 (마케팅 포인트)
4. 📚 **경쟁사의 강점** → 벤치마킹 대상 (2주 파일럿)

### 검증 프로세스 (6단계)
1. 샘플 리뷰 목록 재확인
2. 키워드로 찾기
3. 정확히 일치하는 문장 찾기
4. 리뷰 번호와 함께 원문 그대로 복사
5. 자기 검증 (100% 확신)
6. 개수 확인 + 스케일 맞추기 (비율 기반)

### 실행 가능성 필터
- ✅ **포함**: 맛/서비스/가격/청결/메뉴/대기/재방문/온도
- ❌ **제외**: 주차/건물크기/위치/소음(건물구조)/계단/엘리베이터
- **기준**: 사장님이 3개월 내 해결 가능한 것만
"""
    
    return md