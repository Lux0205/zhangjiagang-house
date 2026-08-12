"""
深入分析房天下的房价数据结构
"""
import requests
import re
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_fang_detail():
    """详细分析房天下页面"""
    print("=== 房天下详细结构分析 ===")
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 1. 查找所有包含价格数字的元素
    print("\n--- 所有包含'元/平'的元素 ---")
    for elem in soup.find_all(string=re.compile(r'元/平')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            if len(text) < 200:
                print(f"  [{parent.name}] {text}")

    # 2. 搜索均价相关div
    print("\n--- 搜索均价相关class ---")
    avg_elems = soup.select('[class*="average"], [class*="Average"], [class*="price"], [class*="Price"]')
    for elem in avg_elems[:20]:
        text = elem.get_text(strip=True)
        if text and len(text) < 100:
            print(f"  [{elem.name}] class={elem.get('class')} : {text}")

    # 3. 搜索包含数字的区域卡片
    print("\n--- 搜索区域卡片 ---")
    cards = soup.select('.district, .area, .region, [class*="district"], [class*="area"]')
    for card in cards[:20]:
        text = card.get_text(strip=True)
        if text and len(text) < 200 and any(c.isdigit() for c in text):
            print(f"  [{card.name}] class={card.get('class')} : {text[:150]}")

    # 4. 直接搜索包含区域名和价格的最相关文本块
    print("\n--- 关键词+价格组合 ---")
    keywords = ['杨舍', '塘桥', '金港', '后塍', '德积', '锦丰', '凤凰', '乐余', '南丰', '大新',
                '步行街', '人民路', '长安路', '市中心']
    for kw in keywords:
        for match in soup.find_all(string=re.compile(re.escape(kw))):
            parent = match.parent
            if parent:
                granpa = parent.parent
                if granpa:
                    text = granpa.get_text(strip=True)
                    if len(text) < 300 and any(c.isdigit() for c in text):
                        print(f"  [{kw}] {text[:200]}")

    # 5. 搜索script标签中的数据
    print("\n--- script标签中的数据 ---")
    for script in soup.find_all('script'):
        text = script.string or ''
        if 'price' in text.lower() or '均价' in text or '元' in text:
            # 提取数字
            prices = re.findall(r'[\d]+', text)
            if len(prices) > 3:
                print(f"  script: {text[:300]}")
                print(f"  ---")
                break


def analyze_anjuke_detail():
    """详细分析安居客页面"""
    print("\n\n=== 安居客详细结构分析 ===")
    r = requests.get('https://www.anjuke.com/fangjia/zhangjiagang/', headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 查找所有包含数字的元素
    print("\n--- 包含'均价'的元素 ---")
    for elem in soup.find_all(string=re.compile(r'均价')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            if len(text) < 200:
                print(f"  [{parent.name}] {text}")

    # 搜索包含数字的元素
    print("\n--- 搜索价格相关元素 ---")
    price_elems = soup.select('[class*="price"], [class*="average"], [class*="number"]')
    for elem in price_elems[:20]:
        text = elem.get_text(strip=True)
        if text and len(text) < 100 and any(c.isdigit() for c in text):
            print(f"  [{elem.name}] class={elem.get('class')} : {text}")

    # 检查title
    title = soup.find('title')
    print(f"\n--- 页面标题: {title.get_text() if title else 'N/A'} ---")


def analyze_58_detail():
    """详细分析58同城页面"""
    print("\n\n=== 58同城详细结构分析 ===")
    r = requests.get('https://zhangjiagang.58.com/ershoufang/', headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 检查是否有反爬
    if 'verifycode' in html or 'antibot' in html:
        print("⚠️ 检测到反爬虫验证！")
        return

    # 查找包含价格的元素
    print("\n--- 包含'元'的元素 ---")
    count = 0
    for elem in soup.find_all(string=re.compile(r'元')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            if len(text) < 150 and any(c.isdigit() for c in text):
                print(f"  [{parent.name}] {text}")
                count += 1
                if count > 15:
                    break


if __name__ == '__main__':
    analyze_fang_detail()
    analyze_anjuke_detail()
    analyze_58_detail()
