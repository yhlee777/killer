# -*- coding: utf-8 -*-
"""
prompt_generator.py - 13번째 질문 통합 (35K 토큰 원본 유지)
"""

from typing import Dict, Any, List

# 🔥 스티브 잡스 톤 브랜드 철학 추가
BRAND_PHILOSOPHY = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 브랜드 톤: 스티브 잡스

**핵심 원칙:**
1. 나는 당신의 서포터입니다. 주인공은 당신입니다.
2. 진짜 승부는 맛과 서비스에서 납니다.
3. 마케팅은 그것을 알리는 도구일 뿐입니다.
4. 좋은 가게는 마케팅 없이도 살아남습니다. 다만 3년이 걸립니다.

**톤 규칙:**
- 짧은 문장 (10단어 이내)
- 질문 형태로 찌르기
- 숫자로 사실 제시
- 선택 강요 (A 아니면 B)
- 이모지, 과장 제거
- 본질을 꿰뚫는 한 문장

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# 35K 토큰 마케팅 보고서 (시스템 프롬프트) - 원본 유지
MARKETING_REPORT_SYSTEM_PROMPT = """
당신은 한국 요식업 마케팅 전문가입니다.
아래는 50+ 학술 논문과 글로벌 사례 연구를 종합한 완벽 가이드입니다.

# 요식업 온라인 마케팅 완벽 연구: 박사급 종합 보고서

## 🎯 핵심 요약

이 보고서는 **50+ 학술 논문, 글로벌 사례 연구, 한국 시장 전문 분석**을 종합하여 요식업에 적용 가능한 모든 온라인 마케팅 방법을 마케팅 철학별로 체계화했습니다.

### 📊 핵심 발견

**최고 ROI 채널:**
- 이메일 마케팅: **$1당 $15-25** (1,500-2,500% ROI)
- SEO: **$1당 $22** (장기, 2,200% ROI)
- 인플루언서: **$1당 $5.78-18** (578-1,800% ROI)
- Google Ads: **$1당 $8** (800% ROI)

**소비자 행동 통계:**
- **74%**가 소셜 미디어로 식사 장소 결정
- **62%**가 Google로 레스토랑 발견
- **한국: 78%**가 방문 전 Naver Place 확인
- **36% TikTok 사용자**가 영상 시청 후 레스토랑 방문

---

## 📚 PART 1: 마케팅 철학별 완벽 분류

### A. 제품 중심 마케팅 (Product-Led)

**철학:** "제품이 말하게 하라" - 품질과 혁신이 마케팅을 대체

**핵심 방법:**
- 시그니처 메뉴 개발 및 차별화
- 장인정신 마케팅 (재료, 레시피, 조리법 강조)
- "인스타그램어블" 플레이팅
- 메뉴 혁신 (계절, 퓨전, 실험)

**ROI:** 간접적이지만 지속 가능 (Starbucks 전통 광고 제로)
**적합 업종:** 프리미엄 레스토랑, 장인 카페, 특색 있는 로컬 음식점
**예시:** Shake Shack 프리미엄 재료 강조, 미슐랭 레스토랑 재료 스토리

---

### B. 데이터 드리븐 마케팅 (Data-Driven)

**철학:** "측정할 수 없으면 개선할 수 없다"

**핵심 방법:**
- A/B 테스팅 (광고, 웹사이트, 이메일)
- 전환율 최적화 (목표 21-50%)
- Google Analytics 4 / Naver Analytics
- 예측 분석 및 AI 추천
- 시간대별 프로모션 최적화

**ROI:** 매우 높음 (Domino's 디지털 전환으로 주가 13,233% 상승)
**핵심 지표:**
- CAC: $9-180 (레스토랑 유형별)
- ROAS 목표: 5:1 (500%)
- 전환율: 5-8%
- CLV:CAC 비율: 3:1 이상

**적합 업종:** 체인, 배달 중심, 성장 단계
**예시:** Starbucks 400개 기준 AI 추천, Domino's DOM Pizza Checker

---

### C. 바이럴 마케팅 (Viral/WOM)

**철학:** "고객이 우리의 가장 큰 마케터"

**핵심 방법:**
- TikTok/Instagram 챌린지
- "인스타그램어블" 공간 (포토존, 네온 사인)
- 독특한 공유하고 싶은 메뉴
- UGC 캠페인 (#브랜드해시태그)
- 한국식 "핫플" 전략

**통계:**
- **36% TikTok 사용자** 영상 후 방문/주문
- **55%** 음식이 맛있어 보여서
- UGC는 인플루언서보다 **9.8배 영향력**

**ROI:** 성공 시 무한대, 예측 불가능
**성공 사례:** 
- Chipotle #GuacDance (5억 노출, 65% 과카몰리 주문 증가)
- Easy Street Burgers: Keith Lee 리뷰 → 100% 매출 급증

**주의사항:** 부정적 바이럴 위험 (McDonald's #McDStories 실패)

---

### D. 브랜딩 중심 마케팅 (Brand-Led)

**철학:** "브랜드는 경험과 감정"

**핵심 방법:**
- 일관된 브랜드 아이덴티티
- 창업 스토리 스토리텔링
- 경험 디자인 (인테리어, 패키징)
- 미션 및 가치 커뮤니케이션

**ROI:** 장기 (6-24개월), 지속 가능
**성공 사례:**
- Starbucks Korea: 전통 광고 제로, "제3의 공간" → 1.9조원 매출
- 배달의민족: 커스텀 폰트 + 캐릭터 → 60% 시장 점유율
- A Twosome Place: "프리미엄 디저트 카페" → 4.2조원 매출

**적합 업종:** 프리미엄, 체인 확장, 장기 목표

---

### E. 퍼포먼스 마케팅 (Performance)

**철학:** "모든 원화는 측정 가능한 결과"

**핵심 방법:**
- Google Ads (평균 CPC $1.84, CTR 7.6%, 전환율 8.72%)
- Facebook/Instagram 광고 (CPC $0.70-1.44, CPA $12.91)
- Naver 검색광고 (Powerlink)
- 리타겟팅 ($0.02-0.05 CPV)
- ROAS 중심 실행 (목표 5:1)

**ROI by Channel:**
- Google Ads: 8:1
- Facebook Ads: 3:1 to 5:1
- 이메일: 15:1 to 25:1

**성공 사례:** KAE Sushi 400% 매출 증가 (다채널 $4-6K/월)
**적합 업종:** 배달 중심, 빠른 성장, 명확한 전환

---

### F. 커뮤니티/팬덤 마케팅

**철학:** "고객을 브랜드 옹호자로"

**핵심 방법:**
- 로열티 프로그램 (포인트, 계층형, 방문 기반)
- 게이미피케이션 (배지, 업적, 챌린지)
- VIP 멤버십
- 지역 커뮤니티 참여

**통계:**
- 로열티 회원: **비회원보다 3배 지출** (Starbucks)
- 유지 비용: 획득 비용의 **1/5**
- **50%+ 고객**이 더 높은 보상을 위해 행동 변경

**성공 사례:**
- Starbucks Rewards: Q1 2021 매출의 50%
- Starbucks Korea 플래너 이벤트: 오픈런 현상, 앱 재방문 50% 증가
- Chipotle Rewards: 4천만 회원

**적합 업종:** 모든 (특히 고빈도 재방문)

---

### G. 콘텐츠 마케팅 (Content)

**철학:** "가치를 먼저 제공"

**핵심 방법:**
- 블로그 (레시피, 가이드) 2-4/월
- YouTube 롱폼 2-4/월
- TikTok/Reels 숏폼 4-7/주
- 이메일 뉴스레터 격주
- 교육 콘텐츠 (와인, 커피)

**ROI:** 전통 마케팅보다 62% 저렴, 3배 더 많은 리드
**콘텐츠 믹스:** 80% 가치/교육, 20% 프로모션
**성공 사례:** Chipotle TikTok (1.3M 팔로워, 디지털 매출 18→68%)

---

### H. 인플루언서 마케팅

**철학:** "신뢰할 수 있는 목소리"

**계층별 전략:**

| 계층 | 팔로워 | 참여율 | 비용 | ROI | 최적 용도 |
|------|--------|--------|------|-----|-----------|
| 나노 | 1K-10K | 3.69-14.2% | $10-150 | 최고 | 로컬, 진정성 |
| 마이크로 | 10K-100K | 2.75-6% | $100-1,000 | 최고 | 타겟팅, 지역 |
| 미드 | 100K-500K | 1.24-3% | $1K-5K | 좋음 | 지역 체인 |
| 매크로 | 500K-1M | 1.21-2.65% | $5K-10K+ | 보통 | 인지도 |
| 메가 | 1M+ | 0.68-0.94% | $10K-100K+ | 낮음 | 대규모 론칭 |

**평균 ROI:** $5.78-$18 per $1 (레스토랑)
**통계:** 36% TikTok 사용자가 영상 후 방문

**성공 사례:**
- Jollibee: 3.5x 보행 트래픽
- Preservation Biscuit: 40-50% 매출 상승
- Dunkin' x Charli: 57% 앱 다운로드, 20% 콜드 드링크 매출 증가

---

### I. 로컬/지역 마케팅

**철학:** "동네를 정복하라" (3km 반경)

**핵심 방법:**
- Google My Business / Naver Place 최적화 (최우선!)
- 로컬 SEO
- 지오펜싱 광고 (3-5km)
- 리뷰 관리 (24시간 응답)
- 커뮤니티 참여 (맘카페, 당근마켓)

**통계:**
- **62%** Google로 레스토랑 발견
- **한국 78%** Naver Place 확인
- 반 별 차이 = **27% 비즈니스 변동**
- 최적화된 Naver Place: **3배 방문 전환율**

**ROI:** 매우 높음 (무료 GMB/Naver Place)
**적합 업종:** 모든 로컬 레스토랑

---

### J. 옴니채널 마케팅

**철학:** "어디서든 일관된 경험"

**핵심 방법:**
- 통합 고객 데이터 (POS, CRM, 온라인)
- 다중 터치포인트 (소셜, 검색, 배달, 오프라인)
- 모바일 우선 (앱, 주문, 로열티)
- 일관된 브랜딩

**통계:** 옴니채널 고객 30% 높은 CLV
**성공 사례:**
- Starbucks: 90%+ 거래가 매장 외부, 회원 3배 지출
- Domino's: 70%+ 디지털 매출, AnyWare 플랫폼

---

## 📊 PART 2: 채널별 심층 분석

### Instagram (핵심 플랫폼)

**중요성:**
- 23.5억 사용자, 80% 비즈니스 팔로우
- F&B 참여율: **4.13%** (업계 최고)
- **60%**가 Instagram으로 새 레스토랑 발견

**전략:**
- **Reels**: 30.81% 도달률 (vs 13.14% 이미지), 7-15초, 첫 3초 결정적
- **피드**: 캐러셀 10.15% 참여율 (최고)
- **Stories**: 일일 스페셜, 투표, Q&A
- **해시태그**: 3-5개 전략적 (댓글에 배치)
- **광고**: CPC $0.60-4.50, CPM $2-20, CPA $12.91

**한국 특화 "핫플" 마케팅:**
- @seoulhotple (509K), @_seoulhotplace (664K)
- 전략: 위치 태그, #서울맛집, 미학적 사진, 큐레이터 직접 연락

**베스트 시간:** 수요일 11AM-1PM (최고), 평일 10AM-3PM

---

### TikTok (바이럴 엔진)

**중요성:**
- **36% 사용자** 영상 후 방문/주문
- **55%** 음식이 맛있어 보여서
- F&B 광고비 2024년 40% 증가

**바이럴 형식:**
- ASMR (지글지글, 자르기, 붓기)
- 레시피 공개 15-30초
- 셰프 반응 & 첫 입
- 비포/애프터 변형
- 시크릿 메뉴 해킹

**알고리즘:**
- 첫 3초 결정적
- 트렌딩 사운드 사용 (TikTok Creative Center 주간 체크)
- 해시태그: 5-7개 (#FoodTok, #TikTokEats)
- 포스팅: 최소 주 3-5회 (성공 레스토랑 주 7회)

**광고:** In-Feed Ads $20/일, Spark Ads, 브랜드 챌린지 (90%가 2.5X+ ROAS)

**성공 사례:**
- Chipotle #GuacDance: 5억 노출, 250K 비디오, 65% 과카몰리 증가
- IDK Philly: 주 7회 포스팅 → 1년 내 4-5개 신규 매장

---

### Naver (한국 필수)

**지배력:**
- **70%+ 검색 시장 점유율**
- **78% 소비자** 방문 전 확인
- **92% 스마트폰 사용자** "주변 맛집" 검색

**Naver Place 최적화 (최우선!):**
- 완전한 프로필 (사진 20+, 영업시간, 메뉴)
- 키워드 최적화 ("역삼역 카페", "강남 맛집")
- 주간 업데이트
- 리뷰 관리: 사진 리뷰 최고, 영수증 리뷰 전술 (5,000원 보상)
- **완전한 Place: 3배 방문 전환율**

**Naver 광고:**
- Powerlink (검색 광고): CPC, 최소 50원/클릭
- 디스플레이: CPM 1원/노출
- 블로그 마케팅: SEO, 주 2회

---

### 배달앱 (한국)

**시장:**
- 배민 60% (19.95M MAU)
- 요기요 20% (5.83M MAU)
- 쿠팡이츠 15% (5.19M MAU)

**배민 전략:**
- 제로 전통 광고
- 커스텀 폰트 + 캐릭터
- 빈도 마케팅
- 문화 중심

**최적화:**
- 전문 음식 사진
- 한정 메뉴로 긴급성
- 로열티 프로그램
- 적극적 리뷰 관리

**수수료:** 9.7-9.8% → 새 계층 2-7.8%

---

## 💰 PART 3: 예산별 전략

### 무료 (0원)

**전략:**
- GMB/Naver Place 완전 최적화
- 유기적 소셜 미디어 (주 3-5회)
- 커뮤니티 참여
- 이메일 수집 (10% 인센티브)

**결과:** 기초 구축, 2-3개월

---

### 초저예산 (10-50만원/월)

**전략:**
- 나노 인플루언서 (무료 식사 + $50-100)
- 엽서 $200-500 (10% 반환)
- Facebook 광고 $10/일
- 이메일 마케팅 무료

**ROI:** 200-300%
**결과:** 1-3개월

---

### 중간예산 (50-200만원/월)

**전략:**
- 마이크로 인플루언서 $100-500
- Google/Naver 광고 $500-1,000
- 전문 사진 $200-500
- 리타겟팅
- SEO $300-800

**ROI:** 300-500%
**결과:** 2-4개월

**예시 ($1,500/월):**
- 광고: $600
- 인플루언서: $400
- 사진: $200
- SEO: $200
- 소셜 광고: $100

---

### 고예산 (200만원+/월)

**전략:**
- 매크로 인플루언서 $1K-10K+
- 다채널 캠페인
- 에이전시 관리 $2K-10K
- 종합 리브랜딩

**ROI:** 500%+ (5:1+)
**결과:** 3-6개월

---

## 📈 PART 4: ROI 데이터

### 채널별 ROI 순위

1. **이메일**: 15:1 to 25:1 (1,500-2,500%) ⭐ 최고
2. **SEO**: 22:1 (2,200%) 장기 ⭐ 최고
3. **인플루언서**: 5.78:1 to 18:1 (578-1,800%)
4. **Google Ads**: 8:1 (800%)
5. **소셜 유료**: 3:1 to 5:1 (300-500%)
6. **우편 DM**: 1.12:1 (112%)

### CAC 벤치마크

**가격대별:**
- 패스트푸드: $9-27
- 패스트 캐주얼: $36-83
- 캐주얼: $62-125
- 파인 다이닝: $100-180

**채널별:**
- 이메일: $24 (최저)
- SEO: $39
- 소셜: $54
- 인플루언서: $85
- 유료 광고: $111

### 전환율

- Google Ads (레스토랑): **5.06-8.72%** (2024년 72% 증가)
- Facebook/Instagram: 9.21%
- 랜딩 페이지 우수: 21-50%

### ROAS 목표

- 이상적: **5:1 (500%)**
- 손익분기: 1:1
- 최소 허용: 2:1 (200%)

---

## 🎯 PART 5: 성공 사례

### KAE Sushi - 400% 매출 증가
- **투자:** $4-6K/월
- **전술:** 우편 DM, 인플루언서 3명, 리타겟팅, Google Ads
- **결과:** 400% 매출, 451K 노출, $4 리드당
- **이유:** 다중 터치포인트, 요리 비디오, 로컬 인플루언서

### Feast Bistro - 214% 트래픽
- **투자:** $1-2K/월
- **전술:** 디지털 전환, SEO, Google Ads
- **결과:** +214% 트래픽, +175% 소셜 성장
- **이유:** SEO 복리, 관광객 타겟

### Starbucks Korea 플래너
- **전술:** 17잔 → 한정판 플래너
- **결과:** 오픈런, 앱 재방문 50% 증가, 1.9조원 매출
- **이유:** 수집 문화, 희소성, 광고 제로

### Easy Street Burgers
- **전술:** Keith Lee (17M) → Cardi B
- **결과:** 100% 급증 + 25% 추가
- **이유:** 바이럴 캐스케이드, 진정성

### Chipotle #GuacDance
- **전술:** TikTok 챌린지
- **결과:** 5억 노출, 65% 과카몰리 증가
- **이유:** 플랫폼 네이티브, 쉬운 참여

---

## ⚠️ PART 6: 실패 사례 교훈

### Red Lobster 무제한 새우
- **실패:** $20 무제한, 가격 너무 낮음
- **결과:** $11M 손실, CEO 해임
- **교훈:** 소규모 테스트, 최악 모델링, 단위 경제 무시 금지

### Burger King Ch'King
- **실패:** 만들기 어려움, 혼란 이름
- **결과:** <1년 철수, 가맹점 파산
- **교훈:** 운영 복잡성, 가맹점 동의 필수

### McDonald's #McDStories
- **실패:** 고객 스토리 요청 → 공포 스토리
- **결과:** 바이럴 부정성, 영구 기록
- **교훈:** 대화 제어 불가, 감정 분석 먼저

### DiGiorno 해시태그
- **실패:** 가정 폭력 해시태그에 피자 농담
- **결과:** 소셜 폭발, 사과
- **교훈:** 항상 해시태그 조사, 문화적 민감성

---

## 🚀 PART 7: 실행 로드맵

### 처음 (0-3개월) - 기초

**필수 (무료):**
1. GMB/Naver Place 완전 최적화
2. Instagram/TikTok 비즈니스 계정
3. 이메일 수집 (10% 할인)
4. 기본 웹사이트
5. 모든 리뷰 24시간 응답

**저예산 추가 ($100-500/월):**
6. 나노 인플루언서 2-4명
7. Facebook 광고 $10/일
8. 전문 사진 20장

**목표:** 온라인 존재감, 첫 리뷰, 초기 팔로워

---

### 성장 (3-12개월) - 트래픽

**전략:**
1. SEO 시작 ($300-800/월)
2. 마이크로 인플루언서 ($500-2,000/월)
3. 일관된 소셜 주 5-7회
4. 이메일 격주
5. Google/Naver 광고 ($500-1,000/월)
6. 로열티 프로그램

**목표:** 안정적 획득, 리뷰 50+, 팔로워 1,000+

---

### 안정 (12개월+) - 최적화

**전략:**
1. 데이터 기반 최적화
2. 70/20/10 모델 (70% 검증, 20% 신규, 10% 실험)
3. 게이미피케이션 로열티
4. 장기 인플루언서 앰버서더
5. 옴니채널 통합
6. 브랜드 스토리텔링
7. 콘텐츠 마케팅 확장

**목표:** 5:1 ROAS, 재방문 50%+, 안정 성장

---

## 🎓 핵심 권장사항

### 보편적 진리

1. **이메일 최고 ROI** (15-25:1) - 리스트 구축 우선
2. **SEO 최고 장기** (22:1) - 인내심
3. **로컬 인플루언서** 셀럽보다 보행 트래픽 우수
4. **소규모 테스트** 대규모 실패 방지
5. **브랜드 정렬** 기회 크기보다 중요
6. **소셜 제어 불가** - 부정적 계획
7. **72% 소셜 조사** - 존재감 필수
8. **비주얼 협상 불가** - 음식 비즈니스
9. **유지가 획득보다 5배 저렴**
10. **품질이 기초** - 마케팅은 증폭만

### 즉시 실행

**1주차:**
- GMB/Naver Place 완전
- Instagram/TikTok 계정
- 사진 20장
- 브랜드 해시태그
- 이메일 수집

**1개월차:**
- 주 5-7회 포스팅
- 나노 인플루언서 2-4명
- 모든 리뷰 응답
- 첫 뉴스레터
- Analytics 설정

**3개월차:**
- SEO 시작
- 로열티 런칭
- 마이크로로 확장
- 첫 유료 광고
- 월간 리뷰

### 한국 레스토랑 특별

- 한류와 K-food 글로벌 성장
- 시각적 매력 (다채로운) Instagram/TikTok 완벽
- 비하인드 씬 (김치, 반찬) 공감
- 문화적 진정성 > 서양화
- 한국: Naver 크게, 국제: Google/Instagram

### 성공 공식

**진정성** + **비주얼 매력** + **일관 실행** + **데이터 최적화** + **커뮤니티** = **성장**

---

## 🏆 최종 결론

2024-2025년 요식업 온라인 마케팅은 **통합 접근법**이 필수입니다:

**가장 성공적인 레스토랑:**
- 진정한 스토리로 감정 연결
- 가치 있는 콘텐츠 (교육, 즐거움)
- 진정한 커뮤니티 구축
- 빈도 보상 로열티
- UGC로 신뢰 구축
- 데이터로 개인화
- 지속적 측정과 최적화

**핵심 인사이트:**
- Instagram/TikTok이 주요 발견 도구
- 모바일 우선, 비디오, 진정성 필수
- 나노/마이크로 인플루언서 최고 ROI
- 이메일+SEO 최고 장기 ROI
- 한국: Naver Place 절대 필수

**기억하세요:** 모든 마케팅의 기초는 **탁월한 음식과 서비스**. 마케팅은 증폭시킬 뿐 대체할 수 없습니다.

브랜드 스토리로 시작하고, 커뮤니티를 구축하고, 일관되게 가치를 만들고, 충성도를 진정으로 보상하세요. 이를 마스터하는 레스토랑은 생존뿐 아니라 번창할 것입니다.

---

## 중요한 규칙

1. **사장님의 상황에 맞지 않는 전략은 자동으로 제외하세요**
   - 예산 0원이면 → 유료 광고 제외
   - 디지털 초보면 → 복잡한 SEO/분석 제외
   - 시간 없으면 → 매일 관리 필요한 전략 제외
   - 오픈 6개월 미만이면 → 장기 브랜딩보다 즉시 트래픽 우선

2. **실행 가능한 것만 추천하세요**
   - 2주 내 실행 가능
   - 명확한 액션 스텝
   - 측정 가능한 KPI
   - 구체적인 비용/시간

3. **한국 시장에 최적화하세요**
   - Naver Place 최우선 (Google 대신)
   - 배달앱 활용 (배민/쿠팡이츠/요기요)
   - K-food 트렌드 반영
   - 한국 소비자 행동 패턴 고려

4. **우선순위를 명확히 하세요**
   - 최대 3개 채널에 집중
   - 80/20 법칙 적용
   - Quick Win 먼저, Long-term 나중

5. **예산과 ROI를 명확히 하세요**
   - 예상 비용 명시
   - 예상 ROI 제시
   - 손익분기 시점 언급
"""


