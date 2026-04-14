import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re

# List of websites to scrape
websites = [
    "https://www.buch-dein-visum.de/en/news",
    "https://visasnews.com/en/africa-news/",
    "https://visasnews.com/en/america-news/",
    "https://visasnews.com/en/asia-news/",
    "https://visasnews.com/en/europe-news/",
    "https://visasnews.com/en/oceania-news/",
    "https://visasnews.com/en/travel-news/",
    "https://www.visamundi.co/es/blog/seccion/noticias/",
    "https://e.vnexpress.net/news/travel/visa",
    "https://atta.travel/news.html?sortBy=recent&topic_categories=visa",
    "https://visadone.com/news/",
    "https://www.bal.com/immigration-news/",
    "https://www.fragomen.com/insights/index.html?nt=news",
    "https://travelobiz.com/category/visas-passports/"
]

# Month mapping
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
    items = soup.select('.list_news_folder .item_news')
    out = []
    for n in items:
        a = n.select_one('h4.title_news_site a[href]')
        if not a:
            continue
        title = a.get_text().strip()
        link = absolute_url(a.get('href'), base_url)
        t = n.select_one('.timer_post')
        date_text = ''
        date = None
        if t:
            raw = t.get_text().strip()
            m = re.search(r'([A-Za-zÀ-ÿ\.]+\s+\d{1,2},\s*\d{4})', raw)
            if m:
                date_text = m.group(1)
                date = parse_month_day_year(date_text)
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'vnexpress'})
    return out

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
    # Dedupe
    seen = set()
    return [it for it in out if not (it['link'] in seen or seen.add(it['link']))]

def parse_bal_short_date(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.search(r'^(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+)\s+(\d{2,4})$', t)
    if not m:
        return None
    day = int(m.group(1))
    mon_key = m.group(2).lower()
    year = int(m.group(3))
    if year < 100:
        year += 2000
    month_idx = MONTHS.get(mon_key)
    if month_idx is None:
        return None
    return safe_datetime(year, month_idx + 1, day)


def parse_bal_post_title(html):
    soup = BeautifulSoup(html, 'html.parser')
    title_el = soup.select_one('h1.line-under') or soup.select_one('title')
    if title_el:
        return title_el.get_text(strip=True)
    og_title = soup.select_one('meta[property="og:title"]')
    if og_title and og_title.get('content'):
        return og_title.get('content').strip()
    return ''


def parse_bal_sitemap(base_url, max_items=30):
    out = []
    try:
        sitemap_url = 'https://www.bal.com/sitemap-posttype-bal_news.xml'
        response = requests.get(sitemap_url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/"
}, timeout=15)
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
                post_resp = requests.get(loc, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/"
}, timeout=15)
                post_resp.raise_for_status()
                title = parse_bal_post_title(post_resp.text)
            except Exception:
                title = ''
            if not title:
                title = loc.rstrip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            out.append({'title': title, 'link': loc, 'date': date, 'date_text': date_text, 'source': 'bal'})
    except Exception:
        pass
    return out


def parse_bal(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    items = soup.select('div.recommended-box, .recommended-box')
    for it in items:
        title_el = it.select_one('a.recommended-box__link h3.line-under') or it.select_one('h3.line-under')
        title = title_el.get_text().strip() if title_el else ''
        link_el = it.select_one('a.recommended-box__link[href], a.post-img-wrap[href]') or it.select_one('a[href*="/immigration-news/"]')
        if not link_el:
            continue
        link = absolute_url(link_el.get('href'), base_url)
        date_el = it.select_one('span[style*="font-size: 1.5rem"], span[style*="font-weight: 400"]')
        if not date_el:
            date_el = it.find('span', string=re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}\b', re.I))
        date_text = date_el.get_text().strip() if date_el else ''
        date = parse_month_day_year(date_text) if date_text else None
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'bal'})

    if out:
        return out

    return parse_bal_sitemap(base_url)

