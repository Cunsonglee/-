import requests
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re
import time

# List of websites to scrape
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

# Month mapping (English, German, Spanish)
MONTHS = {
    'jan': 0, 'january': 0, 'jan.': 0, 'januar': 0,
    'feb': 1, 'february': 1, 'feb.': 1, 'februar': 1,
    'mar': 2, 'march': 2, 'märz': 2, 'mär': 2, 'maerz': 2, 'marz': 2, 'mar.': 2,
    'apr': 3, 'april': 3, 'apr.': 3,
    'may': 4, 'mai': 4,
    'jun': 5, 'june': 5, 'juni': 5,
    'jul': 6, 'july': 6, 'juli': 6,
    'aug': 7, 'august': 7,
    'sep': 8, 'sept': 8, 'september': 8, 'sept.': 8,
    'oct': 9, 'october': 9, 'okt': 9, 'oktober': 9,
    'nov': 10, 'november': 10,
    'dec': 11, 'december': 11, 'dez': 11, 'dezember': 11,
    'ene': 0, 'enero': 0,
    'febr': 1, 'febrero': 1,
    'marzo': 2,
    'abr': 3, 'abril': 3,
    'mayo': 4,
    'junio': 5,
    'julio': 6,
    'ago': 7, 'agosto': 7,
    'setiembre': 8, 'septiembre': 8,
    'octubre': 9,
    'noviembre': 10,
    'diciembre': 11
}

def normalize_date(dt):
    if not dt:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt

def parse_day_month(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'^(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+)$', t)
    if not m:
        return None
    day = int(m.group(1))
    mon_key = m.group(2).lower()
    month_idx = MONTHS.get(mon_key)
    if month_idx is None:
        return None
    year = infer_year(day, month_idx)
    return safe_datetime(year, month_idx + 1, day)

def parse_month_day_year(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'^([A-Za-zÀ-ÿ\.]+)\s+(\d{1,2}),\s*(\d{4})$', t)
    if not m:
        return None
    mon_key = m.group(1).lower()
    month_idx = MONTHS.get(mon_key)
    if month_idx is None:
        return None
    day = int(m.group(2))
    year = int(m.group(3))
    return safe_datetime(year, month_idx + 1, day)

def parse_day_month_year(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'^(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+),?\s+(\d{4})$', t)
    if not m:
        return None
    day = int(m.group(1))
    mon_key = m.group(2).lower()
    month_idx = MONTHS.get(mon_key)
    if month_idx is None:
        return None
    year = int(m.group(3))
    return safe_datetime(year, month_idx + 1, day)

def parse_es_date(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.match(r'(\d{1,2})\s*(?:de\s*)?([A-Za-zÁÉÍÓÚÜáéíóúüñÑ\.]+)\s*(?:de\s*)?(\d{4})', t, re.IGNORECASE)
    if not m:
        return None
    day = int(m.group(1))
    mon_key = m.group(2).lower()
    month_idx = MONTHS.get(mon_key)
    year = int(m.group(3))
    if month_idx is None:
        return None
    return datetime(year, month_idx + 1, day)

def safe_datetime(year, month, day):
    try:
        return datetime(year, month, day)
    except Exception:
        return None

def infer_year(day, month_idx):
    now = datetime.now()
    assumed = safe_datetime(now.year, month_idx + 1, day)
    if not assumed:
        return now.year
    if assumed - now > timedelta(days=7):
        assumed = safe_datetime(now.year - 1, month_idx + 1, day)
    return assumed.year if assumed else now.year

def absolute_url(href, base):
    if href.startswith('http'):
        return href
    if base.endswith('/') and href.startswith('/'):
        return base.rstrip('/') + href
    return base + href

# Parsing functions for each site
def parse_bdv(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    nodes = soup.select('.blogItem')
    out = []
    for n in nodes:
        title_a = n.select_one('a.blogItem-title')
        date_small = n.select_one('.blogItem-footer small')
        if not title_a:
            continue
        title = title_a.get_text().strip()
        href = title_a.get('href')
        link = absolute_url(href, base_url)
        date_text = date_small.get_text().strip() if date_small else ''
        date = parse_day_month(date_text)
        out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'buch-dein-visum'})
    return out

