"""
测试各网站的可抓取性 — 分析页面结构
"""
import requests
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def test_fangtianxia():
    """测试房天下张家港房价页"""
    print("\n" + "="*60)
    print("=== 房天下 fangjia.fang.com/zjg/ ===")
    print("="*60)
    try:
        r = requests.get('http://fangjia.fang.com/zjg/', headers=headers, timeout=15)
        print(f"状态码: {r.status_code}, 长度: {len(r.text)}")
        if r.status_code != 200:
            return

        html = r.text

        # 搜索所有价格模式
        print("\n--- 价格模式搜索 ---")
        patterns = [
            (r'均价[：:]?\s*([\d,]+)\s*元', "均价+元"),
            (r'([\d,]+)\s*元/㎡', "元/㎡"),
            (r'([\d,]+)\s*元/平', "元/平"),
        ]
        for pat, label in patterns:
            matches = re.findall(pat, html)
            if matches:
                print(f"  [{label}] 找到 {len(matches)} 个: {matches[:15]}")

        # 搜索区域名附近的房价
        print("\n--- 区域+价格关联 ---")
        areas = ['杨舍', '塘桥', '金港', '后塍', '德积', '锦丰', '凤凰', '乐余', '南丰', '大新']
        for area in areas:
            idx = html.find(area)
            if idx >= 0:
                snippet = html[max(0,idx-200):idx+300]
                prices = re.findall(r'([\d,]+)\s*元', snippet)
                if prices:
                    print(f"  {area}: 价格 {prices[:5]}")

        # 尝试提取script中的json数据
        print("\n--- 搜索JSON数据 ---")
        json_patterns = [
            r'var\s+\w+\s*=\s*(\{.*?\});',
            r'"price":\s*"?(\d+)"?',
            r'"avgPrice":\s*"?(\d+)"?',
            r'"data":\s*(\[.*?\])',
        ]
        for pat in json_patterns:
            matches = re.findall(pat, html[:50000])
            if matches:
                print(f"  模式 {pat[:30]}...: 找到 {len(matches)} 个")
                for m in matches[:3]:
                    print(f"    {m[:200]}")

        # 检查是否包含动态加载标志
        if 'ajax' in html.lower() or 'load' in html.lower():
            print("\n  提示: 页面可能使用AJAX动态加载")

    except Exception as e:
        print(f"错误: {e}")


def test_anjuke():
    """测试安居客张家港房价页"""
    print("\n" + "="*60)
    print("=== 安居客 m.anjuke.com ===")
    print("="*60)
    try:
        # 安居客PC版
        r = requests.get('https://www.anjuke.com/fangjia/zhangjiagang/', headers=headers, timeout=15)
        print(f"PC版状态码: {r.status_code}, 长度: {len(r.text)}")
        if r.status_code == 200:
            # 搜索价格
            prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
            print(f"PC版 元/㎡ 价格: {prices[:10]}")

            # 区域均价
            idx = r.text.find('均价')
            if idx >= 0:
                print(f"均价附近: {r.text[idx:idx+200]}")
        else:
            print(f"PC版返回: {r.text[:300]}")
    except Exception as e:
        print(f"错误: {e}")


def test_58():
    """测试58同城张家港二手房"""
    print("\n" + "="*60)
    print("=== 58同城 zhangjiagang.58.com ===")
    print("="*60)
    try:
        r = requests.get('https://zhangjiagang.58.com/ershoufang/', headers=headers, timeout=15)
        print(f"状态码: {r.status_code}, 长度: {len(r.text)}")
        if r.status_code == 200:
            prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
            print(f"元/㎡ 价格: {prices[:10]}")
            # 区域均价
            avg_prices = re.findall(r'均价[：:]?\s*([\d,]+)', r.text)
            print(f"均价: {avg_prices[:10]}")
            # 检查是否有反爬
            if 'verifycode' in r.text or 'antibot' in r.text:
                print("⚠️ 检测到反爬虫验证！")
        else:
            print(f"返回: {r.text[:300]}")
    except Exception as e:
        print(f"错误: {e}")


def test_beike():
    """测试贝壳找房张家港"""
    print("\n" + "="*60)
    print("=== 贝壳找房 su.ke.com ===")
    print("="*60)
    try:
        r = requests.get('https://su.ke.com/ershoufang/zhangjiagang/', headers=headers, timeout=15)
        print(f"状态码: {r.status_code}, 长度: {len(r.text)}")
        if r.status_code == 200:
            prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
            print(f"元/㎡ 价格: {prices[:10]}")
            # 检查是否JS渲染
            if len(r.text) < 5000 or 'loading' in r.text.lower():
                print("⚠️ 页面可能需要JS渲染")
        else:
            print(f"返回: {r.text[:300]}")
    except Exception as e:
        print(f"错误: {e}")


def test_zjgzf():
    """测试张家港房产网"""
    print("\n" + "="*60)
    print("=== 张家港房产网 zjgzf.cn ===")
    print("="*60)
    try:
        r = requests.get('http://www.zjgzf.cn/', headers=headers, timeout=15)
        print(f"状态码: {r.status_code}, 长度: {len(r.text)}")
        if r.status_code == 200:
            prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
            print(f"元/㎡ 价格: {prices[:10]}")
        else:
            print(f"返回: {r.text[:300]}")
    except Exception as e:
        print(f"错误: {e}")


def test_lianjia():
    """测试链家张家港"""
    print("\n" + "="*60)
    print("=== 链家 su.lianjia.com ===")
    print("="*60)
    try:
        r = requests.get('https://su.lianjia.com/ershoufang/zhangjiagang/', headers=headers, timeout=15)
        print(f"状态码: {r.status_code}, 长度: {len(r.text)}")
        if r.status_code == 200:
            prices = re.findall(r'([\d,]+)\s*元/㎡', r.text)
            print(f"元/㎡ 价格: {prices[:10]}")
            if len(r.text) < 5000:
                print("⚠️ 页面可能需要JS渲染")
        else:
            print(f"返回: {r.text[:300]}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == '__main__':
    test_fangtianxia()
    test_anjuke()
    test_58()
    test_beike()
    test_zjgzf()
    test_lianjia()
