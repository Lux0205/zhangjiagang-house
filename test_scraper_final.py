"""
房天下爬虫 — 正式测试
提取全市均价、各区域均价、热门小区排行榜
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 区域代码映射
AREA_CODES = {
    '市中心': 'a017470-b030568',
    '城东': 'a017470-b022634',
    '城西': 'a017470-b022633',
    '城南': 'a017470-b022635',
    '城北': 'a017470-b022636',
    '金港': 'a017470-b019124',
    '锦丰': 'a017470-b019127',
    '塘桥': 'a017470-b019130',
    '凤凰': 'a017470-b019133',
    '大新': 'a017470-b019135',
    '乐余': 'a017470-b019136',
    '南丰': 'a017470-b019137',
    '常阴沙': 'a017470-b019138',
}


def get_citywide_price():
    """获取全市均价"""
    url = 'http://fangjia.fang.com/zjg/'
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, 'lxml')

    result = {}
    # 二手房均价
    for li in soup.select('li.title_num'):
        text = li.get_text(strip=True)
        if '元/平' in text:
            num = re.search(r'([\d,]+)', text)
            if num:
                price = float(num.group(1).replace(',', ''))
                if '二手房' in str(li.find_previous()):
                    result['ershou'] = price
                elif '新房' in str(li.find_previous()):
                    result['xin'] = price
                else:
                    if 'ershou' not in result:
                        result['ershou'] = price
                    elif 'xin' not in result:
                        result['xin'] = price

    # 更精确的方式：找包含"二手房参考均价"的ul
    for ul in soup.select('ul'):
        text = ul.get_text(strip=True)
        if '二手房参考均价' in text or '八月二手房' in text:
            nums = re.findall(r'([\d,]+)\s*元/平', text)
            if nums:
                result['ershou'] = float(nums[0].replace(',', ''))
        if '新房参考均价' in text or '八月新房' in text:
            nums = re.findall(r'([\d,]+)\s*元/平', text)
            if nums:
                result['xin'] = float(nums[0].replace(',', ''))

    return result


def get_area_price(area_name, code):
    """获取单个区域的均价"""
    url = f'http://fangjia.fang.com/zjg/{code}/'
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, 'lxml')

    result = {}

    # 方式1: 找 <em> 标签中的数字
    for em in soup.select('em'):
        text = em.get_text(strip=True)
        if re.match(r'^[\d,]+$', text):
            price = float(text.replace(',', ''))
            if 3000 <= price <= 50000:
                if 'ershou' not in result:
                    result['ershou'] = price
                elif 'xin' not in result:
                    result['xin'] = price

    # 方式2: 找包含"八月参考均价"的元素
    if not result:
        for elem in soup.find_all(string=re.compile(r'八月参考均价')):
            parent = elem.parent
            if parent:
                granpa = parent.parent
                if granpa:
                    nums = re.findall(r'([\d,]+)\s*元/平', granpa.get_text())
                    if nums:
                        result['ershou'] = float(nums[0].replace(',', ''))

    return result


def get_community_ranking():
    """获取热门小区排行榜"""
    url = 'http://fangjia.fang.com/zjg/'
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, 'lxml')

    ranking = []

    # 排行榜结构: <dl> 包含 <dt>排名</dt> 和 <dd>小区信息</dd>
    for dl in soup.select('dl.clearfix'):
        dt = dl.select_one('dt')
        dd = dl.select_one('dd')
        if not dt or not dd:
            continue

        rank_text = dt.get_text(strip=True)
        if not rank_text.isdigit():
            continue

        # 小区名
        name_elem = dd.select_one('a')
        community_name = name_elem.get_text(strip=True) if name_elem else ''

        # 挂牌数
        listing_elem = dd.select_one('.pm-price')
        listing_text = listing_elem.get_text(strip=True) if listing_elem else ''
        listing_match = re.search(r'(\d+)', listing_text)
        listing_count = int(listing_match.group(1)) if listing_match else 0

        # 参考价
        price_elem = dd.select_one('.pm-rate')
        price_text = price_elem.get_text(strip=True) if price_elem else ''
        price_match = re.search(r'([\d,]+)', price_text)
        price = float(price_match.group(1).replace(',', '')) if price_match else 0

        if community_name and price > 0:
            ranking.append({
                'rank': int(rank_text),
                'community': community_name,
                'listing_count': listing_count,
                'price': price,
            })

    return ranking


if __name__ == '__main__':
    print("=== 全市均价 ===")
    city = get_citywide_price()
    print(f"  二手房: {city.get('ershou')} 元/平")
    print(f"  新房: {city.get('xin')} 元/平")

    print("\n=== 各区域均价 ===")
    for area_name, code in AREA_CODES.items():
        prices = get_area_price(area_name, code)
        print(f"  {area_name}: 二手房 {prices.get('ershou')} 元/平, 新房 {prices.get('xin')} 元/平")

    print("\n=== 热门小区排行榜 ===")
    ranking = get_community_ranking()
    for r in ranking:
        print(f"  {r['rank']}. {r['community']} - 挂牌{r['listing_count']}套 - {r['price']}元/平米")