def parse_vn(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')

    out = []
    seen = set()

    def add_item(title, link, date, date_text=''):
        if not title or not link:
            return
        key = link.strip()
        if not key or key in seen:
            return
        seen.add(key)
        out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'visasnews'})

    slides = soup.select('.n2-ss-showcase-slides .n2-ss-slide')
    for slide in slides:
        a = slide.select_one('a[href]')
        href = a.get('href') if a else ''
        link = absolute_url(href, base_url)
        title = a.get_text().strip() if a else slide.get('data-title', '').strip()
        b = slide.select_one('p b, .n2-ss-item-content b')
        date_text = b.get_text().strip() if b else ''
        date = parse_month_day_year(date_text)
        add_item(title, link, date, date_text)

    posts = soup.select('article.post')
    for post in posts:
        a = post.select_one('h2.entry-title a[href]')
        if not a:
            continue

        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        date_text = ''
        date = None
        time_el = post.select_one('time.entry-date.published') or post.select_one('time.entry-date') or post.select_one('time')
        if time_el:
            date_text = time_el.get_text().strip()
            iso = time_el.get('datetime')
            if iso:
                try:
                    date = normalize_date(datetime.fromisoformat(iso.replace('Z', '+00:00')))

                except:
                    date = parse_month_day_year(date_text) or parse_day_month(date_text)
            else:
                date = parse_month_day_year(date_text) or parse_day_month(date_text)
        add_item(title, link, date, date_text)

    return out


def parse_vne(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('.item-news, .item_news')
    out = []
    
    for n in items:
        a = n.select_one('h4.title_news_site a[href]')
        if not a:
            continue
        
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        
        # --- A. 尝试在主页抓取日期 ---
        t = n.select_one('.timer_post')
        date = None
        date_text = ''
        
        if t:
            raw = t.get_text().strip()
            m = re.search(r'([A-Za-z]+\s+\d{1,2},\s*\d{4})', raw)
            if m:
                date_text = m.group(1)
                date = parse_month_day_year(date_text)
        
        # --- B. 主页没日期（头条），进入内页 ---
        if not date:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                import requests
                inner_res = requests.get(link, headers=headers, timeout=15)
                
                if inner_res.status_code == 200:
                    inner_soup = BeautifulSoup(inner_res.text, 'html.parser')
                    
                    # 【优先级 1】优先找肉眼可见的 HTML 标签，保证和网页上写的时间一模一样
                    target_el = (inner_soup.select_one('.author') or 
                                 inner_soup.select_one('span.date') or 
                                 inner_soup.select_one('.date') or 
                                 inner_soup.select_one('.time-detail'))
                    
                    if target_el:
                        full_text = target_el.get_text(separator=' ').strip()
                        m_inner = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})', full_text)
                        if m_inner:
                            date_text = f"{m_inner.group(1)} {m_inner.group(2)}, {m_inner.group(3)}"
                            date = parse_month_day_year(date_text)
                            
                    # 【优先级 2】如果标签变了，直接在全文里搜索可见的日期格式
                    if not date:
                        m_global = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*\|\s*\d{1,2}:\d{2}', inner_res.text)
                        if m_global:
                            date_text = f"{m_global.group(1)} {m_global.group(2)}, {m_global.group(3)}"
                            date = parse_month_day_year(date_text)
                            
                    # 【优先级 3 (最后兜底)】如果以上都不行，才读取隐藏的 Meta 标签（时区可能会导致差一天）
                    if not date:
                        meta_tags = [
                            inner_soup.select_one('meta[name="pubdate"]'),
                            inner_soup.select_one('meta[itemprop="datePublished"]'),
                            inner_soup.select_one('meta[property="article:published_time"]')
                        ]
                        for meta in meta_tags:
                            if meta and meta.get('content'):
                                iso_str = meta.get('content')
                                try:
                                    date_part = iso_str.split('T')[0].split(' ')[0]
                                    date = datetime.fromisoformat(date_part)
                                    date_text = date.strftime('%B %d, %Y')
                                    break
                                except: pass
                                
            except Exception as e:
                print(f"无法访问内页 {link}: {e}")
        
        if title and link:
            out.append({
                'title': title, 
                'link': link, 
                'date': date, 
                'date_text': date_text or '—', 
                'source': 'vnexpress'
            })
            
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]

