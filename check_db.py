# -*- coding: utf-8 -*-
# check_db.py
# seoul_reviews.db 확인 스크립트

import sqlite3
import json

print("""
╔══════════════════════════════════════════════════════╗
║   서울 리뷰 DB 확인                                  ║
╚══════════════════════════════════════════════════════╝
""")

# DB 연결
conn = sqlite3.connect('seoul_reviews.db')
cursor = conn.cursor()

# 1. 전체 통계
print("📊 전체 통계:")
cursor.execute("SELECT COUNT(*) FROM reviews")
total_reviews = cursor.fetchone()[0]
print(f"   총 리뷰 수: {total_reviews:,}개")

cursor.execute("SELECT COUNT(DISTINCT place_id) FROM stores")
total_stores = cursor.fetchone()[0]
print(f"   총 가게 수: {total_stores}개")

cursor.execute("SELECT COUNT(DISTINCT region) FROM stores WHERE region IS NOT NULL")
total_regions = cursor.fetchone()[0]
print(f"   수집된 지역: {total_regions}개\n")

# 2. 지역별 리뷰 수
print("📍 지역별 리뷰 수:")
cursor.execute("""
    SELECT s.region, COUNT(r.id) as count, COUNT(DISTINCT s.place_id) as stores
    FROM stores s
    LEFT JOIN reviews r ON s.place_id = r.place_id
    WHERE s.region IS NOT NULL
    GROUP BY s.region
    ORDER BY count DESC
""")

regions_data = cursor.fetchall()
success_regions = []

for i, (region, count, stores) in enumerate(regions_data, 1):
    print(f"   [{i:2d}] {region:<20} {count:>4}개 리뷰 ({stores}개 가게)")
    if count > 0:
        success_regions.append(region)

# 3. 0개인 지역 (서울 25개 구)
print("\n❌ 수집 안된 지역:")
ALL_REGIONS = [
    "강남구 맛집", "서초구 맛집", "송파구 맛집", "강동구 맛집",
    "광진구 맛집", "성동구 맛집", "동대문구 맛집", "중랑구 맛집",
    "성북구 맛집", "강북구 맛집", "도봉구 맛집", "노원구 맛집",
    "은평구 맛집", "서대문구 맛집", "마포구 맛집", "용산구 맛집",
    "중구 맛집", "종로구 맛집", "영등포구 맛집", "구로구 맛집",
    "금천구 맛집", "동작구 맛집", "관악구 맛집", "양천구 맛집",
    "강서구 맛집"
]

collected_regions = [r[0] for r in regions_data]
missing_regions = [r for r in ALL_REGIONS if r not in collected_regions]

if missing_regions:
    for region in missing_regions:
        print(f"   - {region}")
else:
    print("   (없음)")

# 4. progress.json 수정 제안
print("\n" + "="*55)
print("💡 다음 단계:")

if missing_regions:
    print(f"\n1️⃣  progress.json 수정 (추천)")
    print(f"   - 성공한 {len(success_regions)}개 지역은 유지")
    print(f"   - 실패한 {len(missing_regions)}개 지역만 재수집")
    
    # progress.json 생성
    new_progress = {
        "completed_regions": success_regions,
        "failed_stores": []
    }
    
    with open('progress_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(new_progress, f, ensure_ascii=False, indent=2)
    
    print(f"\n   ✅ progress_fixed.json 파일 생성됨!")
    print(f"   \n   실행 방법:")
    print(f"   1. progress.json 삭제")
    print(f"   2. progress_fixed.json 이름을 progress.json으로 변경")
    print(f"   3. python turbo_crawler.py 실행")
    
    print(f"\n2️⃣  또는 처음부터 다시:")
    print(f"   del seoul_reviews.db")
    print(f"   del progress.json")
    print(f"   python turbo_crawler.py")

else:
    print("\n✅ 모든 지역 수집 완료!")

conn.close()

print("\n" + "="*55)