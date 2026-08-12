"""
深入分析房天下 — 找出区域名与价格的对应关系
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_fang_structure():
    """分析房天下的完整DOM结构"""
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 1. 查找区域列表结构
    print("=== 查找区域列表 ===")
    # 尝试多种选择器
    selectors = [
        '.house', '.region', '.district', '.area', '.place',
        '.list', '.item', '.info',
        '[class*="region"]', '[class*="district"]',
        '[class*="area"]', '[class*="house"]',
    ]
    for sel in selectors:
        elems = soup.select(sel)
        if elems:
            print(f"\n  选择器 {sel}: {len(elems)} 个元素")
            for e in elems[:3]:
                text = e.get_text(strip=True)[:150]
                print(f"    class={e.get('class')} : {text}")

    # 2. 找到包含区域名的所有元素
    print("\n=== 包含区域名的元素 ===")
    area_names = ['杨舍', '塘桥', '金港', '后塍', '德积', '锦丰', '凤凰', '乐余', '南丰', '大新',
                  '步行街', '人民路', '长安路']
    for area in area_names:
        for elem in soup.find_all(string=re.compile(re.escape(area))):
            parent = elem.parent
            if parent:
                # 往上找3层
                granpa = parent.parent
                great_granpa = granpa.parent if granpa else None
                context = (great_granpa or granpa or parent).get_text(strip=True)
                if len(context) < 300:
                    print(f"  [{area}] {context[:200]}")
                    break

    # 3. 分析价格列表结构 - 找到价格对应的父容器
    print("\n=== 价格元素结构分析 ===")
    price_spans = soup.select('[class*="price"]')
    for span in price_spans[:10]:
        # 往上找父元素
        p1 = span.parent
        p2 = p1.parent if p1 else None
        p3 = p2.parent if p2 else None
        p4 = p3.parent if p3 else None

        span_text = span.get_text(strip=True)
        p2_text = p2.get_text(strip=True)[:200] if p2 else ''
        p3_text = p3.get_text(strip=True)[:200] if p3 else ''
        p4_text = p4.get_text(strip=True)[:300] if p4 else ''

        print(f"\n  span: {span_text}")
        print(f"  p2: {p2_text}")
        print(f"  p3: {p3_text}")
        print(f"  p4: {p4_text}")

    # 4. 查找"元/平米"的完整上下文
    print("\n=== '元/平米' 完整上下文 ===")
    for elem in soup.find_all(string=re.compile(r'元/平米')):
        parent = elem.parent
        if parent:
            p2 = parent.parent
            if p2:
                text = p2.get_text(strip=True)
                print(f"  {text[:200]}")


if __name__ == '__main__':
    analyze_fang_structure()
