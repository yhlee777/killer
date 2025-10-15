# -*- coding: utf-8 -*-
# check_db_realtime.py - 실시간 DB 상태 확인

import sqlite3
import time

DB_FILE = 'seoul_industry_reviews.db'

print("실시간 DB 모니터링 (Ctrl+C로 종료)\n")

prev_with_address = 0
prev_with_coords = 0

while True:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 전체 가게
        cursor.execute("SELECT COUNT(*) FROM stores")
        total = cursor.fetchone()[0]
        
        # 주소 있음
        cursor.execute("SELECT COUNT(*) FROM stores WHERE address IS NOT NULL AND address != ''")
        with_address = cursor.fetchone()[0]
        
        # 좌표 있음
        cursor.execute("SELECT COUNT(*) FROM stores WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        with_coords = cursor.fetchone()[0]
        
        # 주소 있고 좌표 없음
        cursor.execute("""
            SELECT COUNT(*) FROM stores 
            WHERE address IS NOT NULL AND address != ''
              AND (latitude IS NULL OR longitude IS NULL)
        """)
        needs_geocoding = cursor.fetchone()[0]
        
        conn.close()
        
        # 변화량
        address_delta = with_address - prev_with_address
        coords_delta = with_coords - prev_with_coords
        
        # 출력
        print(f"[{time.strftime('%H:%M:%S')}] "
              f"전체:{total} | "
              f"주소:{with_address}(+{address_delta}) | "
              f"좌표:{with_coords}(+{coords_delta}) | "
              f"대기중:{needs_geocoding}")
        
        prev_with_address = with_address
        prev_with_coords = with_coords
        
        time.sleep(3)  # 3초마다 확인
        
    except KeyboardInterrupt:
        print("\n\n종료!")
        break
    except Exception as e:
        print(f"오류: {e}")
        time.sleep(3)