def parse_atta(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    nodes = soup.select('#resource-section-list .article-list-item.article-type-article')
    out = []
    for n in nodes:
        a = n.select_one('h4.article-title a[href]')
        if not a:
            continue
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        d_el = n.select_one('.article-meta-list-item.mod-published-date')
        date_text = d_el.get_text().strip() if d_el else ''
        date = parse_day_month_year(date_text) or parse_day_month(date_text)
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'atta'})
    return out

def parse_visadone(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    title_links = soup.select('h3.entry-title a')
    for a in title_links:
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        date_text = ''
        date = None
        container = a
        while container:
            time_el = container.select_one('time.entry-date, time')
            if time_el:
                date_text = time_el.get_text().strip()
                iso = time_el.get('datetime')
                if iso:
                    try:
                        date = normalize_date(datetime.fromisoformat(iso.replace('Z', '+00:00')))
                    except Exception:
                        date = parse_month_day_year(date_text) or parse_day_month(date_text)
                else:
                    date = parse_month_day_year(date_text) or parse_day_month(date_text)
                break
            container = container.parent
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'visadone'})
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]

def parse_bal_sitemap(base_url, max_items=30):
    out = []
    try:
        # 在这里也创建一个隐身 scraper
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

        sitemap_url = 'https://www.bal.com/sitemap-posttype-bal_news.xml'
        response = scraper.get(sitemap_url, timeout=15)  # <--- 使用 scraper 替换 requests
        response.raise_for_status()
        sitemap = BeautifulSoup(response.text, 'xml')
        urls = sitemap.find_all('url')[:max_items]

        for url_tag in urls:
            loc = url_tag.find('loc').get_text(strip=True) if url_tag.find('loc') else ''
            if '/immigration-news/' not in loc:
                continue
            lastmod = url_tag.find('lastmod').get_text(strip=True) if url_tag.find('lastmod') else ''
            date = None
            date_text = ''
            if lastmod:
                try:
                    date = normalize_date(datetime.fromisoformat(lastmod))
                    date_text = date.strftime('%B %d, %Y')
                except Exception:
                    date = None
            try:
                # 获取内页也使用 scraper
                post_resp = scraper.get(loc, timeout=15)  # <--- 使用 scraper 替换 requests
                post_resp.raise_for_status()
                title = parse_bal_post_title(post_resp.text)
            except Exception:
                title = ''
            if not title:
                title = loc.rstrip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            out.append({'title': title, 'link': loc, 'date': date, 'date_text': date_text, 'source': 'bal'})
    except Exception as e:
        print(f"BAL Sitemap 解析出错: {e}")
    return out

def parse_bal(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    items = soup.select('div.recommended-box, .recommended-box')
    for it in items:
        title_el = it.select_one('a.recommended-box__link h3.line-under') or it.select_one('h3.line-under')
        title = title_el.get_text().strip() if title_el else ''
        link_el = it.select_one('a.recommended-box__link[href]') or it.select_one('a[href*="/immigration-news/"]')
        if not link_el:
            continue
        link = absolute_url(link_el.get('href'), base_url)
        date_el = it.select_one('span.date') # Simplified for brevity
        date_text = date_el.get_text().strip() if date_el else ''
        date = parse_month_day_year(date_text) if date_text else None
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'bal'})
    if out: return out
    return parse_bal_sitemap(base_url)

def parse_fragomen(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    anchors = soup.select('a.galleryView')
    for a in anchors:
        title_el = a.select_one('span.rte-title-mode')
        if not title_el: continue
        title = title_el.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        date_text = ''
        date = None
        prev_span = a.find_previous(lambda tag: tag.name == 'span' and '|' in tag.get_text())
        if prev_span:
            raw = prev_span.get_text().strip()
            m = re.search(r'([A-Za-zÀ-ÿ\.]+\s+\d{1,2},\s*\d{4})', raw)
            if m:
                date_text = m.group(1)
                date = parse_month_day_year(date_text)
        out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'fragomen'})
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]

