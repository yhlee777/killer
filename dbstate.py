# -*- coding: utf-8 -*-
# db_export_simple.py
# 지역/업종별 간단 분류 및 개수 확인

import sqlite3
import pandas as pd
from pathlib import Path

DB_FILE = 'seoul_industry_reviews.db'
OUTPUT_DIR = Path('data_export')
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("  📦 지역/업종별 데이터 추출 시작")
print("=" * 60)

conn = sqlite3.connect(DB_FILE)

# ==================== 1. 전체 통계 ====================
stats = pd.read_sql("""
    SELECT 
        COUNT(DISTINCT s.place_id) as stores,
        COUNT(r.id) as reviews
    FROM stores s
    LEFT JOIN reviews r ON s.place_id = r.place_id
""", conn).iloc[0]

print(f"\n총 가게: {stats['stores']:,}개")
print(f"총 리뷰: {stats['reviews']:,}개\n")

# ==================== 2. 지역별 폴더 생성 ====================
print("=" * 60)
print("📍 지역별 데이터 추출 중...")
print("=" * 60)

districts = pd.read_sql("""
    SELECT DISTINCT district 
    FROM stores 
    WHERE district IS NOT NULL 
    ORDER BY district
""", conn)['district'].tolist()

for i, district in enumerate(districts, 1):
    # 지역별 전체 데이터
    district_data = pd.read_sql("""
        SELECT 
            s.place_id as 가게ID,
            s.name as 가게명,
            s.industry as 업종,
            r.rating as 평점,
            r.date as 날짜,
            r.content as 리뷰내용
        FROM stores s
        LEFT JOIN reviews r ON s.place_id = r.place_id
        WHERE s.district = ?
        ORDER BY s.name, r.date DESC
    """, conn, params=(district,))
    
    # 지역별 폴더 생성
    district_dir = OUTPUT_DIR / district
    district_dir.mkdir(exist_ok=True)
    
    # 전체 파일 저장
    output_file = district_dir / f'{district}_전체.csv'
    district_data.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    store_count = district_data['가게명'].nunique()
    review_count = len(district_data)
    
    print(f"[{i:2d}] {district:<15} → {store_count:>4}개 가게, {review_count:>6}개 리뷰")

# ==================== 3. 지역 내 업종별 파일 생성 ====================
print("\n" + "=" * 60)
print("🍽️  지역 내 업종별 데이터 추출 중...")
print("=" * 60)

for district in districts:
    district_dir = OUTPUT_DIR / district
    
    # 해당 지역의 업종 리스트
    industries = pd.read_sql("""
        SELECT DISTINCT industry 
        FROM stores 
        WHERE district = ? AND industry IS NOT NULL
        ORDER BY industry
    """, conn, params=(district,))['industry'].tolist()
    
    print(f"\n{district} ({len(industries)}개 업종)")
    
    for industry in industries:
        industry_data = pd.read_sql("""
            SELECT 
                s.place_id as 가게ID,
                s.name as 가게명,
                r.rating as 평점,
                r.date as 날짜,
                r.content as 리뷰내용
            FROM stores s
            LEFT JOIN reviews r ON s.place_id = r.place_id
            WHERE s.district = ? AND s.industry = ?
            ORDER BY s.name, r.date DESC
        """, conn, params=(district, industry))
        
        output_file = district_dir / f'{industry}.csv'
        industry_data.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        store_count = industry_data['가게명'].nunique()
        review_count = len(industry_data)
        
        print(f"  └─ {industry:<15} → {store_count:>3}개 가게, {review_count:>5}개 리뷰")

# ==================== 4. 요약 통계 ====================
print("\n" + "=" * 60)
print("📊 요약 통계 생성 중...")
print("=" * 60)

summary = pd.read_sql("""
    SELECT 
        s.district as 지역,
        s.industry as 업종,
        COUNT(DISTINCT s.place_id) as 가게수,
        COUNT(r.id) as 리뷰수
    FROM stores s
    LEFT JOIN reviews r ON s.place_id = r.place_id
    WHERE s.district IS NOT NULL AND s.industry IS NOT NULL
    GROUP BY s.district, s.industry
    ORDER BY s.district, 가게수 DESC
""", conn)

output_file = OUTPUT_DIR / '00_전체요약.csv'
summary.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"✅ 전체 요약 파일 생성: {output_file}")

conn.close()

print("\n" + "=" * 60)
print("✅ 완료!")
print("=" * 60)
print(f"\n생성된 폴더: {OUTPUT_DIR}/")
print(f"  ├─ 00_전체요약.csv")
for district in districts[:3]:
    print(f"  ├─ {district}/")
    print(f"  │   ├─ {district}_전체.csv")
    print(f"  │   └─ [업종별].csv")
print(f"  └─ ...")
print(f"\n총 {len(districts)}개 지역별 폴더 생성됨")