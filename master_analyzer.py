# -*- coding: utf-8 -*-
# master_analyzer.py - 블로그 + DB + 경쟁사 통합 분석 시스템 (하이브리드 버전)

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

# 기존 모듈 임포트
from naver_blog_crawler import analyze_store_from_blog, StoreProfile
from mvp_analyzer import (
    crawl_store_info,
    extract_dong_from_address,
    get_reviews_from_db
)
from competitor_search import find_competitors_smart
from review_preprocessor import (
    generate_review_stats,
    compare_review_stats
)
# 🔥 하이브리드 엔진 임포트 (변경!)
from hybrid_insight_engine import generate_hybrid_report


# ==================== 체크리스트 생성 ====================

def generate_action_checklist(
    blog_profile: Optional[StoreProfile],
    insight_html: str,
    comparison_result: Dict
) -> str:
    """
    실행 가능한 체크리스트 생성
    """
    checklist = f"""
# ✅ 실행 체크리스트 (2주 러닝)

생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 🔥 최우선 과제 (이번 주 내)

"""
    
    # 1. 블로그 vs 실제 갭 분석
    if blog_profile:
        checklist += f"""### 📊 1. 블로그 vs 실제 리뷰 갭 분석

**블로그에서 발견된 컨셉**: {blog_profile.concept}
**주요 방문 목적 (블로그)**: {list(blog_profile.visit_purposes.keys())[:3]}

**실행 항목**:
- [ ] 블로그 컨셉이 실제 고객 경험과 일치하는지 확인
- [ ] 불일치 발견 시 → 마케팅 메시지 수정 또는 운영 개선
- [ ] 블로그 긍정 비율 {blog_profile.positive_ratio:.1%} vs 실제 리뷰 비교

💡 **Gap이 크면**: 블로그는 좋은데 실제는 아니거나, 실제는 좋은데 홍보가 부족

"""
    
    # 2. 통계 기반 약점 개선
    if comparison_result and '우리의_약점' in comparison_result:
        weaknesses = comparison_result['우리의_약점']
        if weaknesses:
            checklist += """### ⚠️ 2. 통계적으로 확인된 약점 (즉시 개선)

"""
            for topic, stats in list(weaknesses.items())[:3]:
                gap = stats['gap']
                checklist += f"""**{topic}**
- [ ] GAP: {gap:+.3f} (경쟁사보다 낮음)
- [ ] 우리: {stats['our']['rate']*100:.1f}% / 경쟁사: {stats['comp']['rate']*100:.1f}%
- [ ] 개선 목표: 경쟁사 수준({stats['comp']['rate']*100:.1f}%) 달성

"""
    
    # 3. 강점 마케팅
    if comparison_result and '우리의_강점' in comparison_result:
        strengths = comparison_result['우리의_강점']
        if strengths:
            checklist += """### ✨ 3. 강점 마케팅 활용

"""
            for topic, stats in list(strengths.items())[:2]:
                checklist += f"""**{topic}** (경쟁사보다 {stats['gap']*100:.1f}%p 우수)
- [ ] SNS에 "{topic}" 관련 콘텐츠 주 2회 이상 포스팅
- [ ] 네이버 톡채널/인스타 고정 프로필에 "{topic}" 강조
- [ ] 메뉴판/테이블에 "{topic}" 어필 문구 추가

"""
    
    # 7. 측정 KPI
    checklist += """---

## 📊 측정 KPI (2주 후 재측정)

### 리뷰 관련
- [ ] 네이버 플레이스 리뷰 수: 현재 ___개 → 목표 ___개
- [ ] 별점 평균: 현재 ___점 → 목표 ___점
- [ ] 긍정 키워드 언급률: 현재 ___% → 목표 ___%

### 마케팅 관련
- [ ] SNS 팔로워: 현재 ___명 → 목표 ___명
- [ ] 인스타 저장수: 주당 ___건 → 목표 ___건
- [ ] 네이버 톡채널 문의: 주당 ___건 → 목표 ___건

### 운영 관련
- [ ] 대기 시간: 평균 ___분 → 목표 ___분
- [ ] 재방문 고객 비율: ___% → 목표 ___%
- [ ] 객단가: ___원 → 목표 ___원

---

## 🎯 다음 스텝

1. **이번 주 (Day 1-7)**
   - 체크리스트 상위 5개 항목 실행
   - 일일 체크 및 기록

2. **다음 주 (Day 8-14)**
   - 남은 항목 실행
   - 고객 반응 관찰 및 조정

3. **2주 후**
   - 재분석 실행 (이 스크립트 다시 실행)
   - KPI 달성도 확인
   - 다음 2주 목표 수립

💡 **Tip**: 체크리스트를 프린트하여 주방/카운터에 붙이고, 매일 체크하세요!
"""
    
    return checklist


# ==================== 통합 리포트 생성 ====================

