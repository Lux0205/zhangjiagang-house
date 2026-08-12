"""
获取房天下所有区域的均价数据
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


def get_area_avg_price(area_name, code):
    """获取单个区域的均价"""
    url = f'http://fangjia.fang.com/zjg/{code}/'
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, None

        html = r.text

        # 提取二手房参考均价
        # 模式: "八月参考均价9349元/平" 或 "参考均价XXXX元/平"
        esc_price = None
        new_price = None

        # 搜索所有"参考均价"附近的数字
        for match in re.finditer(r'参考均价\s*([\d,]+)\s*元/平', html):
            price = float(match.group(1).replace(',', ''))
            if 3000 <= price <= 50000:
                if esc_price is None:
                    esc_price = price
                elif new_price is None:
                    new_price = price
                    break

        # 如果只找到一个，尝试其他模式
        if esc_price is None:
            match = re.search(r'八月参考均价\s*([\d,]+)\s*元/平', html)
            if match:
                esc_price = float(match.group(1).replace(',', ''))

        return esc_price, new_price

    except Exception as e:
        print(f"  错误: {e}")
        return None, None


def get_citywide_price():
    """获取全市均价"""
    url = 'http://fangjia.fang.com/zjg/'
    r = requests.get(url, headers=headers, timeout=15)
    html = r.text

    esc_price = None
    new_price = None

    # 二手房参考均价
    match = re.search(r'二手房参考均价\s*([\d,]+)\s*元/平', html)
    if match:
        esc_price = float(match.group(1).replace(',', ''))

    # 新房参考均价
    match = re.search(r'新房参考均价\s*([\d,]+)\s*元/平', html)
    if match:
        new_price = float(match.group(1).replace(',', ''))

    return esc_price, new_price


def get_community_ranking():
    """获取热门小区排行榜"""
    url = 'http://fangjia.fang.com/zjg/'
    r = requests.get(url, headers=headers, timeout=15)
    html = r.text

    # 提取排行榜: 数字+小区名+挂牌X套+参考价XXXX元/平米
    pattern = r'(\d{1,2})\s*([^\d]+?)\s*挂牌(\d+)套\s*参考价([\d,]+)元/平米'
    matches = re.findall(pattern, html)

    ranking = []
    for m in matches:
        ranking.append({
            'rank': int(m[0]),
            'community': m[1].strip(),
            'listing_count': int(m[2]),
            'price': float(m[3].replace(',', '')),
        })

    return ranking


if __name__ == '__main__':
    print("=== 全市均价 ===")
    esc, new = get_citywide_price()
    print(f"  二手房参考均价: {esc} 元/平")
    print(f"  新房参考均价: {new} 元/平")

    print("\n=== 各区域均价 ===")
    area_prices = {}
    for area_name, code in AREA_CODES.items():
        esc, new = get_area_avg_price(area_name, code)
        area_prices[area_name] = {'ershou': esc, 'xin': new}
        print(f"  {area_name}: 二手房 {esc} 元/平, 新房 {new} 元/平")

    print("\n=== 热门小区排行榜 ===")
    ranking = get_community_ranking()
    for r in ranking:
        print(f"  {r['rank']}. {r['community']} - 挂牌{r['listing_count']}套 - {r['price']}元/平米")
