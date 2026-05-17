# 基金周度涨跌幅工具 - 设计文档

## 概述

国内基金每周涨跌幅查询工具，支持按基金代码搜索、自定义时间段周度涨跌幅、同分类全市场排名、基金分类展示。

## 架构

```
定时任务 (爬虫)
    │
    │  每周爬取
    ▼
MySQL (主数据源)
    │
    │  SQL查询
    ▼
Flask后端 (Python)
    │
    ├── /api/fund/search
    ├── /api/fund/categories
    ├── /api/fund/performance
    ├── /api/fund/ranking
    └── /api/crawler/run
    │
    ▼
浏览器 (HTML/JS)
```

- 前端纯HTML/CSS/JS单页面，Chart.js绘图
- Flask后端做API服务，所有查询走MySQL
- 定时爬虫每周从天天基金API抓取数据写入MySQL
- MySQL做主数据源，不依赖实时API

## 数据库设计

### fund_categories — 基金分类

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 主键 |
| name | VARCHAR(50) UNIQUE | 分类名称 |

### funds — 基金基本信息

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(6) PK | 基金代码 |
| name | VARCHAR(100) | 基金名称 |
| category_id | INT FK | 关联fund_categories |

### fund_nav — 每日净值

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 主键 |
| fund_code | VARCHAR(6) FK | 关联funds |
| nav_date | DATE | 净值日期 |
| nav | DECIMAL(10,4) | 单位净值 |
| acc_nav | DECIMAL(10,4) | 累计净值 |

唯一约束：`(fund_code, nav_date)`

### fund_weekly — 周度涨跌幅

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 主键 |
| fund_code | VARCHAR(6) FK | 关联funds |
| week_start | DATE | 周起始日 |
| week_end | DATE | 周结束日 |
| change_pct | DECIMAL(8,4) | 周涨跌幅(%) |

唯一约束：`(fund_code, week_start)`

周涨跌幅 = (周末净值 - 周初净值) / 周初净值 * 100

## API设计

### GET /api/fund/search

搜索基金

| 参数 | 说明 |
|------|------|
| keyword | 基金代码或名称关键词 |

返回：匹配的基金列表（code、name、category_name）

### GET /api/fund/categories

获取所有基金分类

返回：分类列表（id、name）

### GET /api/fund/performance

查询指定基金周度涨跌幅

| 参数 | 说明 |
|------|------|
| code | 基金代码（必填） |
| start | 开始日期（必填） |
| end | 结束日期（必填） |

返回：每周涨跌幅列表（week_start、week_end、change_pct）

### GET /api/fund/ranking

同分类全市场排名

| 参数 | 说明 |
|------|------|
| category_id | 基金分类ID（必填） |
| start | 开始日期（必填） |
| end | 结束日期（必填） |
| sort | 排序方式：asc/desc，默认desc（选填） |

返回：排名列表（rank、fund_code、fund_name、change_pct、total_funds）

累计涨跌幅 = (1+w1) * (1+w2) * ... * (1+wn) - 1

### POST /api/crawler/run

触发爬虫

| 参数 | 说明 |
|------|------|
| mode | full（全量）/increment（增量），默认increment |

缓存策略：排名查询结果Flask-Caching内存缓存1小时

## 前端设计

单页面三个区域：

1. **搜索栏**：基金代码/名称输入框 + 搜索按钮，结果下拉列表
2. **查询条件**：开始/结束日期选择器 + 基金分类下拉 + 查询按钮
3. **结果展示**：
   - 单基金：信息卡片 + 周度涨跌幅表格 + 折线图(Chart.js)
   - 分类排名：排名表格，搜索的基金高亮

技术：手写CSS，Chart.js(CDN)，HTML5原生日期选择器，无构建工具

## 爬虫模块

数据源：天天基金（东方财富）公开API

| 用途 | 接口 |
|------|------|
| 基金列表+分类 | fund.eastmoney.com/js/fundcode_search.js |
| 单基金历史净值 | fund.eastmoney.com/f10/F10DataApi.aspx |

### 全量模式（首次）

1. 拉取基金列表，写入funds和fund_categories
2. 逐只基金拉取全部历史净值，写入fund_nav
3. 计算所有周度涨跌幅，写入fund_weekly
4. 请求间隔0.5秒

### 增量模式（日常）

1. 拉取最新基金列表，新增/更新funds
2. 逐只基金拉取最近一周净值
3. 计算最新一周涨跌幅，写入fund_weekly

### 定时与容错

- APScheduler每周六00:30增量爬取
- 全量通过API手动触发
- 单只基金失败不影响其他，记录失败列表
- 非交易日无数据自动跳过

## 项目目录

```
fund/
├── app.py                  # Flask入口
├── config.py               # 配置
├── models.py               # SQLAlchemy模型
├── requirements.txt        # Python依赖
├── crawler/
│   ├── __init__.py
│   ├── fund_list.py        # 爬取基金列表+分类
│   ├── fund_nav.py         # 爬取历史净值
│   └── scheduler.py        # APScheduler定时任务
├── api/
│   ├── __init__.py
│   ├── fund.py             # 基金查询接口
│   └── crawler.py          # 爬虫触发接口
├── service/
│   ├── __init__.py
│   ├── fund_service.py     # 基金查询业务逻辑
│   └── ranking_service.py  # 排名计算逻辑
├── static/
│   ├── index.html          # 主页面
│   ├── style.css           # 样式
│   └── app.js              # 前端逻辑
└── sql/
    └── init.sql            # 建表脚本
```

## 依赖

- Flask
- Flask-SQLAlchemy
- Flask-Caching
- Flask-APScheduler
- requests
- pymysql

## 启动方式

```bash
pip install -r requirements.txt
python sql/init.sql          # 建表
python app.py                # 启动服务
```
