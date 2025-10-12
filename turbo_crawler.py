# -*- coding: utf-8 -*-
# turbo_crawler.py - 봇 탐지 우회 + headless=False

import asyncio
import sqlite3
import re
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import random

DB_FILE = 'seoul_industry_reviews.db'
PROGRESS_FILE = "turbo_progress.json"
PARALLEL_WORKERS = 5  # 🔥 5개 워커 (속도 UP)
TARGET_REVIEWS = 100
SCROLL_DEPTH = 15

# ==================== User-Agent 랜덤화 ====================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

# ==================== 서울 지역 ====================

SEOUL_ALL_AREAS = [
    "강남역", "신논현역", "논현역", "압구정", "청담", "삼성동", "역삼", "선릉",
    "홍대입구역", "홍대", "연남동", "상수역", "합정역", "망원동",
    "이태원", "경리단길", "한남동", "성수동", "뚝섬", "건대입구",
    "신촌", "이대", "여의도", "잠실", "혜화", "성신여대",
    "종로", "명동", "익선동", "삼청동"
]

INDUSTRIES = [
    "카페", "디저트카페", "베이커리", "브런치카페",
    "파스타", "이탈리안", "스테이크", "피자", "버거",
    "오마카세", "스시", "이자카야", "라멘", "우동", "돈카츠",
    "딤섬", "마라탕", "쌀국수", "태국음식",
    "한식당", "고기집", "삼겹살", "곱창",
    "와인바", "칵테일바", "바", "펍"
]

# ==================== DB 관련 ====================

def get_existing_place_ids():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT place_id FROM stores")
        existing = set(row[0] for row in cursor.fetchall())
        conn.close()
        print(f"✅ 기존 가게: {len(existing):,}개")
        return existing
    except:
        return set()

def save_to_db(place_id, store_name, region, industry, reviews):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO stores 
            (place_id, name, district, industry, review_count, crawled_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (place_id, store_name, region, industry, len(reviews), datetime.now().isoformat()))
        
        for r in reviews:
            cursor.execute("""
                INSERT INTO reviews 
                (place_id, date, content, crawled_at) 
                VALUES (?, ?, ?, ?)
            """, (place_id, r.get('날짜'), r.get('리뷰', ''), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False

def save_progress_safe(progress):
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# ==================== 크롤링 ====================

def is_owner_reply(review_text):
    if not review_text:
        return False
    strong_signals = ['리뷰 감사', '진심으로 감사', '찾아주셔서', '보답하겠습니다']
    return any(s in review_text for s in strong_signals) or \
           sum(1 for k in ['감사드립니다', '감사합니다'] if k in review_text) >= 2

async def expand_reviews(page):
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

async def collect_place_ids(search_query, scroll_depth, max_stores, worker_id, existing_ids):
    """Place ID 수집 - 봇 탐지 우회"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,  # 🔥 False 유지!
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security'
            ]
        )
        
        # 🔥 랜덤 User-Agent
        user_agent = random.choice(USER_AGENTS)
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, 
            locale="ko-KR",
            user_agent=user_agent,
            # 🔥 추가 헤더
            extra_http_headers={
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        )
        
        # 🔥 강화된 봇 탐지 우회
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
        """)
        
        page = await context.new_page()
        
        try:
            # 🔥 랜덤 대기 (1-3초)
            await asyncio.sleep(random.uniform(1, 3))
            
            await page.goto(
                f"https://map.naver.com/v5/search/{search_query}", 
                wait_until="domcontentloaded", 
                timeout=30000
            )
            await asyncio.sleep(random.uniform(2, 4))  # 🔥 랜덤 대기
            
            search_frame = None
            for attempt in range(12):
                for frame in page.frames:
                    if "searchIframe" in frame.name or "entry=plt" in frame.url or "restaurant/list" in frame.url:
                        search_frame = frame
                        break
                if search_frame:
                    break
                await asyncio.sleep(random.uniform(0.5, 1.0))
            
            if not search_frame:
                await context.close()
                await browser.close()
                return []
            
            # 🔥 인간처럼 스크롤 (속도 랜덤)
            for i in range(scroll_depth):
                try:
                    scroll_amount = random.randint(700, 1000)
                    await search_frame.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(0.3, 0.6))
                except:
                    pass
            
            await asyncio.sleep(1)
            
            store_items = []
            for sel in ["li.UEzoS", "li.CHC5F", "li[data-id]"]:
                try:
                    items = await search_frame.locator(sel).all()
                    valid_items = []
                    for item in items[:50]:
                        try:
                            text = await item.inner_text(timeout=300)
                            if len(text) > 10:
                                valid_items.append(item)
                        except:
                            pass
                    if len(valid_items) >= 5:
                        store_items = valid_items
                        break
                except:
                    pass
            
            place_data = []
            for i, item in enumerate(store_items[:max_stores], 1):
                try:
                    store_name = "알 수 없음"
                    try:
                        name_text = await item.inner_text(timeout=500)
                        lines = [ln.strip() for ln in name_text.split('\n') if ln.strip()]
                        if lines:
                            store_name = lines[0][:30]
                    except:
                        pass
                    
                    # 🔥 랜덤 대기 (인간 시뮬레이션)
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    await item.click(timeout=2000)
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    place_id = None
                    for frame in page.frames:
                        match = re.search(r'place[/=](\d+)', frame.url)
                        if match:
                            place_id = match.group(1)
                            break
                    
                    if place_id and place_id not in existing_ids:
                        place_data.append({"place_id": place_id, "name": store_name})
                    
                    await page.go_back(wait_until="domcontentloaded", timeout=8000)
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    search_frame = None
                    for frame in page.frames:
                        if "searchIframe" in frame.name or "entry=plt" in frame.url:
                            search_frame = frame
                            break
                    if not search_frame:
                        break
                    
                except:
                    continue
            
            await context.close()
            await browser.close()
            return place_data
            
        except:
            await context.close()
            await browser.close()
            return []

