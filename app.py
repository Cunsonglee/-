import streamlit as st
import requests
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
from urllib.parse import urlparse
import json
import time
import sys

# ==========================================
# 1. 爬虫基础配置 (Headers, 网站列表, 月份映射)
# ==========================================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

websites = [
    "https://www.buch-dein-visum.de/en/news",
    "https://visasnews.com/en/africa-news/",
    "https://visasnews.com/en/america-news/",
    "https://visasnews.com/en/asia-news/",
    "https://visasnews.com/en/europe-news/",
    "https://visasnews.com/en/oceania-news/",
    "https://visasnews.com/en/travel-news/",
    "https://www.visamundi.co/en/blog/",
    "https://e.vnexpress.net/news/travel/visa",
    "https://atta.travel/news.html?sortBy=recent&topic_categories=visa",
    "https://visadone.com/news/",
    "https://www.bal.com/immigration-news/",
    "https://www.fragomen.com/insights/index.html?nt=news",
    "https://travelobiz.com/category/visas-passports/",
    "https://www.business-standard.com/search?q=visa",
    "https://travel.economictimes.indiatimes.com/news/visas-and-passports"
]

MONTHS = {
    'jan': 0, 'january': 0, 'jan.': 0, 'januar': 0, 'feb': 1, 'february': 1, 'feb.': 1, 'mar': 2, 'march': 2, 'marz': 2,
    'apr': 3, 'april': 3, 'may': 4, 'mai': 4, 'jun': 5, 'june': 5, 'jul': 6, 'july': 6, 'aug': 7, 'august': 7,
    'sep': 8, 'september': 8, 'oct': 9, 'october': 9, 'nov': 10, 'november': 10, 'dec': 11, 'december': 11,
    'ene': 0, 'enero': 0, 'febrero': 1, 'marzo': 2, 'abril': 3, 'mayo': 4, 'junio': 5, 'julio': 6, 'agosto': 7,
    'septiembre': 8, 'octubre': 9, 'noviembre': 10, 'diciembre': 11
}

# ==========================================
# 2. 爬虫解析工具函数 (日期处理与URL补全)
# ==========================================
def normalize_date(dt):
    if not dt: return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt

def safe_datetime(year, month, day):
    try:
        return datetime(year, month, day)
    except Exception:
        return None

def infer_year(day, month_idx):
    now = datetime.now()
    assumed = safe_datetime(now.year, month_idx + 1, day)
    if not assumed: return now.year
    if assumed - now > timedelta(days=7):
        assumed = safe_datetime(now.year - 1, month_idx + 1, day)
    return assumed.year if assumed else now.year

def parse_day_month(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'^(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+)$', t)
    if not m: return None
    day = int(m.group(1))
    mon_key = m.group(2).lower()
    month_idx = MONTHS.get(mon_key)
    if month_idx is None: return None
    year = infer_year(day, month_idx)
    return safe_datetime(year, month_idx + 1, day)

def parse_month_day_year(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'^([A-Za-zÀ-ÿ\.]+)\s+(\d{1,2}),\s*(\d{4})$', t)
    if not m: return None
    mon_key = m.group(1).lower()
    month_idx = MONTHS.get(mon_key)
    if month_idx is None: return None
    return safe_datetime(int(m.group(3)), month_idx + 1, int(m.group(2)))

def parse_day_month_year(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'^(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+),?\s+(\d{4})$', t)
    if not m: return None
    mon_key = m.group(2).lower()
    month_idx = MONTHS.get(mon_key)
    if month_idx is None: return None
    return safe_datetime(int(m.group(3)), month_idx + 1, int(m.group(1)))

def absolute_url(href, base):
    if not href: return ''
    if href.startswith('http'): return href
    if base.endswith('/') and href.startswith('/'): return base.rstrip('/') + href
    return base + href

# ==========================================
# 3. 核心路由分配：各大网站独立解析器
# ==========================================
# (为了保持代码整洁，我保留了其中几个你写的最长的解析函数结构)
# 【注意】你可以将原来 main.py 里的其它 parse_xxx 函数也粘贴到这个区域

