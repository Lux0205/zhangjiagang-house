# 自动生成中文注释技能

## 技能说明

当用户要求给代码添加、补全、整理注释时，激活此技能。所有注释必须使用中文，变量名保持英文。

---

## 触发条件

用户说了以下任何一句话时，使用此技能：
- "给这段代码加注释"
- "帮我补全注释"
- "整理一下注释"
- "添加中文注释"
- "这代码看能不能加下说明"
- 任何明确表达"要给代码加注释"的请求

---

## 执行规则

### 1. 函数/方法注释

每个函数（function）和方法（method）必须有 docstring，格式如下：

```python
def calculate_average(prices):
    """
    计算列表里所有数字的平均值。

    参数：
        prices (list): 一个包含数字的列表。

    返回：
        float: 所有数字的平均值。
    """
```

docstring 必须包含三个部分：
- **一句话说明**函数做什么
- **参数**：每个参数的名字、类型、含义
- **返回**：返回值的类型和含义

### 2. 关键逻辑注释

遇到以下情况，必须加行内中文注释（`#` 开头的单行注释）：

- 容易让人看不懂的代码（比如复杂计算、奇怪的条件判断）
- 涉及业务规则的地方（比如"满 100 减 20"需要说明这是促销规则）
- 临时性的 workaround 或 TODO
- 数据来源的说明（比如"从安居客网页抓取"）

注释加在该行代码的上方，空一行隔开其他代码。

```python
# 安居客的每页有 30 条数据，所以偏移量要乘以 30
offset = page * 30
```

### 3. 变量名规则

- 变量名保持 **英文**（拼音也算英文，但尽量不用拼音）
- 如果用英文缩写，第一次出现时加注释说明含义

```python
total_avg = 0  # total average 的缩写，记录总平均值
```

### 4. 不需要加注释的情况

- 一看就懂的代码，比如 `x = 1`、`return result`
- 重复代码已有的说明（不要为了加注释而加注释）

---

## 执行步骤

当用户要求加注释时，按以下顺序操作：

1. 通读全部代码，理解模块的整体逻辑
2. 先给每个函数补全 docstring
3. 再扫描需要加行内注释的地方
4. 最后检查一遍，确保没有遗漏

---

## 针对不同语言的风格

### Python（本项目的主要语言）
- docstring 用三引号（`"""`）
- 行内注释用 `#`

### JavaScript / TypeScript
- 多行注释用 `/** ... */`
- 行内注释用 `//`

### HTML
- 注释用 `<!-- ... -->`

---

## 示例

### ❌ 修改前的代码

```python
def get_price(url, page):
    resp = requests.get(url, params={"p": page})
    data = resp.json()
    items = data["list"]
    result = []
    for item in items:
        price = int(item["total"]) / int(item["size"])
        result.append(round(price, 2))
    return result
```

### ✅ 修改后的代码

```python
def get_price(url, page):
    """
    抓取指定页面的房价数据，并换算成每平米单价。

    参数：
        url (str): 数据接口的 URL 地址。
        page (int): 要抓取的页码，从 1 开始。

    返回：
        list[float]: 每平米的单价列表，保留两位小数。
    """
    resp = requests.get(url, params={"p": page})
    data = resp.json()

    # "list" 字段包含当前页的所有房源信息
    items = data["list"]

    result = []
    for item in items:
        # 总价除以面积，得到每平米的单价
        price = int(item["total"]) / int(item["size"])
        result.append(round(price, 2))

    return result
```

---

## 注意事项

- 只改注释部分，不要改动任何原有的代码逻辑
- 如果代码本身有 bug，先告诉用户，等确认后再改动
- 批量的注释添加，一次不要超过 200 行代码，避免遗漏
