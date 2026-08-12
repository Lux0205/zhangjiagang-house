"""
分析房天下价格数据的实际HTML结构
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_price_html():
    """分析价格数据的实际HTML结构"""
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text

    # 找到"参考均价"附近的完整HTML
    print("=== '参考均价' 附近HTML ===")
    idx = html.find('参考均价')
    if idx >= 0:
        # 找到包含这个文本的最小标签
        start = max(0, idx - 500)
        end = min(len(html), idx + 500)
        snippet = html[start:end]

        # 用BeautifulSoup解析
        soup = BeautifulSoup(snippet, 'lxml')
        print(f"文本: {soup.get_text(strip=True)[:300]}")
        print(f"\n原始HTML:\n{snippet}")

    # 搜索包含"9153"的HTML
    print("\n\n=== 包含 '9153' 的HTML ===")
    idx = html.find('9153')
    if idx >= 0:
        start = max(0, idx - 300)
        end = min(len(html), idx + 300)
        snippet = html[start:end]
        print(f"HTML片段:\n{snippet}")

    # 搜索包含"元/平"的HTML
    print("\n\n=== 包含 '元/平' 的HTML ===")
    for match in re.finditer(r'.{0,100}元/平.{0,100}', html):
        print(f"  {match.group()}")
        break  # 只打印第一个

    # 搜索包含"参考价"和数字的HTML
    print("\n\n=== '参考价' 附近HTML ===")
    for match in re.finditer(r'.{0,200}参考价.{0,200}', html):
        text = match.group()
        if '元' in text:
            print(f"  {text[:300]}")
            print("  ---")
            break


def analyze_area_price_html():
    """分析区域页面价格HTML"""
    print("\n\n=== 金港区域页面价格HTML ===")
    r = requests.get('http://fangjia.fang.com/zjg/a017470-b019124/', headers=headers, timeout=15)
    html = r.text

    # 搜索"9349"附近的HTML
    for target in ['9349', '9390', '9500']:
        idx = html.find(target)
        if idx >= 0:
            start = max(0, idx - 200)
            end = min(len(html), idx + 200)
            print(f"\n  包含 '{target}' 的HTML:")
            print(f"  {html[start:end]}")
            break

    # 搜索"参考均价"附近的HTML
    print("\n  '参考均价' 附近HTML:")
    idx = html.find('参考均价')
    if idx >= 0:
        start = max(0, idx - 300)
        end = min(len(html), idx + 300)
        print(f"  {html[start:end]}")


if __name__ == '__main__':
    analyze_price_html()
    analyze_area_price_html()
