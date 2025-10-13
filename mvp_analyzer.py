# -*- coding: utf-8 -*-
# mvp_analyzer.py - 실시간 크롤링 (블랙리스트만 + 첫번째 선택)

import asyncio
import sqlite3
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

from hybrid_insight_engine import generate_hybrid_report  # 🔥 변경됨
from review_preprocessor import (
    generate_review_stats,
    compare_review_stats,
    format_comparison_for_gpt
)
from competitor_search import find_competitors_smart, normalize_area

DB_FILE = 'seoul_industry_reviews.db'
TARGET_REVIEWS = 150
SCROLL_DEPTH = 20
MONTHS_FILTER = 12


# ==================== 블랙리스트 ====================

STORE_NAME_BLACKLIST = [
    "이미지수",
    "이미지",
    "사진",
    "메뉴",
    "리뷰",
    "더보기",
    "상세보기",
    "정보",
    "안내",
    "광고",
]


def is_blacklisted(store_name):
    """블랙리스트 체크"""
    if not store_name:
        return True
    
    name_lower = store_name.lower().strip()
    
    for blacklist_item in STORE_NAME_BLACKLIST:
        if name_lower == blacklist_item.lower():
            return True
        if len(blacklist_item) >= 3 and blacklist_item.lower() in name_lower:
            return True
    
    return False


async def select_best_store(store_items, user_input, debug=True):
    """
    가게 목록에서 최적의 가게 선택 (간소화 버전)
    
    블랙리스트 제거 후 첫 번째 가게 선택
    """
    if not store_items:
        return None, None
    
    if debug:
        print(f"\n   🔍 가게 선택 중... (블랙리스트 필터링)")
    
    for idx, item in enumerate(store_items[:10], 1):
        try:
            text = await item.inner_text(timeout=500)
            if not text or not text.strip():
                continue
            
            lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
            if not lines:
                continue
            
            store_name = lines[0]
            
            # 블랙리스트 체크
            if is_blacklisted(store_name):
                if debug:
                    print(f"      [{idx}] ❌ 블랙리스트: {store_name}")
                continue
            
            # 🔥 첫 번째 유효한 가게 선택!
            if debug:
                print(f"      [{idx}] ✅ 선택: {store_name}")
            
            return item, store_name
        
        except Exception as e:
            if debug:
                print(f"      [{idx}] ⚠️  파싱 실패: {e}")
            continue
    
    # 모든 가게가 블랙리스트면 None
    if debug:
        print(f"      ❌ 유효한 가게를 찾지 못했습니다")
    
    return None, None


# ==================== 업종 추출 (개선) ====================

def extract_category_from_text(text, store_name):
    """
    텍스트에서 업종 추출 (강화 버전)
    
    전략:
    1. 가게명에서 직접 추출 (최우선!)
    2. 확장된 키워드 매칭
    3. 폴백: "음식점"
    """
    if not text:
        return "음식점"
    
    # 🔥 전략 1: 가게명에서 직접 추출 (최우선!)
    if store_name:
        # 키워드 우선순위: 구체적 → 일반 순
        # "요리주점"을 그대로 유지! (정제하지 않음)
        for keyword in ['요리주점', '오마카세', '스시', '이자카야', '라멘', 
                       '돈카츠', '샤브샤브', '뷔페', '베이커리', 
                       '주점', '술집', '카페', '음식점', '식당', 
                       '일식', '양식', '중식', '한식', '치킨', '피자']:
            if keyword in store_name:
                # "요리"로 끝나는 경우만 정제 (예: "육류요리" → "육류")
                if keyword.endswith('요리') and keyword != '요리주점':
                    return keyword[:-2]
                return keyword  # 요리주점은 그대로 반환!
    
    # 가게명 제거 (전략 2를 위해)
    text_clean = text.replace(store_name, '') if store_name else text
    
    # 🔥 확장된 업종 키워드 (우선순위 순)
    industry_keywords = [
        # 구체적 카테고리 우선
        '요리주점', '오마카세', '스시', '이자카야', '라멘', '우동', '돈카츠',
        '파스타', '이탈리안', '스테이크', '피자',
        '디저트카페', '브런치카페', '베이커리',
        '와인바', '칵테일바', '펍',
        '아귀찜', '해물찜', '갈비', '삼겹살', '곱창', '육류',
        '마라탕', '딤섬', '쌀국수',
        '샤브샤브', '뷔페',
        # 일반 카테고리
        '주점', '술집', '카페', '일식', '양식', '중식', '한식',
    ]
    
    # 키워드 매칭
    for keyword in industry_keywords:
        if keyword in text_clean:
            # "요리"로 끝나는 경우만 정제
            if keyword.endswith('요리') and keyword != '요리주점':
                return keyword[:-2]
            return keyword
    
    # 못 찾으면 폴백
    return "음식점"


