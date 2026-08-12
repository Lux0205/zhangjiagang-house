"""
修复市中心和常阴沙的均价提取
"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def analyze_shizhongxin():
    """分析市中心页面结构"""
    url = 'http://fangjia.fang.com/zjg/a017470-b030568/'
    r = requests.get(url, headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    print("=== 市中心页面分析 ===")
    print(f"标题: {soup.find('title').get_text() if soup.find('title') else 'N/A'}")

    # 搜索所有包含"参考均价"或"均价"的元素
    print("\n--- 均价相关元素 ---")
    for elem in soup.find_all(string=re.compile(r'均价')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            if len(text) < 200:
                print(f"  [{parent.name}] {text}")

    # 搜索所有 <em> 标签
    print("\n--- 所有 <em> 标签 ---")
    for em in soup.select('em'):
        text = em.get_text(strip=True)
        if text:
            print(f"  {text}")

    # 搜索包含数字+元/平的文本
    print("\n--- 包含'元/平'的文本 ---")
    for elem in soup.find_all(string=re.compile(r'元/平')):
        parent = elem.parent
        if parent:
            p2 = parent.parent
            if p2:
                text = p2.get_text(strip=True)
                if len(text) < 200:
                    print(f"  {text}")

    # 搜索包含"参考"的div
    print("\n--- 包含'参考'的div ---")
    for div in soup.select('div'):
        text = div.get_text(strip=True)
        if '参考' in text and '价格' in text and len(text) < 300:
            print(f"  {text}")


def analyze_changyinsha():
    """分析常阴沙页面结构"""
    url = 'http://fangjia.fang.com/zjg/a017470-b019138/'
    r = requests.get(url, headers=headers, timeout=15)
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    print("\n\n=== 常阴沙页面分析 ===")
    print(f"标题: {soup.find('title').get_text() if soup.find('title') else 'N/A'}")
    print(f"长度: {len(html)}")

    # 检查是否和市中心是同一页面
    if '市中心' in html:
        print("  ⚠️ 常阴沙页面显示的是市中心内容")

    # 搜索均价
    print("\n--- 均价相关元素 ---")
    for elem in soup.find_all(string=re.compile(r'均价')):
        parent = elem.parent
        if parent:
            text = parent.get_text(strip=True)
            if len(text) < 200:
                print(f"  [{parent.name}] {text}")


if __name__ == '__main__':
    analyze_shizhongxin()
    analyze_changyinsha()