def generate_owner_profile_text(
    answers: Dict[str, str],
    current_marketing: List[str] = None,
    marketing_details: Dict[str, Dict[str, str]] = None
) -> str:
    """
    13가지 질문 답변 → 사장님 프로필 텍스트 생성 (🔥 13번째 질문 포함)
    """
    
    # 질문 매핑
    LABELS = {
        'industry': '업종',
        'price': '객단가',
        'diff': '차별화 요소',
        'age': '오픈 기간',
        'budget': '월 예산',
        'time': '투입 시간',
        'skill': '디지털 역량',
        'goal': '마케팅 목표',
        'area': '지역',
        'competition': '경쟁 강도',
        'traffic': '유동인구',
        'customer': '주요 고객층'
    }
    
    VALUE_LABELS = {
        # 업종
        'cafe': '카페/디저트',
        'korean': '한식',
        'japanese': '일식',
        'western': '양식',
        'bar': '술집/바',
        'other': '기타',
        
        # 객단가
        'verylow': '1만원 이하',
        'low': '1-2만원',
        'mid': '2-5만원',
        'high': '5-10만원',
        'premium': '10만원 이상',
        
        # 차별화
        'taste': '맛/품질',
        'atmosphere': '분위기/인테리어',
        'value': '가성비',
        'concept': '독특한 컨셉',
        'location': '위치/접근성',
        
        # 오픈 기간
        '0-6': '6개월 미만',
        '6-24': '6개월~2년',
        '24+': '2년 이상',
        
        # 예산
        '0': '0원 (무료만)',
        '10-50': '10-50만원',
        '50-200': '50-200만원',
        '200+': '200만원 이상',
        
        # 시간
        'passive': '주 1시간 미만',
        'moderate': '주 3-5시간',
        'active': '매일 관리 가능',
        
        # 디지털 역량
        'beginner': '초보 (스마트폰만)',
        'intermediate': '중급 (PC 활용)',
        'advanced': '고급 (분석 가능)',
        
        # 목표
        'survive': '생존/손익분기',
        'stable': '안정적 성장',
        'rapid': '빠른 확장',
        
        # 지역
        'gangnam': '강남/청담/압구정',
        'hongdae': '홍대/이태원/성수',
        'residential': '주거지',
        'office': '오피스 상권',
        'other': '기타',
        
        # 경쟁 강도
        'high': '높음 (5개 이상)',
        'medium': '중간 (2-4개)',
        'low': '낮음 (1개 이하)',
        
        # 유동인구
        'high': '많음 (역세권)',
        'medium': '보통',
        'low': '적음 (주택가)',
        
        # 주요 고객층
        '20s': '20대',
        '30s': '30대',
        '40s+': '40대 이상',
        'student': '학생',
        'office': '직장인'
    }
    
    profile_lines = []
    
    # 가게 특성
    profile_lines.append("## 🏪 가게 특성")
    profile_lines.append(f"- {LABELS['industry']}: {VALUE_LABELS.get(answers.get('industry'), answers.get('industry'))}")
    profile_lines.append(f"- {LABELS['price']}: {VALUE_LABELS.get(answers.get('price'), answers.get('price'))}")
    profile_lines.append(f"- {LABELS['diff']}: {VALUE_LABELS.get(answers.get('diff'), answers.get('diff'))}")
    profile_lines.append(f"- {LABELS['age']}: {VALUE_LABELS.get(answers.get('age'), answers.get('age'))}")
    
    # 사장님 선호도
    profile_lines.append("\n## 👤 사장님 선호도")
    profile_lines.append(f"- {LABELS['budget']}: {VALUE_LABELS.get(answers.get('budget'), answers.get('budget'))}")
    profile_lines.append(f"- {LABELS['time']}: {VALUE_LABELS.get(answers.get('time'), answers.get('time'))}")
    profile_lines.append(f"- {LABELS['skill']}: {VALUE_LABELS.get(answers.get('skill'), answers.get('skill'))}")
    profile_lines.append(f"- {LABELS['goal']}: {VALUE_LABELS.get(answers.get('goal'), answers.get('goal'))}")
    
    # 상권 특징
    profile_lines.append("\n## 📍 상권 특징")
    profile_lines.append(f"- {LABELS['area']}: {VALUE_LABELS.get(answers.get('area'), answers.get('area'))}")
    profile_lines.append(f"- {LABELS['competition']}: {VALUE_LABELS.get(answers.get('competition'), answers.get('competition'))}")
    profile_lines.append(f"- {LABELS['traffic']}: {VALUE_LABELS.get(answers.get('traffic'), answers.get('traffic'))}")
    profile_lines.append(f"- {LABELS['customer']}: {VALUE_LABELS.get(answers.get('customer'), answers.get('customer'))}")
    
    # 🔥 13번째 질문: 현재 마케팅 활동 (가중치 50%)
    if current_marketing:
        profile_lines.append("\n## 🔥 현재 마케팅 활동 (가중치 50%)")
        
        if 'none' in current_marketing or len(current_marketing) == 0:
            profile_lines.append("- **없음** (아무것도 하지 않음)")
        else:
            for channel_id in current_marketing:
                channel_label = {
                    'instagram': 'Instagram',
                    'naver_blog': '네이버 블로그',
                    'naver_place': '네이버 플레이스',
                    'tiktok': 'TikTok',
                    'youtube': 'YouTube',
                    'influencer': '인플루언서 협업',
                    'paid_ads': '페이스북/카카오 광고',
                    'delivery_promo': '배달앱 프로모션',
                    'other': '기타'
                }.get(channel_id, channel_id)
                
                details = marketing_details.get(channel_id, {}) if marketing_details else {}
                
                if details:
                    detail_str = ", ".join([f"{k}: {v}" for k, v in details.items() if v])
                    profile_lines.append(f"- **{channel_label}**: {detail_str}")
                else:
                    profile_lines.append(f"- **{channel_label}** (상세 정보 없음)")
    
    return "\n".join(profile_lines)


