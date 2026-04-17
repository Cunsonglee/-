import requests
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re
import os
import random

# --- 配置区 ---
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
    "https://travel.economictimes.indiatimes.com/news/visas-and-passports"
]

MONTHS = {
    'jan': 0, 'january': 0, 'jan.': 0, 'januar': 0, 'feb': 1, 'february': 1, 'feb.': 1, 'februar': 1,
    'mar': 2, 'march': 2, 'märz': 2, 'mär': 2, 'maerz': 2, 'marz': 2, 'mar.': 2, 'apr': 3, 'april': 3, 'apr.': 3,
    'may': 4, 'mai': 4, 'jun': 5, 'june': 5, 'juni': 5, 'jul': 6, 'july': 6, 'juli': 6, 'aug': 7, 'august': 7,
    'sep': 8, 'sept': 8, 'september': 8, 'sept.': 8, 'oct': 9, 'october': 9, 'okt': 9, 'oktober': 9,
    'nov': 10, 'november': 10, 'dec': 11, 'december': 11, 'dez': 11, 'dezember': 11, 'ene': 0, 'enero': 0,
    'febr': 1, 'febrero': 1, 'marzo': 2, 'abr': 3, 'abril': 3, 'mayo': 4, 'junio': 5, 'julio': 6, 'ago': 7,
    'agosto': 7, 'setiembre': 8, 'septiembre': 8, 'octubre': 9, 'noviembre': 10, 'diciembre': 11
}

# --- 核心辅助工具 ---
def normalize_date(dt):
    if not dt: return None
    if dt.tzinfo is not None: dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt

def safe_datetime(year, month, day):
    try: return datetime(year, month, day)
    except: return None

def infer_year(day, month_idx):
    now = datetime.now()
    assumed = safe_datetime(now.year, month_idx + 1, day)
    if not assumed: return now.year
    if assumed - now > timedelta(days=7):
        assumed = safe_datetime(now.year - 1, month_idx + 1, day)
    return assumed.year if assumed else now.year

def absolute_url(href, base):
    if not href: return ""
    if href.startswith('http'): return href
    from urllib.parse import urljoin
    return urljoin(base, href)

# --- 各站点解析逻辑 ---
def parse_bdv(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    nodes = soup.select('.blogItem')
    out = []
    for n in nodes:
        title_a = n.select_one('a.blogItem-title')
        if not title_a: continue
        title = title_a.get_text().strip()
        link = absolute_url(title_a.get('href'), base_url)
        date_small = n.select_one('.blogItem-footer small')
        date_text = date_small.get_text().strip() if date_small else ''
        # 这里使用你的解析函数
        date = parse_day_month(date_text)
        out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'buch-dein-visum'})
    return out

def parse_vn(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    seen = set()
    posts = soup.select('article.post')
    for post in posts:
        a = post.select_one('h2.entry-title a[href]')
        if not a: continue
        link = absolute_url(a.get('href'), base_url)
        if link in seen: continue
        seen.add(link)
        title = a.get_text().strip()
        time_el = post.select_one('time')
        date = None
        date_text = time_el.get_text().strip() if time_el else ''
        if time_el and time_el.get('datetime'):
            try: date = normalize_date(datetime.fromisoformat(time_el.get('datetime').replace('Z', '+00:00')))
            except: date = parse_month_day_year(date_text)
        out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'visasnews'})
    return out