def parse_bdv(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for n in soup.select('.blogItem'):
        title_a = n.select_one('a.blogItem-title')
        date_small = n.select_one('.blogItem-footer small')
        if not title_a: continue
        title = title_a.get_text().strip()
        link = absolute_url(title_a.get('href'), base_url)
        date_text = date_small.get_text().strip() if date_small else ''
        out.append({'title': title, 'link': link, 'date': parse_day_month(date_text), 'date_text': date_text, 'source': 'buch-dein-visum'})
    return out

def parse_vn(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out, seen = [], set()
    def add_item(title, link, date, date_text=''):
        if not title or not link or link in seen: return
        seen.add(link)
        out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'visasnews'})

    for post in soup.select('article.post'):
        a = post.select_one('h2.entry-title a[href]')
        if not a: continue
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        time_el = post.select_one('time.entry-date.published') or post.select_one('time.entry-date') or post.select_one('time')
        date_text = time_el.get_text().strip() if time_el else ''
        date = parse_month_day_year(date_text) or parse_day_month(date_text)
        add_item(title, link, date, date_text)
    return out

def parse_items_from_html(html, url):
    """解析器路由：根据网址域名调用对应的解析函数"""
    try:
        if "buch-dein-visum.de" in url: return parse_bdv(html, url)
        elif "visasnews.com" in url: return parse_vn(html, url)
        # 【请在此处补充】你原来 main.py 里的 parse_travelobiz, parse_vne, parse_bal 等函数，然后在这加 if 分支即可
        # elif "travelobiz.com" in url: return parse_travelobiz(html, url)
    except Exception as e:
        print(f"解析出错 {url}: {e}")
    return []

# ==========================================
# 4. 后台自动化抓取任务 (供 Github Actions 使用)
# ==========================================
def run_scraper_job():
    print("🚀 开始执行定时抓取任务...")
    all_posts = []
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    for url in websites:
        try:
            print(f"Scraping {url}...")
            response = scraper.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            found = parse_items_from_html(response.text, url)
            if found:
                all_posts.extend(found)
        except Exception as e:
            print(f"❌ 抓取 {url} 失败: {e}")
            
    # 数据格式化为JSON并保存
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
# 5. Streamlit 前端数据展示界面
# ==========================================
def trigger_github_action():
    try:
        # 触发 Github Action 绕过反爬机制
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["GITHUB_REPO"]
        url = f"https://api.github.com/repos/{repo}/actions/workflows/daily_scrape.yml/dispatches"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.post(url, headers=headers, json={"ref": "main"})
        return res.status_code
    except Exception as e:
        st.error(f"Error en la configuración de Secrets: {e}")
        return 0

def run_streamlit_app():
    st.set_page_config(page_title="Asistente de Visados", layout="wide")
    st.title("🌍 Extracción de Noticias de Visado")

    st.sidebar.header("Parámetros de búsqueda")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("Fecha fin", value=datetime.now())

    keyword = st.sidebar.text_input("Buscar palabra clave")
    
    if st.sidebar.button("🚀 Iniciar extracción en la nube (GitHub Actions)"):
        with st.spinner("Despertando el motor de GitHub para omitir bloqueos..."):
            status = trigger_github_action()
            if status == 204:
                st.sidebar.success("✅ ¡Orden enviada con éxito! GitHub está trabajando (aprox. 1 min).")
            else:
                st.sidebar.error(f"Fallo al iniciar. Código: {status}")

    st.markdown("---")

    # 从 visa_data.json 加载数据
    try:
        with open('visa_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data:
                df = pd.DataFrame(data)
                
                # 处理时间格式并过滤
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    start_datetime = pd.to_datetime(start_date)
                    end_datetime = pd.to_datetime(end_date)
                    # 补充筛选逻辑 (忽略空时间，防止报错)
                    mask = df['date'].isna() | ((df['date'] >= start_datetime) & (df['date'] <= end_datetime + pd.Timedelta(days=1)))
                    df = df.loc[mask]
                    
                # 过滤关键字
                if keyword:
                    df = df[df['title'].str.contains(keyword, case=False, na=False)]
                
                # 调整页面列显示顺序并去除索引
                st.dataframe(
                    df[['title', 'source', 'date', 'link']].sort_values(by='date', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("No hay datos en el archivo JSON. Espera a que termine la acción de GitHub.")
    except FileNotFoundError:
        st.error("No se encontró el archivo visa_data.json. Por favor inicie una extracción primero.")

# ==========================================
# 6. 环境入口分配 (重要)
# ==========================================
if __name__ == '__main__':
    # 检查当前是否是由 Streamlit 启动的进程
    # 如果不是 Streamlit (比如是 `python app.py`)，就执行爬虫脚本
    if "streamlit" not in sys.modules and not sys.argv[0].endswith("streamlit"):
        run_scraper_job()
        
# ------------------------------------------
# 如果是 Streamlit 执行，它按顺序渲染文件，到这里渲染 UI 
if "streamlit" in sys.modules or sys.argv[0].endswith("streamlit"):
    run_streamlit_app()
