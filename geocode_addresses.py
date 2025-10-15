# -*- coding: utf-8 -*-
# geocode_addresses.py - DB 주소로 카카오 지오코딩 (병렬 처리)

import sqlite3
import os
import re
import asyncio
import aiohttp
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

DB_FILE = 'seoul_industry_reviews.db'
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY', '')


async def geocode_address_kakao_async(session, address: str, store_name: str = None):
    """카카오 지오코딩 API로 주소 → 좌표 변환 (비동기)"""
    if not address or not KAKAO_REST_API_KEY:
        print(f"      ⚠️ API 키 없음")
        return None, None
    
    try:
        # 방법 1: 주소 검색 API 시도
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {
            "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
        }
        params = {"query": address}
        
        async with session.get(url, headers=headers, params=params, timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                documents = data.get('documents', [])
                
                if documents and len(documents) > 0:
                    first = documents[0]
                    lat = float(first['y'])
                    lng = float(first['x'])
                    return lat, lng
        
        # 방법 2: 실패하면 키워드 검색 (가게명 + 주소)
        if store_name:
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            params = {"query": f"{store_name} {address}"}
            
            async with session.get(url, headers=headers, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    documents = data.get('documents', [])
                    
                    if documents and len(documents) > 0:
                        first = documents[0]
                        lat = float(first['y'])
                        lng = float(first['x'])
                        print(f"      💡 키워드 검색으로 발견!")
                        return lat, lng
        
        # 방법 3: 주소 일부만으로 재시도 (건물번호 제거)
        simplified = re.sub(r'\s+\d+$', '', address)
        
        if simplified != address:
            params = {"query": simplified}
            async with session.get("https://dapi.kakao.com/v2/local/search/address.json", headers=headers, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    documents = data.get('documents', [])
                    
                    if documents and len(documents) > 0:
                        first = documents[0]
                        lat = float(first['y'])
                        lng = float(first['x'])
                        print(f"      💡 단순화된 주소로 발견!")
                        return lat, lng
        
        print(f"      ⚠️ 모든 방법 실패")
        return None, None
    
    except asyncio.TimeoutError:
        print(f"      ⚠️ 타임아웃")
        return None, None
    except Exception as e:
        print(f"      ⚠️ 오류: {e}")
        return None, None


def get_stores_with_address_no_coords():
    """주소는 있지만 좌표가 없는 가게 조회"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT place_id, name, address, district
        FROM stores
        WHERE address IS NOT NULL 
          AND address != ''
          AND (latitude IS NULL OR longitude IS NULL)
        ORDER BY review_count DESC
    """)
    
    stores = [
        {
            'place_id': row[0],
            'name': row[1],
            'address': row[2],
            'district': row[3]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return stores


def batch_update_coords(results):
    """배치로 좌표 일괄 저장"""
    if not results:
        return 0
    
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cursor = conn.cursor()
        
        for result in results:
            if result and result.get('latitude') and result.get('longitude'):
                cursor.execute("""
                    UPDATE stores
                    SET latitude = ?, longitude = ?
                    WHERE place_id = ?
                """, (result['latitude'], result['longitude'], result['place_id']))
        
        conn.commit()
        conn.close()
        return len([r for r in results if r and r.get('latitude')])
        
    except Exception as e:
        print(f"\n❌ 배치 저장 실패: {e}")
        return 0


async def geocode_single_store(session, store, index, total):
    """단일 가게 지오코딩"""
    place_id = store['place_id']
    name = store['name']
    address = store['address']
    district = store['district']
    
    print(f"[{index}/{total}] 📍 {name} ({district})")
    print(f"   주소: {address}")
    
    # 지오코딩 (가게명도 함께 전달)
    print(f"   🌍 좌표 변환 중...")
    latitude, longitude = await geocode_address_kakao_async(session, address, name)
    
    if not latitude or not longitude:
        print(f"      ❌ 좌표 변환 실패")
        return None
    
    print(f"      ✅ 좌표: ({latitude:.6f}, {longitude:.6f})")
    
    return {
        'place_id': place_id,
        'latitude': latitude,
        'longitude': longitude
    }


async def main():
    """메인 실행 함수"""
    print("\n" + "="*60)
    print("🗺️  카카오 지오코딩으로 좌표 업데이트 (실시간 감지)")
    print("="*60)
    
    # API 키 확인
    if not KAKAO_REST_API_KEY:
        print("\n❌ 카카오 API 키가 설정되지 않았습니다!")
        print("\n💡 카카오 API 키 발급 방법:")
        print("   1. https://developers.kakao.com 접속")
        print("   2. 로그인 후 '내 애플리케이션' → '애플리케이션 추가하기'")
        print("   3. 앱 이름 입력 (아무거나)")
        print("   4. 'REST API 키' 복사")
        print("\n💡 .env 파일에 추가:")
        print("   KAKAO_REST_API_KEY=your_key_here")
        return
    
    print(f"\n✅ 카카오 API 키 확인 완료")
    print(f"   Key: {KAKAO_REST_API_KEY[:10]}...")
    
    # 실시간 모드 선택
    mode = input(f"\n실행 모드를 선택하세요:\n  1. 일회성 (현재 좌표 없는 것만)\n  2. 실시간 감지 (계속 확인하면서 처리)\n선택 (1/2, 기본값=1): ").strip()
    
    if mode == '2':
        print("\n⚡ 실시간 감지 모드 - 크롤링이 주소 추가하면 자동으로 지오코딩!")
        print("💡 종료하려면 Ctrl+C\n")
        
        total_processed = 0
        
        async with aiohttp.ClientSession() as session:
            while True:
                # 주기적으로 DB 재조회
                stores = get_stores_with_address_no_coords()
                
                if not stores:
                    print(f"[{total_processed}개 완료] 대기 중... (10초 후 재확인)")
                    await asyncio.sleep(10)
                    continue
                
                print(f"\n🔍 새로 발견: {len(stores)}개")
                
                # 병렬 처리
                parallel_count = 10
                success_count = 0
                fail_count = 0
                
                for batch_start in range(0, len(stores), parallel_count):
                    batch = stores[batch_start:batch_start + parallel_count]
                    
                    tasks = []
                    for i, store in enumerate(batch):
                        index = total_processed + batch_start + i + 1
                        task = geocode_single_store(session, store, index, total_processed + len(stores))
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    valid_results = []
                    for result in results:
                        if isinstance(result, Exception):
                            fail_count += 1
                        elif result:
                            valid_results.append(result)
                        else:
                            fail_count += 1
                    
                    if valid_results:
                        saved = batch_update_coords(valid_results)
                        success_count += saved
                    
                    await asyncio.sleep(0.5)
                
                total_processed += success_count
                print(f"✅ 배치 완료: +{success_count}개 (총 {total_processed}개)")
                
                # 10초 대기 후 재확인
                await asyncio.sleep(10)
    
    else:
        # 기존 일회성 모드
        stores = get_stores_with_address_no_coords()
        
        if not stores:
            print("\n✅ 모든 가게에 좌표가 있습니다!")
            return
        
        print(f"\n📊 좌표 없는 가게: {len(stores):,}개")
        
        parallel_count = 10
        print(f"⚡ 병렬 처리: {parallel_count}개씩 동시 실행")
        print(f"⚠️  예상 소요 시간: 약 {len(stores) * 1 / 60 / parallel_count:.1f}분")
        
        limit_input = input(f"\n몇 개까지 업데이트하시겠습니까? (전체=all, 기본값=100): ").strip()
        
        if limit_input == '':
            limit = 100
        elif limit_input.lower() == 'all':
            limit = len(stores)
        else:
            try:
                limit = int(limit_input)
            except:
                limit = 100
        
        stores = stores[:limit]
        
        print(f"\n🚀 {len(stores)}개 가게 지오코딩 시작! (병렬 {parallel_count}개)\n")
        
        success_count = 0
        fail_count = 0
        
        async with aiohttp.ClientSession() as session:
            for batch_start in range(0, len(stores), parallel_count):
                batch = stores[batch_start:batch_start + parallel_count]
                
                tasks = []
                for i, store in enumerate(batch):
                    index = batch_start + i + 1
                    task = geocode_single_store(session, store, index, len(stores))
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                valid_results = []
                for result in results:
                    if isinstance(result, Exception):
                        print(f"\n      ❌ 오류: {result}")
                        fail_count += 1
                    elif result:
                        valid_results.append(result)
                    else:
                        fail_count += 1
                
                if valid_results:
                    saved = batch_update_coords(valid_results)
                    success_count += saved
                    print(f"\n   💾 배치 저장 완료: {saved}개\n")
                
                if batch_start + parallel_count < len(stores):
                    await asyncio.sleep(0.5)
        
        print("\n" + "="*60)
        print("✅ 지오코딩 완료!")
        print("="*60)
        print(f"   성공: {success_count}개")
        print(f"   실패: {fail_count}개")
        print(f"   총: {success_count + fail_count}개")
        
        if success_count + fail_count > 0:
            print(f"   성공률: {success_count/(success_count+fail_count)*100:.1f}%")
        
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())