def parse_vne(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('.item-news, .item_news')
    out = []
    for n in items:
        a = n.select_one('h4.title_news_site a[href]')
        if not a: continue
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        # 获取日期（略过复杂的内页逻辑以提高速度，如有需要可保留）
        out.append({'title': title, 'link': link, 'date': None, 'date_text': 'VnExpress', 'source': 'vnexpress'})
    return out

def parse_et_travel(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=True)
    out = []
    scraper = cloudscraper.create_scraper()
    valid_links = []
    for a in links:
        h = a.find(['h2', 'h3'])
        if not h: continue
        title = h.get_text().strip()
        link = absolute_url(a['href'], base_url)
        if '/news/' in link or '/blog/' in link:
            valid_links.append({'title': title, 'link': link})
    
    for item in valid_links[:8]: # 限制内页抓取数量防止超时
        link = item['link']
        date = None
        try:
            inner_res = scraper.get(link, timeout=10)
            if inner_res.status_code == 200:
                inner_soup = BeautifulSoup(inner_res.text, 'html.parser')
                meta = inner_soup.select_one('meta[property="article:published_time"]')
                if meta and meta.get('content'):
                    iso_str = meta.get('content')
                    date_only = iso_str.split('T')[0] # 修正变量名
                    date = datetime.fromisoformat(date_only)
        except: pass
        out.append({'title': item['title'], 'link': link, 'date': date, 'date_text': '', 'source': 'et-travel'})
    return out

# --- 通用日期解析器 ---
def parse_day_month(text):
    m = re.match(r'^(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+)$', re.sub(r'\s+', ' ', (text or '')).strip())
    if not m: return None
    month_idx = MONTHS.get(m.group(2).lower())
    if month_idx is None: return None
    return safe_datetime(infer_year(int(m.group(1)), month_idx), month_idx + 1, int(m.group(1)))

def parse_month_day_year(text):
    m = re.match(r'^([A-Za-zÀ-ÿ\.]+)\s+(\d{1,2}),\s*(\d{4})$', re.sub(r'\s+', ' ', (text or '')).strip())
    if not m: return None
    month_idx = MONTHS.get(m.group(1).lower())
    if month_idx is None: return None
    return safe_datetime(int(m.group(3)), month_idx + 1, int(m.group(2)))

# --- 抓取主控 ---
def parse_items_from_html(html, base_url):
    from urllib.parse import urlparse
    host = urlparse(base_url).netloc
    if 'e.vnexpress.net' in host: return parse_vne(html, base_url)
    if 'visasnews.com' in host: return parse_vn(html, base_url)
    if 'buch-dein-visum.de' in host: return parse_bdv(html, base_url)
    if 'economictimes.indiatimes.com' in host: return parse_et_travel(html, base_url)
    # 其他站点解析器建议按需保留
    return []

def scrape_website(url):
    print(f">>> 正在爬取: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # 尝试普通请求
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        return parse_items_from_html(res.text, url)
    except:
        # 尝试 Cloudscraper 绕过
        try:
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
            res = scraper.get(url, timeout=25)
            return parse_items_from_html(res.text, url)
        except Exception as e:
            print(f"!!! 抓取失败 {url}: {e}")
            return []

def main(days=3):
    print(f"Iniciando extracción (últimos {days} días)...")
    all_posts = []
    cutoff = datetime.now() - timedelta(days=days)

    for url in websites:
        posts = scrape_website(url)
        for post in posts:
            dt = post.get('date')
            if dt and isinstance(dt, datetime):
                if dt >= cutoff: all_posts.append(post)
            else:
                all_posts.append(post) # 无日期记录默认保留

    # 序列化
    serializable_posts = []
    for post in all_posts:
        item = post.copy()
        if isinstance(item.get('date'), datetime):
            item['date'] = item['date'].isoformat()
        serializable_posts.append(item)

    # 合并历史数据
    existing_posts = []
    if os.path.exists('visa_data.json'):
        try:
            with open('visa_data.json', 'r', encoding='utf-8') as f:
                existing_posts = json.load(f)
        except: pass

    merged_dict = { p['link']: p for p in existing_posts if 'link' in p }
    for p in serializable_posts:
        if 'link' in p: merged_dict[p['link']] = p

    final_posts = sorted(merged_dict.values(), key=lambda x: x.get('date') or "", reverse=True)

    with open('visa_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_posts, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 完成！总记录数: {len(final_posts)}")

if __name__ == "__main__":
    main(3)
