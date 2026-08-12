"""
分析房天下各区域页面URL结构和租房页面
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_area_pages():
    """分析各区域房价页面的URL"""
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    # 查找所有区域链接
    print("=== 各区域房价页面链接 ===")
    area_keywords = ['金港', '锦丰', '塘桥', '凤凰', '大新', '乐余', '南丰', '后塍', '德积',
                     '市中心', '城东', '城西', '城南', '城北', '杨舍']

    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if any(kw in text for kw in area_keywords) and ('fangjia' in href or 'zjg' in href):
            print(f"  {text}: {href}")

    # 搜索所有含"房价"的链接
    print("\n=== 含'房价'的链接 ===")
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if '房价' in text:
            print(f"  {text}: {href}")


def analyze_rent_page():
    """分析房天下租房页面"""
    print("\n\n=== 房天下租房页面 ===")
    # 张家港租房页面
    urls = [
        'http://zu.fang.com/zjg/',
        'http://zhangjiagang.zu.fang.com/',
        'http://fangjia.fang.com/zjg/rent/',
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"\n  URL: {url}")
            print(f"  状态码: {r.status_code}, 长度: {len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('title')
                print(f"  标题: {title.get_text() if title else 'N/A'}")
                # 搜索价格
                prices = re.findall(r'([\d,]+)\s*元', r.text)
                print(f"  价格: {prices[:10]}")
        except Exception as e:
            print(f"  错误: {e}")


def analyze_area_detail():
    """分析具体区域页面（塘桥）的结构"""
    print("\n\n=== 塘桥区域页面分析 ===")
    # 尝试几种URL模式
    urls = [
        'http://fangjia.fang.com/zjg/tangqiao/',
        'http://tangqiao.fangjia.fang.com/',
        'http://fangjia.fang.com/tangqiao/',
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"\n  URL: {url}")
            print(f"  状态码: {r.status_code}, 长度: {len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('title')
                print(f"  标题: {title.get_text() if title else 'N/A'}")
                # 搜索小区均价
                matches = re.findall(r'([\d,]+)\s*元/平', r.text)
                print(f"  元/平: {matches[:10]}")
                # 搜索小区名+价格
                for elem in soup.find_all(string=re.compile(r'元/平米')):
                    parent = elem.parent
                    if parent:
                        p2 = parent.parent
                        if p2:
                            text = p2.get_text(strip=True)
                            if len(text) < 200:
                                print(f"  {text}")
                                break
                break
        except Exception as e:
            print(f"  错误: {e}")


def analyze_quanjing():
    """分析房天下'全城'均价数据的提取方式"""
    print("\n\n=== 全城均价提取 ===")
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text

    # 提取全市二手房均价
    # 已知模式: "二手房参考均价9153元/平"
    esc_match = re.search(r'二手房参考均价\s*([\d,]+)\s*元/平', html)
    if esc_match:
        print(f"  二手房参考均价: {esc_match.group(1)} 元/平")

    # 提取新房均价
    new_match = re.search(r'新房参考均价\s*([\d,]+)\s*元/平', html)
    if new_match:
        print(f"  新房参考均价: {new_match.group(1)} 元/平")

    # 提取热门小区排行榜
    print("\n  热门小区排行榜:")
    # 模式: 数字+小区名+挂牌X套+参考价XXXXX元/平米
    rank_pattern = r'(\d+)\s*([^\d]+?)\s*挂牌(\d+)套\s*参考价([\d,]+)元/平米'
    for m in re.finditer(rank_pattern, html):
        print(f"    {m.group(1)}. {m.group(2).strip()} - 挂牌{m.group(3)}套 - {m.group(4)}元/平米")


if __name__ == '__main__':
    analyze_area_pages()
    analyze_rent_page()
    analyze_area_detail()
    analyze_quanjing()