async def extract_category_from_page(page, store_name):
    """
    페이지에서 업종 추출 (3단계 전략)
    """
    try:
        # 🔥 최우선: 가게명에서 직접 추출
        print(f"   🔍 업종 추출 시도: 가게명='{store_name}'")
        
        if store_name:
            result = extract_category_from_text(store_name, store_name)
            if result != "음식점":
                print(f"   ✅ 가게명에서 추출: {result}")
                return result
        
        # 🔥 전략 1: span.lnJFt CSS 셀렉터
        try:
            category_element = await page.locator('span.lnJFt').first
            if category_element:
                text = await category_element.inner_text(timeout=2000)
                if text and text != store_name:
                    result = extract_category_from_text(text, store_name)
                    if result != "음식점":
                        print(f"   ✅ CSS 셀렉터에서 추출: {result}")
                        return result
        except:
            pass
        
        # 🔥 전략 2: 텍스트 패턴 "{가게명}{카테고리}"
        try:
            body_text = await page.inner_text('body', timeout=3000)
            lines = [ln.strip() for ln in body_text.split('\n') if ln.strip()]
            
            for line in lines[:20]:
                if store_name in line:
                    remainder = line.replace(store_name, '').strip()
                    if remainder and len(remainder) < 30:
                        result = extract_category_from_text(remainder, store_name)
                        if result != "음식점":
                            print(f"   ✅ 텍스트 패턴에서 추출: {result} (from: '{line[:50]}...')")
                            return result
        except:
            pass
        
        # 🔥 전략 3: 페이지 전체 텍스트 검색
        try:
            body_text = await page.inner_text('body', timeout=3000)
            result = extract_category_from_text(body_text[:2000], store_name)
            print(f"   ⚠️  페이지 전체 검색: {result}")
            return result
        except:
            pass
        
        print(f"   ⚠️  업종 추출 실패, 기본값 사용: 음식점")
        return "음식점"
        
    except:
        print(f"   ❌ 업종 추출 오류, 기본값 사용: 음식점")
        return "음식점"


# ==================== 주소 파싱 ====================

def extract_dong_from_address(address):
    """
    주소에서 동 단위 추출 (개선)
    
    "성수", "강남역", "홍대" 같은 짧은 입력도 처리
    """
    if not address:
        return None
    
    # 1. 역명/지역명 매핑 활용 (STATION_TO_AREA)
    normalized = normalize_area(address)
    if normalized and normalized != address:
        return normalized
    
    # 2. 정규식 패턴 매칭
    # "OO구 OO동" 패턴
    gu_dong_match = re.search(r'[가-힣]+구\s+([가-힣]+동)', address)
    if gu_dong_match:
        return gu_dong_match.group(1)
    
    # "OO동" 패턴
    dong_match = re.search(r'([가-힣]+동)(?![가-힣])', address)
    if dong_match:
        return dong_match.group(1)
    
    # "OO구" 패턴
    gu_match = re.search(r'([가-힣]+구)', address)
    if gu_match:
        return gu_match.group(1)
    
    # 3. "동" 붙여서 재시도 (성수 → 성수동)
    if not address.endswith('동') and not address.endswith('구') and not address.endswith('역'):
        candidate = address + '동'
        normalized = normalize_area(candidate)
        if normalized and normalized != candidate:
            return normalized
    
    # 4. 못 찾으면 원본 반환 (에러 대신)
    return address