def generate_unified_report(
    store_name: str,
    blog_profile: Optional[StoreProfile],
    target_store: Dict,
    insight_html: str,
    checklist: str
) -> str:
    """
    최종 통합 리포트 생성
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║                  🏪 통합 분석 리포트                         ║
║                  {store_name}                                ║
╚══════════════════════════════════════════════════════════════╝

생성일시: {timestamp}

"""
    
    # Part 1: 블로그 분석 요약
    if blog_profile:
        report += f"""
{'='*60}
📱 Part 1: 블로그 분석 (온라인 평판)
{'='*60}

## 기본 정보
- 가게명: {blog_profile.name}
- 업종: {blog_profile.industry}
- 상권: {blog_profile.area}
- 컨셉: {blog_profile.concept}

## 온라인 이미지
- 분석된 블로그 수: {blog_profile.total_blog_posts}개
- 긍정 비율: {blog_profile.positive_ratio:.1%}
- 평균 평점: {blog_profile.avg_rating:.1f}/5.0

## 주요 고객층
{', '.join(blog_profile.target_customers)}

## 방문 목적 분포
"""
        for purpose, count in blog_profile.visit_purposes.items():
            report += f"- {purpose}: {count}회 언급\n"
        
        report += f"""
## 분위기 키워드
{', '.join(blog_profile.atmosphere_keywords[:5])}

## 상권 분석
- 유동인구: {blog_profile.foot_traffic}
- 경쟁 강도: {blog_profile.competition_level}
- 피크 시간: {', '.join(blog_profile.peak_times)}

💡 **블로그 분석 시사점**:
블로그는 "{blog_profile.concept}" 컨셉으로 인식되고 있습니다.
실제 리뷰와 비교하여 갭이 있는지 확인하세요!

"""
    else:
        report += """
{'='*60}
⚠️  Part 1: 블로그 분석 실패
{'='*60}

블로그 데이터가 부족하거나 API 연동 오류입니다.
네이버 블로그 API 키를 확인하세요.

"""
    
    # Part 2: HTML 리포트 링크
    report += f"""
{'='*60}
⭐ Part 2: 시각화 리포트 (HTML)
{'='*60}

HTML 리포트가 생성되었습니다.
브라우저로 열어서 차트를 확인하세요!

📊 장점/단점 파이 차트
🏆 경쟁사 비교
✅ 2주 체크리스트

"""
    
    # Part 3: 체크리스트
    report += f"""
{'='*60}
✅ Part 3: 실행 체크리스트
{'='*60}

{checklist}

"""
    
    # 최종 요약
    report += f"""
{'='*60}
🎯 최종 요약
{'='*60}

이 리포트는 3가지 데이터 소스를 종합한 결과입니다:
1. 📱 **블로그 분석**: 온라인에서 어떻게 인식되는가?
2. ⭐ **플레이스 리뷰**: 실제 고객 경험은 어떠한가?
3. 🏪 **경쟁사 비교**: 우리의 위치는 어디인가?

**핵심 메시지**:
- 블로그 이미지와 실제 경험의 **갭**을 좁히세요
- 통계적으로 확인된 **약점**을 우선 개선하세요
- 경쟁사보다 강한 부분을 **마케팅**에 활용하세요
- **2주 단위**로 실행하고 측정하세요

📞 **문의**: 이 리포트는 자동 생성되었습니다. 
           구체적인 컨설팅이 필요하면 전문가와 상담하세요.

{'='*60}
"""
    
    return report


# ==================== 메인 실행 함수 ====================