async def collect_reviews(place_id, store_name, region, industry, worker_id, existing_ids):
    """리뷰 수집 - 봇 탐지 우회"""
    if place_id in existing_ids:
        return None
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,  # 🔥 False 유지!
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        
        user_agent = random.choice(USER_AGENTS)
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}, 
            locale="ko-KR",
            user_agent=user_agent
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()
        
        try:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            review_url = f"https://m.place.naver.com/restaurant/{place_id}/review/visitor"
            await page.goto(review_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # 최신순 정렬
            try:
                for selector in ["button:has-text('최신순')", "a:has-text('최신순')"]:
                    try:
                        await page.click(selector, timeout=2000)
                        await asyncio.sleep(1)
                        break
                    except:
                        continue
            except:
                pass
            
            # 🔥 인간처럼 스크롤
            for i in range(25):
                try:
                    scroll_amount = random.randint(1800, 2200)
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                except:
                    pass
                await asyncio.sleep(random.uniform(0.2, 0.4))
                await expand_reviews(page)
                
                if i % 10 == 0:
                    count = 0
                    for sel in ["li.place_apply_pui", "li.pui__X35jYm"]:
                        try:
                            count = await page.locator(sel).count()
                            if count >= TARGET_REVIEWS:
                                break
                        except:
                            pass
                    if count >= TARGET_REVIEWS:
                        break
            
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
            
            for item in review_items[:TARGET_REVIEWS + 20]:
                try:
                    full_text = await item.inner_text(timeout=500)
                    if len(full_text) < 50 or '키워드·별점' in full_text:
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
                    lines = [ln for ln in lines if not re.search(r'\d{4}[./-]', ln)]
                    if lines:
                        review["리뷰"] = max(lines, key=len)
                    
                    if review["리뷰"] and len(review["리뷰"]) >= 20 and not is_owner_reply(review["리뷰"]):
                        reviews.append(review)
                    
                    if len(reviews) >= TARGET_REVIEWS:
                        break
                        
                except:
                    pass
            
            await context.close()
            await browser.close()
            return reviews
            
        except:
            await context.close()
            await browser.close()
            return []

# ==================== 워커 ====================

async def worker(worker_id, query_queue, progress, existing_ids, stats_lock):
    print(f"[W{worker_id}] 🚀 워커 시작")
    
    while True:
        try:
            query_data = await query_queue.get()
            if query_data is None:
                break
            
            query = query_data['query']
            area = query_data['area']
            industry = query_data['industry']
            
            print(f"\n[W{worker_id}] 🎯 {query}")
            
            # 🔥 워커마다 시작 시간 랜덤화 (봇 탐지 회피)
            await asyncio.sleep(random.uniform(0, 3))
            
            place_data = await collect_place_ids(query, SCROLL_DEPTH, 20, worker_id, existing_ids)
            
            if not place_data:
                print(f"[W{worker_id}] ⚠️  신규 없음")
                async with stats_lock:
                    progress["completed_queries"].append(query)
                    save_progress_safe(progress)
                query_queue.task_done()
                continue
            
            for i, store in enumerate(place_data, 1):
                place_id = store['place_id']
                store_name = store['name']
                
                reviews = await collect_reviews(place_id, store_name, area, industry, worker_id, existing_ids)
                
                if reviews:
                    save_to_db(place_id, store_name, area, industry, reviews)
                    existing_ids.add(place_id)
                    
                    async with stats_lock:
                        progress["new_stores_count"] = progress.get("new_stores_count", 0) + 1
                        progress["total_reviews"] = progress.get("total_reviews", 0) + len(reviews)
                        save_progress_safe(progress)
                    
                    print(f"[W{worker_id}] 💾 [{i}/{len(place_data)}] {store_name[:15]} - {len(reviews)}개")
            
            async with stats_lock:
                progress["completed_queries"].append(query)
                save_progress_safe(progress)
            
            query_queue.task_done()
            
        except Exception as e:
            print(f"[W{worker_id}] ❌ {e}")
            query_queue.task_done()

# ==================== 메인 ====================

async def main():
    print("""
╔══════════════════════════════════════════════════════╗
║   🛡️ 터보 크롤러 v2 (봇 탐지 우회)                 ║
║   - 워커 5개                                         ║
║   - headless=False (안전)                            ║
║   - 랜덤 User-Agent                                  ║
║   - 인간 시뮬레이션 (랜덤 대기)                      ║
║   - 실시간 progress 저장                             ║
╚══════════════════════════════════════════════════════╝
    """)
    
    existing_ids = get_existing_place_ids()
    
    queries = []
    for area in SEOUL_ALL_AREAS:
        for industry in INDUSTRIES:
            queries.append({'query': f"{area} {industry}", 'area': area, 'industry': industry})
    random.shuffle(queries)
    
    print(f"📋 총 쿼리: {len(queries):,}개\n")
    
    progress = {"completed_queries": [], "new_stores_count": 0, "total_reviews": 0}
    if Path(PROGRESS_FILE).exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                progress = json.load(f)
            print(f"📂 이전 진행: {len(progress['completed_queries'])}개 완료")
            print(f"   신규 가게: {progress.get('new_stores_count', 0)}개")
            print(f"   신규 리뷰: {progress.get('total_reviews', 0):,}개\n")
        except:
            pass
    
    query_queue = asyncio.Queue()
    for q in queries:
        if q['query'] not in progress["completed_queries"]:
            await query_queue.put(q)
    
    print(f"🎯 남은 쿼리: {query_queue.qsize():,}개\n")
    
    for _ in range(PARALLEL_WORKERS):
        await query_queue.put(None)
    
    stats_lock = asyncio.Lock()
    workers = [
        asyncio.create_task(worker(i, query_queue, progress, existing_ids, stats_lock)) 
        for i in range(PARALLEL_WORKERS)
    ]
    
    await query_queue.join()
    await asyncio.gather(*workers)
    
    save_progress_safe(progress)
    
    print(f"""
╔══════════════════════════════════════════════════════╗
║   ✅ 완료!                                           ║
║   🆕 신규 가게: {progress['new_stores_count']:,}개
║   📝 신규 리뷰: {progress.get('total_reviews', 0):,}개
║   📊 완료 쿼리: {len(progress['completed_queries']):,}개
╚══════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    asyncio.run(main())