# ==================== 크롤링 헬퍼 ====================

def is_owner_reply(review_text):
    """사장님 답글 필터링"""
    if not review_text:
        return False
    strong_signals = ['리뷰 감사', '진심으로 감사', '찾아주셔서', '보답하겠습니다']
    return any(s in review_text for s in strong_signals) or \
           sum(1 for k in ['감사드립니다', '감사합니다'] if k in review_text) >= 2


async def expand_reviews(page):
    """'펼쳐서 더보기' 버튼 클릭"""
    try:
        await page.evaluate("""
            () => {
                document.querySelectorAll('button, a').forEach(btn => {
                    if (btn.textContent.includes('펼쳐서 더보기')) {
                        try { btn.click(); } catch(e) {}
                    }
                });
            }
        """)
    except:
        pass


# ==================== 실시간 크롤링 ====================

async def crawl_store_info(store_name, region_hint=None):
    """네이버 플레이스 크롤링 (블랙리스트 + 첫번째 선택)"""
    print(f"\n{'='*60}")
    print(f"🔍 STEP 1: '{store_name}' 실시간 크롤링")
    print(f"{'='*60}")
    
    if region_hint:
        print(f"   💡 사용자 입력 지역: {region_hint}")
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR"
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = await context.new_page()
        
        try:
            # 1. 네이버 지도 검색
            search_url = f"https://map.naver.com/v5/search/{store_name}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # 2. 검색 프레임 찾기
            search_frame = None
            for attempt in range(15):
                for frame in page.frames:
                    if "searchIframe" in frame.name or "entry=plt" in frame.url:
                        search_frame = frame
                        break
                if search_frame:
                    break
                await asyncio.sleep(1)
            
            if not search_frame:
                print("   ❌ 검색 결과를 찾을 수 없습니다.")
                await context.close()
                await browser.close()
                return None
            
            await asyncio.sleep(3)
            
            # 3. 검색 결과 수집
            store_items = []
            
            selectors = [
                "li.UEzoS",
                "li.CHC5F",
                "li[data-id]",
                "li.Efc51",
                "li.tzwk0",
                "div.place_bluelink",
                "a[class*='place']",
            ]
            
            for sel in selectors:
                try:
                    items = await search_frame.locator(sel).all()
                    if not items:
                        continue
                    
                    print(f"   🔍 셀렉터 '{sel}': {len(items)}개 발견")
                    
                    valid_items = []
                    for item in items[:10]:
                        try:
                            text = await item.inner_text(timeout=500)
                            if text and text.strip():
                                valid_items.append(item)
                        except:
                            pass
                    
                    if len(valid_items) >= 1:
                        store_items = valid_items
                        print(f"   ✅ {len(valid_items)}개 유효 항목 발견")
                        break
                except Exception as e:
                    print(f"   ⚠️  셀렉터 '{sel}' 실패: {e}")
                    pass
            
            if not store_items:
                print("   ❌ 가게를 찾을 수 없습니다.")
                await context.close()
                await browser.close()
                return None
            
            # 🔥 블랙리스트 필터 + 첫 번째 선택
            best_store, store_name_found = await select_best_store(
                store_items, 
                store_name,
                debug=True
            )
            
            if not best_store:
                print("   ❌ 적합한 가게를 찾을 수 없습니다.")
                await context.close()
                await browser.close()
                return None
            
            await asyncio.sleep(1)
            await best_store.click(timeout=3000)
            await asyncio.sleep(3)
            
            # 4. place_id 추출
            place_id = None
            for frame in page.frames:
                match = re.search(r'place[/=](\d+)', frame.url)
                if match:
                    place_id = match.group(1)
                    break
            
            if not place_id:
                print("   ❌ place_id를 찾을 수 없습니다.")
                await context.close()
                await browser.close()
                return None
            
            print(f"\n   ✅ 가게명: {store_name} (사용자 입력)")
            print(f"   ✅ 크롤링 가게명: {store_name_found}")
            print(f"   ✅ Place ID: {place_id}")
            
            # 5. 상세 페이지로 이동
            detail_url = f"https://m.place.naver.com/restaurant/{place_id}/home"
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 지역 추출
            if region_hint:
                region = region_hint
                print(f"   ✅ 지역: {region} (사용자 입력)")
            else:
                region = "알 수 없음"
                try:
                    page_text = await page.inner_text("body", timeout=3000)
                    dong_match = re.search(r'서울특?별?시?\s+[가-힣]+구\s+([가-힣]+동)', page_text)
                    if dong_match:
                        region = dong_match.group(1)
                    else:
                        gu_match = re.search(r'서울특?별?시?\s+([가-힣]+구)', page_text)
                        if gu_match:
                            region = gu_match.group(1)
                    print(f"   ✅ 지역: {region} (크롤링 추출)")
                except:
                    print(f"   ⚠️  지역: {region}")
            
            # 🔥 업종 추출 (개선!)
            industry = await extract_category_from_page(page, store_name_found)
            print(f"   ✅ 업종: {industry}")
            
            # 6. 리뷰 페이지로 이동
            print(f"\n{'='*60}")
            print(f"📥 STEP 2: 리뷰 수집 (목표: {TARGET_REVIEWS}개)")
            print(f"{'='*60}")
            
            review_url = f"https://m.place.naver.com/restaurant/{place_id}/review/visitor"
            await page.goto(review_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 최신순 정렬
            print("   🔄 최신순 정렬 중...")
            try:
                for selector in ["button:has-text('최신순')", "a:has-text('최신순')"]:
                    try:
                        await page.click(selector, timeout=3000)
                        print("   ✅ 최신순 정렬 완료")
                        await asyncio.sleep(2)
                        break
                    except:
                        continue
            except:
                print("   ⚠️  최신순 버튼을 찾지 못했습니다.")
            
            # 7. 스크롤 & 리뷰 수집
            print("   ⏬ 스크롤 중...")
            for i in range(30):
                try:
                    await page.evaluate("window.scrollBy(0, 2000)")
                except:
                    pass
                await asyncio.sleep(0.3)
                await expand_reviews(page)
                
                if i % 10 == 0:
                    count = 0
                    for sel in ["li.place_apply_pui", "li.pui__X35jYm"]:
                        try:
                            count = await page.locator(sel).count()
                            if count >= TARGET_REVIEWS:
                                print(f"   ✅ {count}개 발견, 수집 중단")
                                break
                        except:
                            pass
                    if count >= TARGET_REVIEWS:
                        break
            
            # 8. 리뷰 파싱
            reviews = []
            review_items = []
            for sel in ["li.place_apply_pui", "li.pui__X35jYm", "li.EjjAW"]:
                try:
                    items = await page.locator(sel).all()
                    if items:
                        review_items = items
                        break
                except:
                    pass
            
            print(f"   📝 파싱 중... (발견: {len(review_items)}개)")
            
            for item in review_items[:TARGET_REVIEWS + 20]:
                try:
                    full_text = await item.inner_text(timeout=500)
                    if len(full_text) < 50:
                        continue
                    
                    review = {"별점": None, "날짜": None, "리뷰": ""}
                    
                    if '★' in full_text:
                        review["별점"] = float(min(full_text.count('★'), 5))
                    
                    date_patterns = [
                        r'(\d{4}[./-]\d{1,2}[./-]\d{1,2})',
                        r'(\d{1,2}[./-]\d{1,2})',
                        r'(\d+일\s*전)',
                    ]
                    
                    for pattern in date_patterns:
                        date_match = re.search(pattern, full_text)
                        if date_match:
                            review["날짜"] = date_match.group(1)
                            break
                    
                    lines = [ln.strip() for ln in full_text.split('\n') if len(ln.strip()) >= 20]
                    if lines:
                        review["리뷰"] = max(lines, key=len)
                    
                    if review["리뷰"] and not is_owner_reply(review["리뷰"]):
                        reviews.append(review)
                    
                    if len(reviews) >= TARGET_REVIEWS:
                        break
                        
                except:
                    pass
            
            print(f"   ✅ 수집된 리뷰: {len(reviews)}개")
            
            await context.close()
            await browser.close()
            
            return {
                'place_id': place_id,
                'name': store_name,
                'district': region,
                'industry': industry,
                'reviews': reviews
            }
            
        except Exception as e:
            print(f"   ❌ 크롤링 실패: {e}")
            await context.close()
            await browser.close()
            return None


# ==================== DB 관련 ====================

def parse_review_date(date_str):
    """날짜 문자열을 datetime 객체로 변환"""
    if not date_str:
        return None
    
    try:
        date_str = date_str.replace('/', '.').replace('-', '.')
        parts = date_str.split('.')
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return datetime(year, month, day)
    except:
        pass
    
    return None


def is_recent_review(date_str, months=6):
    """최근 N개월 이내 리뷰인지 확인"""
    review_date = parse_review_date(date_str)
    if not review_date:
        return True
    
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    return review_date >= cutoff_date


def get_reviews_from_db(place_id, filter_recent=True):
    """DB에서 리뷰 가져오기"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT date, content FROM reviews WHERE place_id = ?", (place_id,))
    all_reviews = cursor.fetchall()
    conn.close()
    
    reviews = []
    for date_str, content in all_reviews:
        if not content or not content.strip():
            continue
        
        if filter_recent:
            if is_recent_review(date_str, MONTHS_FILTER):
                reviews.append({'date': date_str if date_str else '날짜없음', 
                              'content': content.strip()})
        else:
            reviews.append({'date': date_str if date_str else '날짜없음', 
                          'content': content.strip()})
    
    return reviews


# ==================== 메인 ====================

async def main():
    print("""
╔══════════════════════════════════════════════════════╗
║   🏪 맛집 실시간 분석 시스템                         ║
╚══════════════════════════════════════════════════════╝
""")
    
    store_input = input("\n가게 이름을 입력하세요: ").strip()
    if not store_input:
        print("❌ 가게 이름이 없습니다.")
        return
    
    address_input = input("주소를 입력하세요 (예: 강남역, 성수동, 성수, 홍대): ").strip()
    if not address_input:
        print("❌ 주소가 없습니다.")
        return
    
    region_extracted = extract_dong_from_address(address_input)
    
    print(f"\n✅ 추출된 지역: {region_extracted}")
    
    # 🔥 블로그 분석 선택 추가
    blog_profile = None  # 기본값
    do_blog = input("\n블로그 분석도 하시겠습니까? (y/N, 20초 소요): ").strip().lower()
    
    if do_blog == 'y':
        try:
            from naver_blog_crawler import analyze_store_from_blog
            print(f"\n{'='*60}")
            print(f"📱 블로그 분석 중...")
            print(f"{'='*60}")
            blog_profile = analyze_store_from_blog(store_input)
            print(f"   ✅ 블로그 {blog_profile.total_blog_posts}개 분석 완료")
            print(f"   긍정 비율: {blog_profile.positive_ratio:.1%}")
        except Exception as e:
            print(f"   ⚠️ 블로그 분석 실패 (스킵): {e}")
    else:
        print(f"   ⏭️  블로그 분석 스킵")
    
    # 🎯 경쟁사 검색 전략 선택
    print(f"\n{'='*60}")
    print(f"🎯 경쟁사 검색 전략 선택")
    print(f"{'='*60}")
    print("\n어떤 기준으로 경쟁사를 찾을까요?\n")
    print("1️⃣  업종 우선 (같은 업종, 지역 무관)")
    print("    💡 추천: 특화 메뉴가 있거나, 지역보다 업종이 중요한 경우")
    print("    예: 서울 전역의 아귀찜/해물찜 가게")
    print("    β=2.5 (업종 강조), α=0.5 (지역 약화)")
    print()
    print("2️⃣  지역 우선 (같은 지역, 업종 다양)")
    print("    💡 추천: 지역 상권이 중요하거나, 업종보다 위치가 중요한 경우")
    print("    예: 방이동/송파권의 한식/중식/일식 등")
    print("    β=1.0 (업종 약화), α=1.5 (지역 강조)")
    print()
    print("3️⃣  균형 (업종과 지역 모두 고려) ⭐ 추천")
    print("    💡 추천: 대부분의 경우 (가장 무난)")
    print("    예: 송파권의 찜/탕 요리, 서울 전역의 아귀찜")
    print("    β=1.8 (업종 중시), α=0.9 (지역 보통)")
    print()
    
    while True:
        strategy = input("선택하세요 (1/2/3, 기본값=3): ").strip()
        if strategy == '':
            strategy = '3'
        if strategy == '1':
            beta, alpha = 2.5, 0.5
            strategy_name = "업종 우선"
            break
        elif strategy == '2':
            beta, alpha = 1.0, 1.5
            strategy_name = "지역 우선"
            break
        elif strategy == '3':
            beta, alpha = 1.8, 0.9
            strategy_name = "균형"
            break
        else:
            print("❌ 1, 2, 3 중 하나를 선택하세요.")
    
    print(f"\n✅ 선택된 전략: {strategy_name} (β={beta}, α={alpha})")
    
    store_data = await crawl_store_info(store_input, region_hint=region_extracted)
    
    if not store_data:
        print("\n❌ 크롤링 실패")
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
    
    print(f"\n{'='*60}")
    print(f"🏪 STEP 3: DB에서 경쟁사 검색")
    print(f"{'='*60}")
    
    competitors = find_competitors_smart(
        db_path=DB_FILE,
        user_area=region_extracted,
        user_industry=store_data['industry'],
        limit=5,
        beta=beta,
        alpha=alpha
    )
    
    competitor_reviews = {}
    if competitors:
        print(f"\n{'='*60}")
        print(f"📥 STEP 3-2: 경쟁사 리뷰 로드")
        print(f"{'='*60}")
        for comp in competitors:
            reviews = get_reviews_from_db(comp.place_id)
            competitor_reviews[comp.place_id] = reviews
            print(f"   ✅ {comp.name}: {len(reviews)}개")
    
    unified_reviews = []
    for r in target_reviews:
        unified_reviews.append({
            'date': r.get('날짜', '날짜없음'),
            'content': r.get('리뷰', ''),
            'rating': r.get('별점', 0)  # 🔥 rating 필드 추가
        })
    
    print(f"\n{'='*60}")
    print(f"📊 STEP 4: 통계 분석")
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
    
    # 🔥 올인원 HTML 리포트 생성
    from all_in_one_html import generate_all_in_one_report
    
    report = await generate_all_in_one_report(
        target_store=target_store,
        target_reviews=unified_reviews,
        blog_profile=blog_profile,  # ✅ 이제 정의됨!
        competitors=competitors,
        competitor_reviews=competitor_reviews,
        statistical_comparison=comparison_result
    )
    
    if report:
        print("\n" + "="*60)
        print("✅ 올인원 HTML 리포트 생성 완료!")
        print(f"💡 브라우저로 열어서 확인하세요!")
        print("="*60)
    else:
        print("\n❌ 리포트 생성 실패")
    
    print("""
╔══════════════════════════════════════════════════════╗
║   ✅ 분석 완료!                                      ║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    asyncio.run(main())