async def run_master_analysis(store_name: str, address: str):
    """
    통합 분석 실행 (블로그 + 플레이스 + 경쟁사 + 하이브리드 AI)
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║         🚀 통합 분석 시스템 v2.0 (하이브리드)                ║
║         블로그 + 플레이스 + 경쟁사 + GPT + Claude           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"\n📋 분석 대상:")
    print(f"   가게명: {store_name}")
    print(f"   주소: {address}")
    
    # ==================== STEP 1: 블로그 분석 ====================
    
    print(f"\n{'='*60}")
    print("📱 STEP 1: 네이버 블로그 분석 (200개)")
    print(f"{'='*60}")
    
    blog_profile = None
    try:
        blog_profile = analyze_store_from_blog(store_name)
    except Exception as e:
        print(f"⚠️  블로그 분석 실패: {e}")
        print("   (계속 진행합니다...)")
    
    # ==================== STEP 2: 플레이스 크롤링 ====================
    
    print(f"\n{'='*60}")
    print("⭐ STEP 2: 네이버 플레이스 크롤링 (200개)")
    print(f"{'='*60}")
    
    region_extracted = extract_dong_from_address(address)
    print(f"   추출된 지역: {region_extracted}")
    
    store_data = await crawl_store_info(store_name, region_hint=region_extracted)
    
    if not store_data:
        print("\n❌ 플레이스 크롤링 실패")
        return
    
    target_store = {
        'place_id': store_data['place_id'],
        'name': store_data['name'],
        'district': region_extracted,
        'industry': store_data['industry']
    }
    
    target_reviews = store_data['reviews']
    
    if not target_reviews:
        print("\n⚠️  리뷰 없음")
        return
    
    # 리뷰 형식 통일
    unified_reviews = []
    for r in target_reviews:
        unified_reviews.append({
            'date': r.get('날짜', '날짜없음'),
            'content': r.get('리뷰', '')
        })
    
    # ==================== STEP 3: 경쟁사 검색 ====================
    
    print(f"\n{'='*60}")
    print("🏪 STEP 3: 경쟁사 검색 (DB)")
    print(f"{'='*60}")
    
    # 전략 선택 (균형 기본값)
    beta, alpha = 1.8, 0.9
    strategy_name = "균형"
    
    competitors = find_competitors_smart(
        db_path='seoul_industry_reviews.db',
        user_area=region_extracted,
        user_industry=store_data['industry'],
        limit=5,
        beta=beta,
        alpha=alpha
    )
    
    competitor_reviews = {}
    if competitors:
        print(f"\n   경쟁사 리뷰 로딩...")
        for comp in competitors:
            reviews = get_reviews_from_db(comp.place_id)
            competitor_reviews[comp.place_id] = reviews
            print(f"   ✅ {comp.name}: {len(reviews)}개")
    
    # ==================== STEP 4: 통계 분석 ====================
    
    print(f"\n{'='*60}")
    print("📊 STEP 4: 통계 분석 및 비교")
    print(f"{'='*60}")
    
    our_stats = generate_review_stats(unified_reviews, target_store['name'])
    print(f"   ✅ 우리 가게 통계 생성 완료")
    
    comp_stats_list = []
    if competitors:
        for comp in competitors:
            comp_revs = competitor_reviews.get(comp.place_id, [])
            if comp_revs:
                comp_stat = generate_review_stats(comp_revs, comp.name)
                comp_stats_list.append(comp_stat)
        print(f"   ✅ 경쟁사 통계 생성 완료")
    
    comparison_result = None
    if comp_stats_list:
        comparison_result = compare_review_stats(our_stats, comp_stats_list)
        print(f"   ✅ 통계 비교 완료")
    
    # ==================== STEP 5: 하이브리드 인사이트 (GPT + Claude) ====================
    
    print(f"\n{'='*60}")
    print("🤖 STEP 5: 하이브리드 AI 인사이트 (GPT + Claude)")
    print(f"{'='*60}")
    
    # 🔥 async 함수 직접 호출!
    insight_html = await generate_hybrid_report(
        target_store=target_store,
        target_reviews=unified_reviews,
        competitors=competitors,
        competitor_reviews=competitor_reviews,
        statistical_comparison=comparison_result
    )
    
    # ==================== STEP 6: 체크리스트 생성 ====================
    
    print(f"\n{'='*60}")
    print("✅ STEP 6: 실행 체크리스트 생성")
    print(f"{'='*60}")
    
    checklist = generate_action_checklist(
        blog_profile=blog_profile,
        insight_html=insight_html,
        comparison_result=comparison_result
    )
    
    # ==================== STEP 7: 통합 리포트 ====================
    
    print(f"\n{'='*60}")
    print("📄 STEP 7: 통합 리포트 생성")
    print(f"{'='*60}")
    
    unified_report = generate_unified_report(
        store_name=store_name,
        blog_profile=blog_profile,
        target_store=target_store,
        insight_html=insight_html,
        checklist=checklist
    )
    
    # 출력
    print("\n" + "="*60)
    print(unified_report)
    print("="*60)
    
    # 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"unified_report_{target_store['name'].replace(' ', '_')}_{timestamp}.md"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(unified_report)
        print(f"\n💾 리포트 저장: {filename}")
    except Exception as e:
        print(f"⚠️  파일 저장 실패: {e}")
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  ✅ 분석 완료!                               ║
║                  📊 HTML 파일을 브라우저로 여세요!           ║
╚══════════════════════════════════════════════════════════════╝
    """)


# ==================== CLI 실행 ====================

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         🏪 맛집 통합 분석 시스템 v2.0                        ║
║         블로그 200개 + 리뷰 200개 + GPT + Claude            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 사용자 입력
    store_name = input("\n가게 이름을 입력하세요: ").strip()
    if not store_name:
        print("❌ 가게 이름이 없습니다.")
        return
    
    address = input("주소를 입력하세요 (예: 강남역, 성수동, 홍대): ").strip()
    if not address:
        print("❌ 주소가 없습니다.")
        return
    
    # 실행
    await run_master_analysis(store_name, address)


if __name__ == "__main__":
    asyncio.run(main())