"""
测试安居客和其他网站的租房页面
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def test_anjuke_rent():
    """测试安居客租房页面"""
    print("=== 安居客租房 ===")
    urls = [
        'https://www.anjuke.com/fangjia/zhangjiagang/rent/',
        'https://zhangjiagang.anjuke.com/rent/',
        'https://m.anjuke.com/su/rent/zhangjiagang/',
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"\n  URL: {url}")
            print(f"  状态码: {r.status_code}, 长度: {len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('title')
                print(f"  标题: {title.get_text() if title else 'N/A'}")
                # 检查反爬
                if 'verifycode' in r.text or 'antibot' in r.text:
                    print("  ⚠️ 反爬虫验证")
                else:
                    prices = re.findall(r'([\d,]+)\s*元', r.text)
                    print(f"  价格: {prices[:10]}")
            else:
                print(f"  内容: {r.text[:200]}")
        except Exception as e:
            print(f"  错误: {e}")


def test_58_rent():
    """测试58同城租房页面"""
    print("\n\n=== 58同城租房 ===")
    urls = [
        'https://zhangjiagang.58.com/chuzu/',
        'https://zhangjiagang.58.com/zufang/',
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"\n  URL: {url}")
            print(f"  状态码: {r.status_code}, 长度: {len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('title')
                print(f"  标题: {title.get_text() if title else 'N/A'}")
                if 'verifycode' in r.text or 'antibot' in r.text:
                    print("  ⚠️ 反爬虫验证")
                else:
                    prices = re.findall(r'([\d,]+)\s*元', r.text)
                    print(f"  价格: {prices[:10]}")
            else:
                print(f"  内容: {r.text[:200]}")
        except Exception as e:
            print(f"  错误: {e}")


def test_anjuke_buy():
    """测试安居客买房页面 - 找正确的URL"""
    print("\n\n=== 安居客买房 ===")
    urls = [
        'https://www.anjuke.com/fangjia/zhangjiagang/',
        'https://www.anjuke.com/fangjia/zhangjiagang2026/',
        'https://zhangjiagang.anjuke.com/market/',
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"\n  URL: {url}")
            print(f"  状态码: {r.status_code}, 长度: {len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('title')
                print(f"  标题: {title.get_text() if title else 'N/A'}")
                if 'verifycode' in r.text or 'antibot' in r.text:
                    print("  ⚠️ 反爬虫验证")
                else:
                    prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
                    print(f"  元/㎡价格: {prices[:10]}")
                    # 搜索均价
                    avg = re.findall(r'均价\s*<[^>]+>\s*([\d,]+)', r.text)
                    print(f"  均价: {avg[:5]}")
            else:
                print(f"  内容: {r.text[:200]}")
        except Exception as e:
            print(f"  错误: {e}")


def test_zjgzf_buy():
    """测试张家港房产网买房数据"""
    print("\n\n=== 张家港房产网 ===")
    urls = [
        'http://www.zjgzf.cn/',
        'http://www.zjgzf.cn/fangjia/',
        'http://www.zjgzf.cn/price/',
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"\n  URL: {url}")
            print(f"  状态码: {r.status_code}, 长度: {len(r.text)}")
            if r.status_code == 200 and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, 'lxml')
                title = soup.find('title')
                print(f"  标题: {title.get_text() if title else 'N/A'}")
                prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
                print(f"  元/㎡价格: {prices[:10]}")
        except Exception as e:
            print(f"  错误: {e}")


if __name__ == '__main__':
    test_anjuke_rent()
    test_58_rent()
    test_anjuke_buy()
    test_zjgzf_buy()
