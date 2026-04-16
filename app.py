import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
from urllib.parse import urlparse
import json
import time

# ==========================================
# 1. 配置与全局变量 (合并原来的配置)
# ==========================================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

MONTHS = {
    'jan': 0, 'january': 0, 'feb': 1, 'february': 1, # ... (保留你原来的 MONTHS 字典)
}

websites = [
    "https://www.buch-dein-visum.de/en/news",
    "https://visasnews.com/en/africa-news/",
    # ... (保留你原来的 websites 列表)
]

# ==========================================
# 2. 数据解析与抓取逻辑 (从原来的 main.py 搬过来)
# ==========================================

# 在这里粘贴你原来 main.py 里的工具函数
# 例如: normalize_date, parse_day_month, parse_month_day_year 等等...

# 在这里粘贴你原来 main.py 里的网站专属解析逻辑
# 例如: def parse_bdv(html, base_url): ...
#      def parse_vn(html, base_url): ...
#      def parse_items_from_html(html, url): ...

def run_scraper_job():
    """
    这是专门给 GitHub Action 定时任务执行的函数：
    获取所有网站数据并写入 visa_data.json
    """
    all_posts = []
    print("🚀 开始执行定时抓取任务...")
    
    for url in websites:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            # 假设你原本 main.py 有一个主分配函数 parse_items_from_html
            found = parse_items_from_html(response.text, url)
            if found:
                all_posts.extend(found)
        except Exception as e:
            print(f"❌ 抓取 {url} 失败: {e}")
            
    # 数据清理和保存到 JSON
    serializable_posts = []
    for post in all_posts:
        item = post.copy()
        if isinstance(item.get('date'), datetime):
            item['date'] = item['date'].isoformat()
        serializable_posts.append(item)

    with open('visa_data.json', 'w', encoding='utf-8') as f:
        json.dump(serializable_posts, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 抓取完成，共提取 {len(serializable_posts)} 条新闻，已保存至 visa_data.json")


# ==========================================
# 3. Streamlit 前端 UI 逻辑 (从原来的 visa_app.py 搬过来)
# ==========================================

def run_streamlit_app():
    """
    这是 Streamlit 云端渲染 UI 的逻辑
    """
    st.set_page_config(page_title="Visa News Tracker", layout="wide")
    st.title("🌐 Visa News Tracker")
    
    # 侧边栏
    st.sidebar.header("过滤选项")
    
    # 加载已保存的 JSON 数据 (由 Github Action 每日更新)
    try:
        with open('visa_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df) # 替换为你原本的表格和过滤展示逻辑
            else:
                st.warning("JSON 暂无数据。")
    except FileNotFoundError:
        st.error("找不到 visa_data.json，请等待 Github Action 完成初次抓取。")

# ==========================================
# 4. 核心执行入口 (魔法就在这里)
# ==========================================
if __name__ == '__main__':
    # 判断运行环境。
    # Streamlit 运行时，__name__ 并不是 "__main__" 而是其内部机制加载，或者即便命中这行，
    # 我们也可以通过判断是否导入了 Streamlit 的某些特有上下文来区分。
    # 但最简单可靠的判断方式是：
    import sys
    
    # 如果命令是 'python app.py' (sys.argv 里没有 streamlit)，则执行抓取
    if "streamlit" not in sys.modules and not sys.argv[0].endswith("streamlit"):
        run_scraper_job()
        
# ------------------------------------------
# 如果是 Streamlit 启动的，它会顺序执行脚本，我们直接把 UI 逻辑放在顶层调用：
import sys
if "streamlit" in sys.modules or sys.argv[0].endswith("streamlit"):
    run_streamlit_app()