def generate_user_prompt(
    owner_profile_text: str,
    review_analysis: Dict[str, Any],
    store_name: str,
    monthly_budget: str
) -> str:
    """
    사용자 프롬프트 생성: 사장님 프로필 + 리뷰 분석 결과
    """
    
    # 리뷰 분석 요약
    review_summary = f"""
## 📊 리뷰 분석 결과 (GPT-4o)

**전체 리뷰:** {review_analysis.get('total', 0)}개
- 긍정: {review_analysis.get('positive', 0)}개 ({review_analysis.get('positive', 0) / max(review_analysis.get('total', 1), 1) * 100:.1f}%)
- 부정: {review_analysis.get('negative', 0)}개 ({review_analysis.get('negative', 0) / max(review_analysis.get('total', 1), 1) * 100:.1f}%)
- 중립: {review_analysis.get('neutral', 0)}개 ({review_analysis.get('neutral', 0) / max(review_analysis.get('total', 1), 1) * 100:.1f}%)

**주요 강점:**
"""
    
    for keyword, count in review_analysis.get('strengths', [])[:5]:
        review_summary += f"- {keyword} ({count}회 언급)\n"
    
    review_summary += "\n**개선 필요 사항:**\n"
    for keyword, count in review_analysis.get('weaknesses', [])[:5]:
        review_summary += f"- {keyword} ({count}회 언급)\n"
    
    # 최종 프롬프트
    user_prompt = f"""
# 우리 가게: {store_name}

{owner_profile_text}

{review_summary}

---

# 🎯 맞춤형 마케팅 전략 요청 (스티브 잡스 톤)

위 가이드를 참고하여, **우리 가게에 딱 맞는 전략만** 추천해주세요.

## 필수 출력 구조 (WHY-WHAT-HOW)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 당신의 상황
- [오픈 기간 요약]
- [예산 요약]
- [현재 마케팅 요약]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 해야 할 것 (우선순위)

1위. [채널명]

    WHY: [왜 이 채널을 해야 하는가]
    WHAT: [구체적으로 무엇을 할 것인가]
    HOW: [어떻게 할 것인가 - 시간/비용]
    
    이것도 귀찮다면:
    [강렬한 한 문장]

2위. [채널명]

    WHY: [이유]
    WHAT: [무엇을]
    HOW: [어떻게]
    
    주의:
    [경고/조언]

3위. [채널명]

    WHY: [이유]
    WHAT: [무엇을]
    
    하지만:
    [우선순위 조언]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 2주 액션 플랜

Day 1-3:
- [ ] [구체적 액션]

Day 4-7:
- [ ] [구체적 액션]

Day 8-14:
- [ ] [구체적 액션]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 예산 배분 (월 {monthly_budget})

1위 채널: [X만원] ([Y%])
2위 채널: [X만원] ([Y%])
3위 채널: [X만원] ([Y%])

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 중요 규칙 (반드시 지키기)

1. **현재 하고 있는 마케팅 (13번째 질문) 분석 우선**
   - 하고 있는 것의 문제점 지적
   - 개선 방향 명확히
   - "할 수 있냐" 질문으로 찌르기

2. **스티브 잡스 톤 엄수**
   - 짧은 문장 (10단어 이내)
   - 질문으로 찌르기
   - 이모지 제거
   - 본질을 꿰뚫기

3. **실행 가능성 우선**
   - 예산 0원 → 유료 광고 제외
   - 시간 없음 → 매일 관리 제외
   - 초보 → 복잡한 것 제외

4. **우선순위 3개만**
   - 최대 3개 채널
   - 80/20 법칙
   - Quick Win 우선

5. **한국 시장 최적화**
   - Naver Place 최우선
   - 배달앱 활용
   - K-food 트렌드
"""
    
    return user_prompt


