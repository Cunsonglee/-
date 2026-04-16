import requests
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re
import time
import os

# --- CONFIGURACIÓN DE SITIOS WEB ---
# Lista de sitios para extraer (Business Standard eliminado por bloqueo de IP en la nube)
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

# Mapeo de meses para normalización de fechas
MONTHS = {
    'jan': 0, 'january': 0, 'jan.': 0, 'januar': 0, 'ene': 0, 'enero': 0,
    'feb': 1, 'february': 1, 'feb.': 1, 'februar': 1, 'febrero': 1,
    'mar': 2, 'march': 2, 'märz': 2, 'mär': 2, 'marz': 2, 'marzo': 2,
    'apr': 3, 'april': 3, 'apr.': 3, 'abr': 3, 'abril': 3,
    'may': 4, 'mai': 4, 'mayo': 4,
    'jun': 5, 'june': 5, 'juni': 5, 'junio': 5,
    'jul': 6, 'july': 6, 'juli': 6, 'julio': 6,
    'aug': 7, 'august': 7, 'ago': 7, 'agosto': 7,
    'sep': 8, 'sept': 8, 'september': 8, 'septiembre': 8,
    'oct': 9, 'october': 9, 'okt': 9, 'oktober': 9, 'octubre': 9,
    'nov': 10, 'november': 10, 'noviembre': 10,
    'dec': 11, 'december': 11, 'dez': 11, 'dezember': 11, 'dic': 11, 'diciembre': 11
}

# --- FUNCIONES DE UTILIDAD ---

def normalize_date(dt):
    """Elimina información de zona horaria para compatibilidad."""
    if not dt: return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt

def safe_datetime(year, month, day):
    """Crea un objeto datetime de forma segura."""
    try: return datetime(year, month, day)
    except: return None

def absolute_url(href, base):
    """Convierte URLs relativas en absolutas."""
    if not href: return ""
    if href.startswith('http'): return href
    return base.rstrip('/') + '/' + href.lstrip('/')

# --- FUNCIONES DE PROCESAMIENTO (PARSING) ---

