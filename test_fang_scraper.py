"""
测试房天下正式爬虫
"""
import sys
sys.path.insert(0, '.')

from src.scraper.fang import FangScraper

print("=== 测试房天下爬虫 ===")
scraper = FangScraper()
records = scraper.scrape()

print(f"\n共抓取到 {len(records)} 条数据")
print("\n--- 数据样例 ---")
for r in records[:15]:
    print(f"  [{r['region']}] {r['community']}: {r['price']} {r['unit']} (来源: {r['source']})")

# 按区域统计
print("\n--- 按区域统计 ---")
from collections import Counter
region_counts = Counter(r['region'] for r in records)
for region, count in region_counts.most_common():
    print(f"  {region}: {count} 条")
