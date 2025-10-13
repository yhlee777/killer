# -*- coding: utf-8 -*-
# fix_imagsu_auto.py - 자동 업데이트 (승인 없음)

import asyncio
import sqlite3
from playwright.async_api import async_playwright

DB_FILE = 'seoul_industry_reviews.db'

BLACKLIST = [
    "이미지수", "이미지", "사진", "메뉴", "리뷰", "더보기",
    "이전 페이지", "다음 페이지", "목록", "검색"
]

def is_blacklisted(name):
    if not name or len(name) < 2:
        return True
    return name.strip().lower() in [b.lower() for b in BLACKLIST]


def find_imagsu_stores():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT place_id, name, district, industry, review_count
        FROM stores
        WHERE name = '이미지수' OR name LIKE '%이미지수%'
        ORDER BY review_count DESC
    """)
    
    stores = [
        {
            'place_id': row[0],
            'name': row[1],
            'district': row[2],
            'industry': row[3],
            'review_count': row[4]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return stores


async def extract_store_info(page, place_id):
    """가게명과 업종 추출 (조용히)"""
    store_name = None
    industry = None
    
    # 방법 1: span.GHAhO + span.lnJFt
    try:
        name_locator = page.locator('span.GHAhO').first
        store_name = await name_locator.inner_text(timeout=3000)
        store_name = store_name.strip()
    except:
        pass
    
    try:
        industry_locator = page.locator('span.lnJFt').first
        industry = await industry_locator.inner_text(timeout=3000)
        industry = industry.strip()
    except:
        pass
    
    # 방법 2: iframe
    if not store_name or is_blacklisted(store_name):
        try:
            for frame in page.frames:
                if "place" in frame.url or "entry" in frame.url:
                    try:
                        name_locator = frame.locator('span.GHAhO').first
                        candidate = await name_locator.inner_text(timeout=2000)
                        candidate = candidate.strip()
                        if candidate and not is_blacklisted(candidate):
                            store_name = candidate
                    except:
                        pass
                    
                    try:
                        industry_locator = frame.locator('span.lnJFt').first
                        industry = await industry_locator.inner_text(timeout=2000)
                        industry = industry.strip()
                    except:
                        pass
                    
                    if store_name and not is_blacklisted(store_name):
                        break
        except:
            pass
    
    # 방법 3: Meta 태그
    if not store_name or is_blacklisted(store_name):
        try:
            meta_locator = page.locator('meta[property="og:title"]').first
            content = await meta_locator.get_attribute('content', timeout=2000)
            if content:
                for sep in [':', '-', '|']:
                    if sep in content:
                        candidate = content.split(sep)[0].strip()
                        candidate = candidate.replace('네이버', '').replace('플레이스', '').strip()
                        
                        if candidate and not is_blacklisted(candidate):
                            store_name = candidate
                            break
        except:
            pass
    
    # 방법 4: title
    if not store_name or is_blacklisted(store_name):
        try:
            title = await page.title()
            for sep in [':', '-', '|', '·']:
                if sep in title:
                    candidate = title.split(sep)[0].strip()
                    candidate = candidate.replace('네이버', '').replace('플레이스', '').strip()
                    
                    if candidate and not is_blacklisted(candidate):
                        store_name = candidate
                        break
        except:
            pass
    
    # 방법 5: 대체 셀렉터
    if not store_name or is_blacklisted(store_name):
        alternative_selectors = ['h1.Fc1rA', 'h1', '.place_section_header']
        
        for sel in alternative_selectors:
            try:
                locator = page.locator(sel).first
                candidate = await locator.inner_text(timeout=1000)
                candidate = candidate.strip()
                
                if candidate and not is_blacklisted(candidate):
                    store_name = candidate
                    break
            except:
                continue
    
    if store_name and is_blacklisted(store_name):
        return None, None
    
    return store_name, industry


async def crawl_store_info(place_id):
    """크롤링 (조용히)"""
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
            url = f"https://m.place.naver.com/restaurant/{place_id}/home"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            store_name, industry = await extract_store_info(page, place_id)
            
            await context.close()
            await browser.close()
            
            return store_name, industry
            
        except:
            await context.close()
            await browser.close()
            return None, None


def update_store_in_db(place_id, new_name, new_industry=None):
    """DB 업데이트"""
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cursor = conn.cursor()
        
        if new_industry:
            cursor.execute("""
                UPDATE stores 
                SET name = ?, industry = ? 
                WHERE place_id = ?
            """, (new_name, new_industry, place_id))
        else:
            cursor.execute("""
                UPDATE stores 
                SET name = ? 
                WHERE place_id = ?
            """, (new_name, place_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
        
    except:
        return False


async def main():
    print("""
╔══════════════════════════════════════════════════════╗
║   🔧 '이미지수' 자동 업데이트                        ║
╚══════════════════════════════════════════════════════╝
""")
    
    # STEP 1: 검색
    stores = find_imagsu_stores()
    
    if not stores:
        print("✅ '이미지수' 가게가 없습니다!")
        return
    
    print(f"\n📊 발견: {len(stores)}개")
    
    confirm = input(f"\n💡 {len(stores)}개 가게를 자동 업데이트하시겠습니까? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ 취소")
        return
    
    # STEP 2: 자동 업데이트
    print(f"\n{'='*60}")
    print("🚀 자동 업데이트 진행 중...")
    print(f"{'='*60}\n")
    
    success = 0
    fail = 0
    changes = []
    
    for i, store in enumerate(stores, 1):
        print(f"[{i}/{len(stores)}] {store['place_id']} 처리 중...", end=" ")
        
        new_name, new_industry = await crawl_store_info(store['place_id'])
        
        if new_name and not is_blacklisted(new_name):
            if update_store_in_db(store['place_id'], new_name, new_industry):
                print(f"✅")
                success += 1
                changes.append({
                    'place_id': store['place_id'],
                    'old_name': store['name'],
                    'new_name': new_name,
                    'old_industry': store['industry'],
                    'new_industry': new_industry,
                    'district': store['district']
                })
            else:
                print(f"❌ (DB 실패)")
                fail += 1
        else:
            print(f"❌ (추출 실패)")
            fail += 1
        
        if i < len(stores):
            await asyncio.sleep(2)
    
    # STEP 3: 결과 출력
    print(f"\n{'='*60}")
    print("📊 최종 결과")
    print(f"{'='*60}")
    print(f"✅ 성공: {success}개")
    print(f"❌ 실패: {fail}개")
    print(f"📊 전체: {len(stores)}개")
    
    if changes:
        print(f"\n{'='*60}")
        print("📝 변경 내역 ({0}개)".format(len(changes)))
        print(f"{'='*60}\n")
        
        for i, change in enumerate(changes, 1):
            print(f"[{i}] place_id: {change['place_id']}")
            print(f"    지역: {change['district']}")
            print(f"    이름: {change['old_name']} → {change['new_name']}")
            
            if change['new_industry'] and change['new_industry'] != change['old_industry']:
                print(f"    업종: {change['old_industry']} → {change['new_industry']}")
            
            print()
    
    print("""
╔══════════════════════════════════════════════════════╗
║   ✅ 완료!                                           ║
╚══════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    asyncio.run(main())