def parse_day_month_year(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.search(r'(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+),?\s+(\d{4})', t)
    if not m: return None
    day, mon_key, year = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
    month_idx = MONTHS.get(mon_key)
    if month_idx is None: return None
    return safe_datetime(year, month_idx + 1, day)

def parse_month_day_year(text):
    t = re.sub(r'\s+', ' ', (text or '')).strip()
    m = re.search(r'([A-Za-zÀ-ÿ\.]+)\s+(\d{1,2}),\s*(\d{4})', t)
    if not m: return None
    mon_key, day, year = m.group(1).lower()[:3], int(m.group(2)), int(m.group(3))
    month_idx = MONTHS.get(mon_key)
    if month_idx is None: return None
    return safe_datetime(year, month_idx + 1, day)

# (Aquí se incluyen los procesadores específicos para cada sitio)

def parse_vne(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for n in soup.select('.item-news, .item_news'):
        a = n.select_one('h4.title_news_site a[href]')
        if not a: continue
        title, link = a.get_text().strip(), absolute_url(a.get('href'), base_url)
        date = None
        t_el = n.select_one('.timer_post')
        if t_el: date = parse_month_day_year(t_el.get_text())
        out.append({'title': title, 'link': link, 'date': date, 'date_text': t_el.get_text().strip() if t_el else '—', 'source': 'vnexpress'})
    return out

def parse_vn(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for post in soup.select('article.post'):
        a = post.select_one('h2.entry-title a[href]')
        if not a: continue
        title, link = a.get_text().strip(), absolute_url(a.get('href'), base_url)
        time_el = post.select_one('time')
        date = None
        if time_el and time_el.get('datetime'):
            try: date = normalize_date(datetime.fromisoformat(time_el.get('datetime').replace('Z', '+00:00')))
            except: pass
        out.append({'title': title, 'link': link, 'date': date, 'date_text': time_el.get_text().strip() if time_el else '—', 'source': 'visasnews'})
    return out

def parse_et_travel(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for a in soup.find_all('a', href=True):
        h = a.find(['h2', 'h3'])
        if not h or len(h.get_text().strip()) < 15: continue
        link = absolute_url(a['href'], base_url)
        if '/news/' in link or '/blog/' in link:
            out.append({'title': h.get_text().strip(), 'link': link, 'date': None, 'date_text': '—', 'source': 'et-travel'})
    return out[:10] # Limitar para evitar lentitud

# --- MOTOR DE EXTRACCIÓN ---

def parse_items_from_html(html, base_url):
    from urllib.parse import urlparse
    host = urlparse(base_url).netloc
    if 'e.vnexpress.net' in host: return parse_vne(html, base_url)
    if 'visasnews.com' in host: return parse_vn(html, base_url)
    if 'economictimes' in host: return parse_et_travel(html, base_url)
    # Por defecto, búsqueda genérica de títulos y enlaces
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for a in soup.find_all('a', href=True):
        title = a.get_text().strip()
        if len(title) > 20 and ('visa' in title.lower() or 'passport' in title.lower()):
            out.append({'title': title, 'link': absolute_url(a['href'], base_url), 'date': None, 'date_text': '—', 'source': host})
    return out

def scrape_website(url):
    """Intenta obtener el contenido de un sitio web."""
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
        response = scraper.get(url, timeout=20)
        if response.status_code == 200:
            return parse_items_from_html(response.text, url)
    except Exception as e:
        print(f"Error al extraer {url}: {e}")
    return []

# --- FUNCIÓN PRINCIPAL DE EJECUCIÓN ---

def run_main_extraction(days_limit=3):
    """
    Función para ser llamada desde la App o de forma automática.
    Implementa actualización incremental y eliminación de duplicados.
    """
    print(f"[{datetime.now()}] Iniciando extracción incremental (últimos {days_limit} días)...")
    
    new_found_data = []
    cutoff = datetime.now() - timedelta(days=days_limit)

    # 1. Realizar la extracción de cada sitio
    for url in websites:
        print(f"  -> Procesando: {url}")
        items = scrape_website(url)
        for item in items:
            dt = item.get('date')
            # Mantener si es reciente o si no tiene fecha (para validar después)
            if not dt or dt >= cutoff:
                new_found_data.append(item)

    # 2. Cargar base de datos existente para evitar duplicados
    file_path = 'visa_data.json'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try: existing_db = json.load(f)
            except: existing_db = []
    else:
        existing_db = []

    # Crear set de enlaces para búsqueda rápida
    existing_links = {doc['link'] for doc in existing_db}
    added_count = 0

    # 3. Integrar solo noticias nuevas
    for post in new_found_data:
        if post['link'] not in existing_links:
            # Serializar fecha para JSON
            if isinstance(post.get('date'), datetime):
                post['date'] = post['date'].isoformat()
            existing_db.append(post)
            existing_links.add(post['link'])
            added_count += 1

    # 4. Ordenar por fecha (las más recientes primero)
    existing_db.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)

    # 5. Guardar archivos de salida
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_db, f, ensure_ascii=False, indent=4)
    
    # Generar el HTML compatible con los filtros de la App
    generate_static_html(existing_db)

    print(f"✅ Proceso completado: {added_count} noticias nuevas añadidas.")
    print(f"📊 Total en base de datos: {len(existing_db)} noticias.")
    return added_count, len(existing_db)

def generate_static_html(data):
    """Genera el archivo visa_news.html para visualización rápida."""
    html_template = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Reporte de Visados</title>
        <style>
            body {{ font-family: sans-serif; background: #f4f4f4; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; background: white; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background: #004a99; color: white; }}
            tr:nth-child(even) {{ background: #f9f9f9; }}
            a {{ color: #007bff; text-decoration: none; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Noticias de Visados Actualizadas</h1>
        <p>Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <table>
            <tr><th>Título</th><th>Fuente</th><th>Fecha</th><th>Acción</th></tr>
    '''
    for item in data[:100]: # Mostrar últimas 100 en el HTML estático
        date_display = item.get('date_text', '—')
        html_template += f'''
            <tr>
                <td>{item['title']}</td>
                <td>{item['source']}</td>
                <td>{date_display}</td>
                <td><a href="{item['link']}" target="_blank">Leer más</a></td>
            </tr>'''
    
    html_template += "</table></body></html>"
    with open('visa_news.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

if __name__ == "__main__":
    # Ejecución por defecto de 3 días para mantenimiento diario
    run_main_extraction(days_limit=3)
