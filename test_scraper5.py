"""
分析房天下各区域页面和租房页面的完整结构
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_area_page(area_name, url):
    """分析单个区域页面"""
    print(f"\n=== {area_name} ({url}) ===")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"  状态码: {r.status_code}")
            return
        html = r.text
        soup = BeautifulSoup(html, 'lxml')
        title = soup.find('title')
        print(f"  标题: {title.get_text() if title else 'N/A'}")
        print(f"  长度: {len(html)}")

        # 搜索区域均价
        avg_match = re.search(r'二手房参考均价\s*([\d,]+)\s*元/平', html)
        if avg_match:
            print(f"  二手房参考均价: {avg_match.group(1)} 元/平")

        # 搜索热门小区排行榜
        rank_pattern = r'(\d+)\s*([^\d]+?)\s*挂牌(\d+)套\s*参考价([\d,]+)元/平米'
        ranks = re.findall(rank_pattern, html)
        if ranks:
            print(f"  热门小区 ({len(ranks)} 个):")
            for r in ranks[:5]:
                print(f"    {r[0]}. {r[1].strip()} - {r[3]}元/平米")

        # 搜索所有小区均价
        prices = re.findall(r'([\d,]+)\s*元/平', html)
        print(f"  所有元/平价格: {prices[:15]}")

        # 搜索小区名+价格组合
        for elem in soup.find_all(string=re.compile(r'参考价')):
            parent = elem.parent
            if parent:
                text = parent.get_text(strip=True)
                if len(text) < 200:
                    print(f"  参考价元素: {text[:150]}")
                    break

    except Exception as e:
        print(f"  错误: {e}")


def analyze_rent_page():
    """分析租房页面"""
    print("\n\n=== 房天下租房页面 ===")
    url = 'http://zu.fang.com/zjg/'
    r = requests.get(url, headers=headers, timeout=15)
    print(f"状态码: {r.status_code}, 长度: {len(r.text)}")
    print(f"内容:\n{r.text[:2000]}")


def analyze_rent_area_pages():
    """分析各区域租房页面"""
    print("\n\n=== 分析各区域租房页面 ===")
    # 从主页获取租房区域链接
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, 'lxml')

    # 查找租房相关链接
    rent_links = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if '租' in text and ('fang' in href or 'zu' in href):
            rent_links.append((text, href))

    print(f"租房相关链接: {len(rent_links)}")
    for text, href in rent_links[:20]:
        print(f"  {text}: {href}")

    # 尝试直接访问租房区域页面
    area_codes = {
        '金港': 'http://zu.fang.com/zjg/a017470-b019124/',
        '塘桥': 'http://zu.fang.com/zjg/a017470-b019130/',
        '凤凰': 'http://zu.fang.com/zjg/a017470-b019133/',
        '市中心': 'http://zu.fang.com/zjg/a017470-b030568/',
    }
    for area, url in area_codes.items():
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"\n  {area} 租房: 状态码={r.status_code}, 长度={len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                prices = re.findall(r'([\d,]+)\s*元', r.text)
                print(f"    价格: {prices[:10]}")
        except Exception as e:
            print(f"  {area} 租房错误: {e}")


def analyze_citywide_data():
    """分析全市均价数据提取"""
    print("\n\n=== 全市均价数据提取 ===")
    r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
    html = r.text

    # 提取均价 - 多种模式
    patterns = [
        r'二手房参考均价\s*</?\w+>\s*([\d,]+)\s*<',
        r'二手房参考均价\s*<[^>]+>\s*([\d,]+)',
        r'参考均价\s*<[^>]+>\s*([\d,]+)\s*<',
        r'均价\s*<[^>]+>\s*([\d,]+)\s*<',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            print(f"  模式匹配: {pat[:40]}... -> {m.group(1)}")

    # 直接用BeautifulSoup搜索
    soup = BeautifulSoup(html, 'lxml')
    for elem in soup.find_all(string=re.compile(r'参考均价')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            print(f"  参考均价文本: {text[:100]}")
            # 往上找包含数字的
            for i in range(5):
                parent = parent.parent if parent.parent else parent
                text = parent.get_text(strip=True)
                numbers = re.findall(r'[\d,]+', text)
                if numbers:
                    print(f"    父级{i+1}: {text[:150]}")
                    break

    # 提取热门小区排行榜 - 用BeautifulSoup
    print("\n  热门小区排行榜 (DOM):")
    # 搜索包含"参考价"和"元/平米"的元素
    for elem in soup.find_all(string=re.compile(r'参考价')):
        parent = elem.parent
        if parent:
            p2 = parent.parent
            if p2:
                text = p2.get_text(strip=True)
                if '元/平米' in text and len(text) < 200:
                    print(f"    {text}")


if __name__ == '__main__':
    # 分析各区域页面
    analyze_area_page('金港', 'http://fangjia.fang.com/zjg/a017470-b019124/')
    analyze_area_page('塘桥', 'http://fangjia.fang.com/zjg/a017470-b019130/')
    analyze_area_page('凤凰', 'http://fangjia.fang.com/zjg/a017470-b019133/')
    analyze_area_page('市中心', 'http://fangjia.fang.com/zjg/a017470-b030568/')

    # 分析租房页面
    analyze_rent_page()
    analyze_rent_area_pages()

    # 分析全市均价
    analyze_citywide_data()
