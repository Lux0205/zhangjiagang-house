"""
深入分析各区域页面的完整结构
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_area_detail(area_name, url):
    """详细分析区域页面"""
    print(f"\n{'='*60}")
    print(f"=== {area_name} ({url}) ===")
    print(f"{'='*60}")
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"  状态码: {r.status_code}")
        return

    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 1. 区域均价
    print("\n--- 区域均价 ---")
    avg_match = re.search(r'二手房参考均价\s*</?\w+>\s*([\d,]+)\s*<', html)
    if not avg_match:
        avg_match = re.search(r'参考均价\s*</?\w+>\s*([\d,]+)\s*<', html)
    if avg_match:
        print(f"  二手房参考均价: {avg_match.group(1)} 元/平")

    # 搜索所有包含均价的文本
    for elem in soup.find_all(string=re.compile(r'参考均价')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            if len(text) < 200:
                print(f"  均价文本: {text}")

    # 2. 热门小区排行榜
    print("\n--- 热门小区排行榜 ---")
    # 搜索包含小区名+价格的结构
    rank_items = soup.select('[class*="rank"], [class*="list"], [class*="item"]')
    for item in rank_items[:5]:
        text = item.get_text(strip=True)
        if '元/平米' in text and len(text) < 300:
            print(f"  {text[:200]}")

    # 3. 直接搜索所有"参考价XXXX元/平米"
    print("\n--- 所有参考价 ---")
    ref_prices = re.findall(r'参考价\s*([\d,]+)\s*元/平米', html)
    print(f"  找到 {len(ref_prices)} 个参考价: {ref_prices[:20]}")

    # 4. 搜索小区名+价格组合
    print("\n--- 小区名+价格 ---")
    # 找到包含"参考价"的元素，获取其父元素中的小区名
    for elem in soup.find_all(string=re.compile(r'参考价')):
        parent = elem.parent
        if parent:
            # 往上找包含小区名的父元素
            for i in range(5):
                if parent.parent:
                    parent = parent.parent
                text = parent.get_text(strip=True)
                if len(text) > 10 and len(text) < 300:
                    # 检查是否包含数字
                    if re.search(r'\d{4,5}', text):
                        print(f"  {text[:200]}")
                    break

    # 5. 搜索所有包含"元/平米"的文本块
    print("\n--- 所有'元/平米'文本 ---")
    count = 0
    for elem in soup.find_all(string=re.compile(r'元/平米')):
        parent = elem.parent
        if parent:
            p2 = parent.parent
            if p2:
                text = p2.get_text(strip=True)
                if len(text) < 200:
                    print(f"  {text}")
                    count += 1
                    if count > 10:
                        break


def analyze_main_page_ranking():
    """分析主页热门小区排行榜的完整结构"""
    print(f"\n{'='*60}")
    print("=== 主页热门小区排行榜 ===")
    print(f"{'='*60}")
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 搜索排行榜容器
    print("\n--- 排行榜区域 ---")
    for elem in soup.find_all(string=re.compile(r'排行榜')):
        parent = elem.parent
        if parent:
            # 往上找包含多个小区的大容器
            for i in range(8):
                if parent.parent:
                    parent = parent.parent
                text = parent.get_text(strip=True)
                if len(text) > 200:
                    print(f"  父级{i+1} ({len(text)} 字符):")
                    print(f"  {text[:500]}")
                    print()
                    break

    # 用正则提取排行榜
    print("\n--- 排行榜小区提取 ---")
    # 模式: 数字+小区名+挂牌X套+参考价XXXXX元/平米
    pattern = r'(\d{1,2})\s*([^\d]+?)\s*挂牌(\d+)套\s*参考价([\d,]+)元/平米'
    matches = re.findall(pattern, html)
    if matches:
        for m in matches:
            print(f"  {m[0]}. {m[1].strip()} - 挂牌{m[2]}套 - {m[3]}元/平米")
    else:
        print("  正则未匹配，尝试其他模式")
        # 更宽松的模式
        pattern2 = r'参考价([\d,]+)元/平米'
        prices = re.findall(pattern2, html)
        print(f"  参考价列表: {prices}")


def analyze_area_navigation():
    """分析区域导航链接结构"""
    print(f"\n{'='*60}")
    print("=== 区域导航链接 ===")
    print(f"{'='*60}")
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, 'lxml')

    # 查找区域导航
    print("\n--- 区域导航链接 ---")
    area_links = {}
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if '二手房房价' in text and '/zjg/' in href:
            area_links[text.replace('二手房房价', '').strip()] = href

    for area, href in area_links.items():
        print(f"  {area}: {href}")

    return area_links


if __name__ == '__main__':
    # 分析各区域页面
    analyze_area_detail('金港', 'http://fangjia.fang.com/zjg/a017470-b019124/')
    analyze_area_detail('塘桥', 'http://fangjia.fang.com/zjg/a017470-b019130/')
    analyze_area_detail('凤凰', 'http://fangjia.fang.com/zjg/a017470-b019133/')

    # 分析主页排行榜
    analyze_main_page_ranking()

    # 分析区域导航
    analyze_area_navigation()