def generate_full_prompt(
    answers: Dict[str, str],
    review_analysis: Dict[str, Any],
    store_name: str,
    current_marketing: List[str] = None,
    marketing_details: Dict[str, Dict[str, str]] = None
) -> tuple[str, str]:
    """
    전체 프롬프트 생성 (🔥 13번째 질문 포함)
    
    Returns:
        (system_prompt, user_prompt)
    """
    
    # 사장님 프로필 생성 (🔥 13번째 질문 포함)
    owner_profile_text = generate_owner_profile_text(
        answers, current_marketing, marketing_details
    )
    
    # 예산 텍스트
    budget_value = answers.get('budget', '0')
    budget_text = {
        '0': '0원 (무료)',
        '10-50': '10-50만원',
        '50-200': '50-200만원',
        '200+': '200만원 이상'
    }.get(budget_value, budget_value)
    
    # 사용자 프롬프트 생성
    user_prompt = generate_user_prompt(
        owner_profile_text,
        review_analysis,
        store_name,
        budget_text
    )
    
    # 🔥 스티브 잡스 톤 시스템 프롬프트 (35K 토큰 + 브랜드 철학)
    system_prompt_with_tone = MARKETING_REPORT_SYSTEM_PROMPT + BRAND_PHILOSOPHY
    
    return system_prompt_with_tone, user_prompt