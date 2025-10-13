# -*- coding: utf-8 -*-
# ultimate_report_generator.py - 완전 통합 보고서 (HTML 하나로!)

import json
from datetime import datetime
from typing import Dict, List, Optional

# 기존 모듈 임포트
from all_in_one_html import deep_analyze_reviews
from master_analyzer import generate_action_checklist


def generate_ultimate_report(
    target_store: Dict,
    target_reviews: List[Dict],
    blog_profile: Optional[object],
    competitors: List,
    competitor_reviews: Dict,
    statistical_comparison: Optional[Dict],
    search_strategy: Dict
) -> str:
    """
    완전 통합 HTML 보고서 생성
    
    구조:
    1. Executive Summary
    2. 블로그 분석
    3. 리뷰 심층 분석 (차트 포함)
    4. 경쟁사 비교
    5. 실행 체크리스트
    6. 부록 (상세 통계)
    """
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # ==================== 1. 심층 분석 (GPT) ====================
    
    print(f"\n{'='*60}")
    print("🔬 심층 분석 중...")
    print(f"{'='*60}")
    
    analysis = deep_analyze_reviews(target_reviews, target_store)
    
    strengths = analysis.get('장점', [])
    weaknesses = analysis.get('단점', [])
    improvements = analysis.get('잠재적_개선점', [])
    
    # ==================== 2. 체크리스트 생성 ====================
    
    print(f"\n{'='*60}")
    print("✅ 체크리스트 생성 중...")
    print(f"{'='*60}")
    
    checklist = generate_action_checklist(
        blog_profile=blog_profile,
        insight_html="",
        comparison_result=statistical_comparison
    )
    
    # ==================== 3. 데이터 준비 ====================
    
    # 별점 분포
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in target_reviews:
        rating = int(r.get('rating', 5))
        if rating == 0:
            rating = 5
        rating_dist[rating] += 1
    
    # 장점/단점 차트 데이터
    strengths_data = {s['aspect']: s['percentage'] for s in strengths[:6]}
    weaknesses_data = {w['aspect']: w['percentage'] for w in weaknesses[:6]}
    
    # 경쟁사 비교 데이터
    comp_strengths_list = []
    comp_weaknesses_list = []
    
    if statistical_comparison:
        for topic, stat in list(statistical_comparison.get('우리의_강점', {}).items())[:5]:
            comp_strengths_list.append({
                'topic': topic,
                'our_rate': stat['our']['rate'] * 100,
                'comp_rate': stat['comp']['rate'] * 100,
                'gap': stat['gap'] * 100
            })
        
        for topic, stat in list(statistical_comparison.get('우리의_약점', {}).items())[:5]:
            comp_weaknesses_list.append({
                'topic': topic,
                'our_rate': stat['our']['rate'] * 100,
                'comp_rate': stat['comp']['rate'] * 100,
                'gap': stat['gap'] * 100
            })
    
    # ==================== 4. HTML 생성 ====================
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{target_store['name']} - Ultimate 분석 리포트</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', 'Noto Sans KR', -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.7;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 80px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 50px 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.8em;
            margin-bottom: 15px;
            font-weight: 700;
        }}
        
        .header .meta {{
            font-size: 1.1em;
            opacity: 0.95;
            margin-top: 15px;
        }}
        
        .nav {{
            background: #f8f9fa;
            padding: 15px 40px;
            border-bottom: 2px solid #e9ecef;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .nav-links {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        
        .nav-links a {{
            color: #667eea;
            text-decoration: none;
            padding: 8px 20px;
            border-radius: 20px;
            transition: all 0.3s;
            font-weight: 600;
        }}
        
        .nav-links a:hover {{
            background: #667eea;
            color: white;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            background: #f8f9fa;
            padding: 40px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }}
        
        h2 {{
            color: #333;
            font-size: 2em;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        h3 {{
            color: #555;
            font-size: 1.4em;
            margin: 25px 0 15px 0;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        
        .summary-card {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        
        .summary-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .summary-value.negative {{
            color: #ff6b6b;
        }}
        
        .summary-value.positive {{
            color: #51cf66;
        }}
        
        .summary-label {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .blog-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .blog-stat {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .blog-stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .blog-stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        
        .chart-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }}
        
        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .weakness-list {{
            display: grid;
            gap: 20px;
            margin: 25px 0;
        }}
        
        .weakness-item {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            border-left: 5px solid #ff6b6b;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        
        .weakness-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .weakness-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }}
        
        .severity-badge {{
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        
        .severity-심각 {{ background: #ff6b6b; color: white; }}
        .severity-보통 {{ background: #feca57; color: #333; }}
        .severity-경미 {{ background: #48dbfb; color: white; }}
        
        .weakness-stats {{
            color: #666;
            margin: 12px 0;
            font-size: 1.05em;
        }}
        
        .weakness-samples {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 15px;
        }}
        
        .review-sample {{
            padding: 10px 0;
            color: #555;
            border-bottom: 1px solid #e0e0e0;
            line-height: 1.6;
        }}
        
        .review-sample:last-child {{
            border-bottom: none;
        }}
        
        .strength-item {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            border-left: 5px solid #51cf66;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            margin: 15px 0;
        }}
        
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        
        .comparison-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        
        .comparison-item {{
            padding: 15px;
            margin: 12px 0;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .comparison-item.positive {{
            border-left-color: #51cf66;
        }}
        
        .comparison-item.negative {{
            border-left-color: #ff6b6b;
        }}
        
        .comparison-stat {{
            color: #666;
            font-size: 0.95em;
            margin-top: 8px;
        }}
        
        .checklist {{
            background: white;
            padding: 25px;
            border-radius: 12px;
        }}
        
        .checklist-item {{
            padding: 18px;
            margin: 12px 0;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: flex-start;
        }}
        
        .checklist-item:hover {{
            background: #e9ecef;
            transform: translateX(5px);
        }}
        
        .checklist-item input[type="checkbox"] {{
            margin-right: 15px;
            transform: scale(1.5);
            cursor: pointer;
            margin-top: 3px;
        }}
        
        .alert {{
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 5px solid;
        }}
        
        .alert-info {{
            background: #e7f5ff;
            border-color: #339af0;
            color: #1864ab;
        }}
        
        .alert-success {{
            background: #d3f9d8;
            border-color: #51cf66;
            color: #2b8a3e;
        }}
        
        .alert-warning {{
            background: #fff3bf;
            border-color: #feca57;
            color: #f08c00;
        }}
        
        @media (max-width: 768px) {{
            .chart-grid,
            .comparison-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .nav {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏪 {target_store['name']}</h1>
            <div class="meta">
                📅 {timestamp} | 📍 {target_store['district']} | 🍽️ {target_store['industry']}
            </div>
            <div class="meta" style="margin-top: 10px;">
                분석 리뷰: {len(target_reviews)}개 | 경쟁사: {len(competitors)}개 | 전략: {search_strategy['name']}
            </div>
        </div>
        
        <div class="nav">
            <div class="nav-links">
                <a href="#summary">📊 요약</a>
                <a href="#blog">📱 블로그</a>
                <a href="#review">⭐ 리뷰</a>
                <a href="#competitor">🏆 경쟁사</a>
                <a href="#checklist">✅ 체크리스트</a>
            </div>
        </div>
        
        <div class="content">
            <!-- Part 1: Summary -->
            <div id="summary" class="section">
                <h2>📊 Executive Summary</h2>
                
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="summary-value">{len(strengths)}</div>
                        <div class="summary-label">발견된 장점</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-value negative">{len(weaknesses)}</div>
                        <div class="summary-label">개선 필요 사항</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-value positive">{rating_dist[5] / len(target_reviews) * 100:.1f}%</div>
                        <div class="summary-label">5점 비율</div>
                    </div>
                    {'<div class="summary-card"><div class="summary-value">' + f"{blog_profile.positive_ratio:.1%}" + '</div><div class="summary-label">블로그 긍정률</div></div>' if blog_profile else ''}
                </div>
                
                <div class="alert alert-info">
                    <strong>💡 핵심 메시지</strong><br>
                    • 통계적으로 확인된 약점을 우선 개선하세요<br>
                    • 경쟁사보다 강한 부분을 마케팅에 활용하세요<br>
                    • 2주 단위로 실행하고 측정하세요
                </div>
            </div>
"""

    # Part 2: 블로그
    if blog_profile:
        html += f"""
            <div id="blog" class="section">
                <h2>📱 블로그 평판 분석 ({blog_profile.total_blog_posts}개)</h2>
                
                <div class="blog-stats">
                    <div class="blog-stat">
                        <div class="blog-stat-value">{blog_profile.concept}</div>
                        <div class="blog-stat-label">인식 컨셉</div>
                    </div>
                    <div class="blog-stat">
                        <div class="blog-stat-value">{blog_profile.positive_ratio:.1%}</div>
                        <div class="blog-stat-label">긍정 비율</div>
                    </div>
                    <div class="blog-stat">
                        <div class="blog-stat-value">{blog_profile.avg_rating:.1f}/5.0</div>
                        <div class="blog-stat-label">평균 평점</div>
                    </div>
                </div>
                
                <h3>주요 방문 목적</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0;">
"""
        
        for purpose, count in list(blog_profile.visit_purposes.items())[:5]:
            html += f"""
                    <div style="background: white; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 1.5em; font-weight: bold; color: #667eea;">{count}회</div>
                        <div style="color: #666; margin-top: 5px;">{purpose}</div>
                    </div>
"""
        
        html += f"""
                </div>
                
                <h3>분위기 키워드</h3>
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 15px 0;">
                    {', '.join(blog_profile.atmosphere_keywords[:5]) if blog_profile.atmosphere_keywords else '정보 없음'}
                </div>
                
                <div class="alert alert-warning">
                    <strong>⚠️ 블로그 vs 실제 Gap 체크</strong><br>
                    블로그는 "{blog_profile.concept}" 컨셉이지만, 실제 리뷰와 일치하는지 확인하세요!
                </div>
            </div>
"""
    
    # Part 3: 리뷰 분석
    html += f"""
            <div id="review" class="section">
                <h2>⭐ 리뷰 심층 분석</h2>
                
                <div class="chart-grid">
                    <div class="chart-container">
                        <h3 style="text-align: center; margin-bottom: 20px;">별점 분포</h3>
                        <canvas id="rating-chart"></canvas>
                    </div>
                    <div class="chart-container">
                        <h3 style="text-align: center; margin-bottom: 20px;">장점 분포</h3>
                        <canvas id="strengths-chart"></canvas>
                    </div>
                </div>
                
                <h3>✅ 우리 가게 장점</h3>
                <div style="display: grid; gap: 15px; margin: 20px 0;">
"""
    
    for s in strengths[:5]:
        html += f"""
                    <div class="strength-item">
                        <div class="weakness-header">
                            <div class="weakness-title">{s['aspect']}</div>
                            <div style="color: #666;">{s['count']}회 ({s['percentage']:.1f}%)</div>
                        </div>
                        <div class="weakness-samples">
                            {''.join([f'<div class="review-sample">💬 {sample}</div>' for sample in s['samples'][:2]])}
                        </div>
                    </div>
"""
    
    html += f"""
                </div>
                
                <h3>⚠️ 개선이 필요한 부분</h3>
                <div class="weakness-list">
"""
    
    if weaknesses:
        for w in weaknesses:
            html += f"""
                    <div class="weakness-item">
                        <div class="weakness-header">
                            <div class="weakness-title">🚨 {w['aspect']}</div>
                            <div class="severity-badge severity-{w['severity']}">{w['severity']}</div>
                        </div>
                        <div class="weakness-stats">
                            📊 {w['count']}회 언급 ({w['percentage']:.1f}%)
                        </div>
                        <div class="weakness-samples">
                            <strong>실제 리뷰:</strong>
                            {''.join([f'<div class="review-sample">💬 {sample}</div>' for sample in w['samples'][:3]])}
                        </div>
                    </div>
"""
    else:
        html += """
                    <div class="alert alert-success">
                        <strong>✨ 우수한 상태!</strong><br>
                        고객 만족도가 매우 높습니다!
                    </div>
"""
    
    html += """
                </div>
            </div>
"""
    
    # Part 4: 경쟁사
    if statistical_comparison:
        html += f"""
            <div id="competitor" class="section">
                <h2>🏆 경쟁사 비교 ({len(competitors)}개)</h2>
                
                <div class="comparison-grid">
                    <div class="comparison-card">
                        <h3>✅ 우리가 강한 부분</h3>
"""
        
        for item in comp_strengths_list:
            html += f"""
                        <div class="comparison-item positive">
                            <strong>{item['topic']}</strong>
                            <div class="comparison-stat">
                                우리: {item['our_rate']:.1f}% | 경쟁사: {item['comp_rate']:.1f}% | GAP: +{abs(item['gap']):.1f}%p
                            </div>
                        </div>
"""
        
        html += """
                    </div>
                    <div class="comparison-card">
                        <h3>⚠️ 우리가 약한 부분</h3>
"""
        
        for item in comp_weaknesses_list:
            html += f"""
                        <div class="comparison-item negative">
                            <strong>{item['topic']}</strong>
                            <div class="comparison-stat">
                                우리: {item['our_rate']:.1f}% | 경쟁사: {item['comp_rate']:.1f}% | GAP: {item['gap']:.1f}%p
                            </div>
                        </div>
"""
        
        html += """
                    </div>
                </div>
                
                <h3 style="margin-top: 30px;">📌 분석 대상 경쟁사</h3>
                <div style="background: white; padding: 20px; border-radius: 10px;">
                    <ul style="list-style-position: inside;">
"""
        
        for i, comp in enumerate(competitors, 1):
            html += f"""
                        <li style="padding: 8px 0; border-bottom: 1px solid #e9ecef;">
                            <strong>{comp.name}</strong> - {comp.district} ({comp.review_count}개 리뷰)
                        </li>
"""
        
        html += """
                    </ul>
                </div>
            </div>
"""
    
    # Part 5: 체크리스트
    checklist_lines = checklist.split('\n')
    checklist_items = [line.strip() for line in checklist_lines if line.strip().startswith('- [ ]')]
    
    html += f"""
            <div id="checklist" class="section">
                <h2>✅ 2주 실행 체크리스트</h2>
                <div class="checklist">
"""
    
    for item in checklist_items[:10]:
        clean_item = item.replace('- [ ]', '').strip()
        html += f"""
                    <div class="checklist-item" onclick="this.querySelector('input').checked = !this.querySelector('input').checked">
                        <input type="checkbox">
                        <span>{clean_item}</span>
                    </div>
"""
    
    html += """
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 별점 분포
        new Chart(document.getElementById('rating-chart'), {
            type: 'bar',
            data: {
                labels: ['★', '★★', '★★★', '★★★★', '★★★★★'],
                datasets: [{
                    label: '리뷰 수',
                    data: """ + json.dumps([rating_dist[1], rating_dist[2], rating_dist[3], rating_dist[4], rating_dist[5]]) + """,
                    backgroundColor: ['#ff6b6b', '#feca57', '#ffeaa7', '#55efc4', '#00b894']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        // 장점 파이
        new Chart(document.getElementById('strengths-chart'), {
            type: 'pie',
            data: {
                labels: """ + json.dumps(list(strengths_data.keys())) + """,
                datasets: [{
                    data: """ + json.dumps(list(strengths_data.values())) + """,
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    return html


# ==================== 메인 실행 함수 ====================

async def generate_and_save_ultimate_report(
    target_store, target_reviews, blog_profile,
    competitors, competitor_reviews, statistical_comparison, search_strategy
):
    """Ultimate 리포트 생성 및 저장"""
    
    print(f"\n{'='*60}")
    print("🚀 Ultimate 통합 리포트 생성 중...")
    print(f"{'='*60}")
    
    html = generate_ultimate_report(
        target_store=target_store,
        target_reviews=target_reviews,
        blog_profile=blog_profile,
        competitors=competitors,
        competitor_reviews=competitor_reviews,
        statistical_comparison=statistical_comparison,
        search_strategy=search_strategy
    )
    
    # 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ultimate_report_{target_store['name'].replace(' ', '_')}_{timestamp}.html"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n{'='*60}")
        print("✅ Ultimate 리포트 생성 완료!")
        print(f"{'='*60}")
        print(f"📂 파일: {filename}")
        print(f"💡 브라우저로 열어서 확인하세요!")
        
        return filename
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return None