def parse_fragomen(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    anchors = soup.select('a.galleryView')
    for a in anchors:
        title_el = a.select_one('span.rte-title-mode')
        if not title_el:
            continue
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
    # Dedupe
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
    arts = soup.select('.articles-wrapper article, article.post')
    out = []
    for a in arts:
        t_a = a.select_one('h2.entry-title a[href]')
        if not t_a:
            continue
        title = t_a.get_text().strip()
        link = absolute_url(t_a.get('href'), base_url)
        date = None
        date_text = ''
        time_pub = a.select_one('time.entry-date[datetime], time.published[datetime]')
        time_upd = a.select_one('time.updated[datetime]')
        pick = time_pub or time_upd
        if pick:
            date_text = pick.get_text().strip()
            iso = pick.get('datetime')
            if iso:
                try:
                    parsed = datetime.fromisoformat(iso.replace('Z', '+00:00'))
                    date = normalize_date(parsed)
                except:
                    pass
        if not date:
            raw = a.select_one('.entry-meta .posted-on') or a
            raw_text = raw.get_text()
            date = parse_es_date(raw_text)
            if date:
                date_text = raw_text.strip()
        if title and link:
            out.append({'title': title, 'link': link, 'date': date, 'date_text': date_text, 'source': 'visamundi'})
    return out

def parse_items_from_html(html, base_url):
    host = ''
    try:
        from urllib.parse import urlparse
        host = urlparse(base_url).netloc
    except:
        pass

    if 'e.vnexpress.net' in host:
        return parse_vne(html, base_url)
    if 'visasnews.com' in host:
        return parse_vn(html, base_url)
    if 'buch-dein-visum.de' in host:
        return parse_bdv(html, base_url)
    if 'atta.travel' in host:
        return parse_atta(html, base_url)
    if 'visamundi.co' in host:
        return parse_visamundi(html, base_url)
    if 'visadone.com' in host:
        return parse_visadone(html, base_url)
    if 'bal.com' in host:
        return parse_bal(html, base_url)
    if 'fragomen.com' in host:
        return parse_fragomen(html, base_url)
    if 'travelobiz.com' in host:
        return parse_travelobiz(html, base_url)
    # Default
    return parse_bdv(html, base_url) + parse_vn(html, base_url)

# Function to scrape a website
def scrape_website(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        html = response.text
        posts = parse_items_from_html(html, url)
        return posts
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

# Main function
def main(days=3):
    all_posts = []
    days = max(days, 1)
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
                all_posts.append(post)  # Include if no date

    # Sort by date descending
    all_posts.sort(key=lambda x: x.get('date') or datetime.min, reverse=True)

    # Generate HTML
    html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Análisis de noticias de visado</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f2f2f2; }
    a { color: #007bff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .filters { margin-bottom: 20px; }
    .filters input, .filters button { margin-right: 10px; padding: 5px; }
    .filters input[type="number"] { width: 120px; }
  </style>
</head>
<body>
  <h1>Noticias de Visado Recientes</h1>
  <div class="filters">
    <input type="text" id="keyword" placeholder="Buscar palabra clave">
    <input type="date" id="startDate">
    <input type="date" id="endDate">
    <input type="number" id="daysFilter" placeholder="O filtrar últimos días" min="0">
    <button onclick="filterTable()">Filtrar</button>
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
        display_date = date.strftime('%d-%m-%Y') if date else '—'
        link = post.get('link', '')
        html_content += f'''
      <tr data-date="{row_date}" data-title="{title.lower()}">
        <td><strong style='color:#000'>{title}</strong></td>
        <td>{source}</td>
        <td>{display_date}</td>
        <td><a href="{link}" target="_blank" style="color:#007bff; text-decoration:none;">Abrir Enlace</a></td>
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
      
      // Calcular rango de fechas
      let filterStartDate = startDate;
      let filterEndDate = endDate;
      
      if (daysFilter > 0) {
        const today = new Date();
        const cutoffDate = new Date(today);
        cutoffDate.setDate(today.getDate() - (daysFilter - 1));
        filterStartDate = cutoffDate.toISOString().split('T')[0];
        filterEndDate = today.toISOString().split('T')[0];
      }
      
      rows.forEach(row => {
        const title = row.getAttribute('data-title');
        const date = row.getAttribute('data-date');
        let show = true;
        
        if (keyword && !title.includes(keyword)) {
          show = false;
        }
        
        if (filterStartDate && date !== '—' && date < filterStartDate) {
          show = false;
        }
        
        if (filterEndDate && date !== '—' && date > filterEndDate) {
          show = false;
        }
        
        row.style.display = show ? '' : 'none';
      });
    }
  </script>
</body>
</html>'''

    with open('visa_news.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("Scraping complete. Output saved to visa_news.html")

if __name__ == "__main__":
    import sys
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    main(days)