def parse_travelobiz(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one('div.entries') or soup
    items = container.select('article.entry-card')
    out = []
    for it in items:
        a = it.select_one('h2.entry-title a')
        if not a:
            continue
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        t = it.select_one('time.ct-meta-element-date') or it.select_one('time')
        date = None
        if t:
            dt = t.get('datetime')
            if dt:
                try:
                    parsed = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    date = normalize_date(parsed)
                except:
                    pass
        if not date and t:
            date_text = t.get_text().strip()
            # Parse DD/MM/YYYY or YYYY-MM-DD
            m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_text)
            if m:
                date = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            else:
                m = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_text)
                if m:
                    date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        out.append({'title': title, 'link': link, 'date': normalize_date(date), 'date_text': t.get('datetime') or t.get_text().strip() if t else '', 'source': 'travelobiz'})
    # Dedupe
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]

def parse_visamundi(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    arts = soup.select('article')
    out = []
    for a in arts:
        t_a = a.select_one('h2.entry-title a[href]')
        if not t_a: continue
        title = t_a.get_text().strip()
        link = absolute_url(t_a.get('href'), base_url)
        date = None
        date_text = ''
        pick = a.select_one('time[datetime]')
        if pick:
            date_text = pick.get_text().strip()
            iso = pick.get('datetime')
            if iso:
                try:
                    date = normalize_date(datetime.fromisoformat(iso.replace('Z', '+00:00')))
                except: pass
        if not date:
            raw_text = a.get_text()
            date = parse_es_date(raw_text)
            if date: date_text = str(date)
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'visamundi'})
    return out

# ==========================================
# 最终版：Business Standard 解析器 (无过滤，抓取所有结果)
# ==========================================
def parse_business_standard(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    # 锁定 cardlist 区块
    items = soup.select('div.cardlist') 
    out = []
    
    for n in items:
        a = n.select_one('a.smallcard-title')
        if not a: continue
            
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        
        date = None
        date_text = ''
        
        # 精准提取你提供的 Updated On 标签内容
        date_el = n.select_one('span[class*="listingstyle_updtText"]')
        if date_el:
            raw_text = date_el.get_text().strip()
            # 正则匹配 16 Apr 2026
            m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})', raw_text)
            if m:
                try:
                    day = int(m.group(1))
                    mon_str = m.group(2).lower()[:3]
                    year = int(m.group(3))
                    if mon_str in MONTHS:
                        date = datetime(year, MONTHS[mon_str] + 1, day)
                        date_text = date.strftime('%B %d, %Y')
                except: pass

        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text or '—', 'source': 'business-standard'})
            
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]

# ==========================================
# 修正版：Economic Times Travel 解析器 (精准锁定 author-section)
# ==========================================
def parse_et_travel(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=True)
    out = []
    
    import cloudscraper
    inner_scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    valid_links = []
    for a in links:
        h = a.find(['h2', 'h3'])
        if not h: continue
        title = h.get_text().strip()
        if len(title) < 15: continue
        link = absolute_url(a['href'], base_url)
        if '/news/' in link or '/blog/' in link:
            valid_links.append({'title': title, 'link': link})
            
    valid_links = valid_links[:15] # 限制前15条防卡死
    
    for item in valid_links:
        title = item['title']
        link = item['link']
        date = None
        date_text = ''
        
        print(f"  -> 正在抓取 ET Travel 内页日期: {title[:25]}...")
        
        try:
            inner_res = inner_scraper.get(link, timeout=10)
            if inner_res.status_code == 200:
                inner_soup = BeautifulSoup(inner_res.text, 'html.parser')
                
                # 【新增】第一优先级：直接去你说的 author-section 里抓 Published On
                author_section = inner_soup.select_one('.author-section') or inner_soup.select_one('.article-publish-date')
                if author_section:
                    raw_text = author_section.get_text(separator=' ').strip()
                    import re
                    # 匹配 "Published On Mar 27, 2026"
                    m_auth = re.search(r'(?:Published|Updated)\s*On\s*([A-Za-z]{3,})\s+(\d{1,2}),\s*(\d{4})', raw_text, re.IGNORECASE)
                    if m_auth:
                        date_text = f"{m_auth.group(1).capitalize()} {m_auth.group(2)}, {m_auth.group(3)}"
                        # 解析为标准格式
                        date = parse_month_day_year(date_text)
                
                # 第二优先级：如果页面排版变了，用 Meta 标签兜底
                if not date:
                    meta_tags = [
                        inner_soup.select_one('meta[property="article:published_time"]'),
                        inner_soup.select_one('meta[name="pubdate"]'),
                        inner_soup.select_one('meta[itemprop="datePublished"]')
                    ]
                    for meta in meta_tags:
                        if meta and meta.get('content'):
                            iso_str = meta.get('content')
                            try:
                                from datetime import datetime
                                date_part = iso_str.split('T')[0].split(' ')[0]
                                date = datetime.fromisoformat(date_part)
                                date_text = date.strftime('%B %d, %Y')
                                break
                            except: pass
                            
        except Exception as e:
            pass
            
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text or '—', 'source': 'et-travel'})
            
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]


def parse_items_from_html(html, base_url):
    from urllib.parse import urlparse
    host = urlparse(base_url).netloc
    if 'e.vnexpress.net' in host: return parse_vne(html, base_url)
    if 'visasnews.com' in host: return parse_vn(html, base_url)
    if 'buch-dein-visum.de' in host: return parse_bdv(html, base_url)
    if 'atta.travel' in host: return parse_atta(html, base_url)
    if 'visamundi.co' in host: return parse_visamundi(html, base_url)
    if 'visadone.com' in host: return parse_visadone(html, base_url)
    if 'bal.com' in host: return parse_bal(html, base_url)
    if 'fragomen.com' in host: return parse_fragomen(html, base_url)
    if 'travelobiz.com' in host: return parse_travelobiz(html, base_url)
    if 'business-standard.com' in host: return parse_business_standard(html, base_url)
    if 'economictimes.indiatimes.com' in host: return parse_et_travel(html, base_url)
    return []

# Function to scrape a website using robust fallback logic
def scrape_website(url):
    try:
        # --- 对正 1：专门针对 Business Standard 的多页翻页逻辑 ---
        # 只有 URL 匹配时才会执行这段
        if 'business-standard.com/search' in url:
            all_bs_posts = []
            # 模拟“点击加载更多”：通过修改 URL 参数 p（1到10页）
            for p in range(1, 11): 
                page_url = f"{url}&p={p}"
                print(f"  -> Business Standard: 正在获取第 {p} 页数据...")
                
                # 使用隐身模式，防止被反爬拦截
                scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
                response = scraper.get(page_url, timeout=20)
                
                if response.status_code == 200:
                    # 调用我们写好的精准解析器
                    page_posts = parse_business_standard(response.text, url)
                    if not page_posts: 
                        break # 如果这一页没内容了，就不用再抓下一页了
                    all_bs_posts.extend(page_posts)
                time.sleep(1) # 礼貌性停顿，防止 Streamlit 被封
            return all_bs_posts

        # --- 对正 2：其他所有网站（原样保留，互不干扰） ---
        # 默认的浏览器伪装头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        html = None
        try:
            # 方案 A：普通请求
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status() 
            html = response.text
        except:
            # 方案 B：隐身请求 (应对 403 或 101 错误)
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
            response = scraper.get(url, timeout=25)
            html = response.text
            
        if html:
            # 根据 URL 自动分发给不同的解析函数（如 parse_vne, parse_et_travel 等）
            return parse_items_from_html(html, url)
        else:
            return []
        
    except Exception as e:
        print(f"抓取失败 {url}: {e}")
        return []

def main(days=30):
    # --- ESPAÑOL: Inicio del proceso ---
    print(f"Iniciando extracción de noticias de los últimos {days} días...")
    all_posts = []
    cutoff = datetime.now() - timedelta(days=days-1)

    for url in websites:
        posts = scrape_website(url)
        for post in posts:
            date = post.get('date')
            date = normalize_date(date) if isinstance(date, datetime) else date
            post['date'] = date
            if date and isinstance(date, datetime) and date >= cutoff:
                all_posts.append(post)
            elif not date:
                all_posts.append(post)

    all_posts.sort(key=lambda x: x.get('date') or datetime.min, reverse=True)

    # --- ESPAÑOL: Generación del archivo HTML ---
    html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Análisis de Noticias de Visados</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f9f9f9; }
    h1 { color: #333; }
    table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #004a99; color: white; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    a { color: #007bff; text-decoration: none; font-weight: bold; }
    a:hover { text-decoration: underline; }
    .filters { margin-bottom: 20px; padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #ddd; }
    .filters input, .filters button { margin: 5px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
    .filters button { background-color: #28a745; color: white; border: none; cursor: pointer; }
    .filters button:hover { background-color: #218838; }
  </style>
</head>
<body>
  <h1>Noticias Recientes de Visados</h1>
  <div class="filters">
    <input type="text" id="keyword" placeholder="Buscar palabra clave...">
    <label>Desde:</label> <input type="date" id="startDate">
    <label>Hasta:</label> <input type="date" id="endDate">
    <input type="number" id="daysFilter" placeholder="Últimos X días" min="0">
    <button onclick="filterTable()">Filtrar Resultados</button>
  </div>
  <table id="newsTable">
    <thead>
      <tr>
        <th>Título</th>
        <th>Fuente</th>
        <th>Fecha</th>
        <th>Enlace</th>
      </tr>
    </thead>
    <tbody>'''

    for post in all_posts:
        title = post.get('title', '')
        source = post.get('source', '')
        date = post.get('date')
        row_date = date.strftime('%Y-%m-%d') if date else '—'
        display_date = date.strftime('%d-%m-%Y') if date else 'Desconocida'
        link = post.get('link', '')
        html_content += f'''
      <tr data-date="{row_date}" data-title="{title.lower()}">
        <td><strong>{title}</strong></td>
        <td>{source}</td>
        <td>{display_date}</td>
        <td><a href="{link}" target="_blank">Ver Noticia</a></td>
      </tr>'''

    html_content += '''
    </tbody>
  </table>
  <script>
    function filterTable() {
      const keyword = document.getElementById('keyword').value.toLowerCase();
      const startDate = document.getElementById('startDate').value;
      const endDate = document.getElementById('endDate').value;
      const daysFilter = parseInt(document.getElementById('daysFilter').value) || 0;
      const rows = document.querySelectorAll('#newsTable tbody tr');
      
      let filterStartDate = startDate;
      let filterEndDate = endDate;
      
      if (daysFilter > 0) {
        const today = new Date();
        const cutoff = new Date(today);
        cutoff.setDate(today.getDate() - (daysFilter - 1));
        filterStartDate = cutoff.toISOString().split('T')[0];
        filterEndDate = today.toISOString().split('T')[0];
      }
      
      rows.forEach(row => {
        const title = row.getAttribute('data-title');
        const date = row.getAttribute('data-date');
        let show = true;
        
        if (keyword && !title.includes(keyword)) show = false;
        if (filterStartDate && date !== '—' && date < filterStartDate) show = false;
        if (filterEndDate && date !== '—' && date > filterEndDate) show = false;
        
        row.style.display = show ? '' : 'none';
      });
    }
  </script>
</body>
</html>'''

    with open('visa_news.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    # --- ESPAÑOL: Guardado de JSON ---
    serializable_posts = []
    for post in all_posts:
        item = post.copy()
        if isinstance(item.get('date'), datetime):
            item['date'] = item['date'].isoformat()
        serializable_posts.append(item)

    with open('visa_data.json', 'w', encoding='utf-8') as f:
        json.dump(serializable_posts, f, ensure_ascii=False, indent=4)

    print(f"✅ Extracción completada. Se han guardado {len(serializable_posts)} noticias.")
    print("Los archivos 'visa_news.html' y 'visa_data.json' han sido generados con éxito.")

if __name__ == "__main__":
    import sys
    # Se establece por defecto en 30 días para alimentar el sistema
    main(30)
