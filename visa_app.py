import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
from deep_translator import GoogleTranslator
import streamlit_antd_components as sac
import re
from urllib.parse import urlparse
import main
import json
import time

# --- 0. 配置国家列表 (请在此处添加你需要匹配的国家名称) ---
COUNTRY_LIST = [
    "China", "India", "Thailand", "Vietnam", "Spain", "France", 
    "USA", "United Kingdom", "Japan", "South Korea", "Italy", "Germany"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

# --- 2. 修正后的抓取函数 ---
def scrape_website_updated(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        found = main.parse_items_from_html(html, url)
        return found
    except Exception as e:
        st.sidebar.error(f"抓取 {urlparse(url).netloc} 失败: {e}")
        return []

# --- 1. Configuración ---
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
    'jan': 0, 'january': 0, 'jan.': 0, 'januar': 0, 'feb': 1, 'february': 1, 'feb.': 1, 'mar': 2, 'march': 2, 'marz': 2,
    'apr': 3, 'april': 3, 'may': 4, 'mai': 4, 'jun': 5, 'june': 5, 'jul': 6, 'july': 6, 'aug': 7, 'august': 7,
    'sep': 8, 'september': 8, 'oct': 9, 'october': 9, 'nov': 10, 'november': 10, 'dec': 11, 'december': 11,
    'ene': 0, 'enero': 0, 'febrero': 1, 'marzo': 2, 'abril': 3, 'mayo': 4, 'junio': 5, 'julio': 6, 'agosto': 7,
    'septiembre': 8, 'octubre': 9, 'noviembre': 10, 'diciembre': 11
}

# --- 2. Funciones auxiliares ---
def parse_content(html, url):
    return main.parse_items_from_html(html, url)

# --- 4. Interfaz Streamlit ---
st.set_page_config(page_title="Asistente de Visados", layout="wide")
st.title("🌍 Extracción de noticias de visado")

# Inicializar estado de sesión
if 'all_data' not in st.session_state:
    st.session_state.all_data = []

# Selección de rango de fecha
st.sidebar.header("Parámetros de búsqueda")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=2), format="DD-MM-YYYY")
with col2:
    end_date = st.date_input("Fecha fin", value=datetime.now(), format="DD-MM-YYYY")

# Filtros
keyword = st.sidebar.text_input("Buscar palabra clave")
filter_days = st.sidebar.number_input("O seleccionar últimos días (opcional)", min_value=0, max_value=30, value=0, help="Si se rellena, sobrescribe el rango de fechas")

# --- Función para disparar GitHub Action ---
def trigger_github_action():
    try:
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

# --- Lógica del botón de ejecución ---
if st.sidebar.button("🚀 Iniciar extracción en la nube"):
    with st.spinner("Despertando el motor de GitHub para omitir bloqueos..."):
        status = trigger_github_action()
        if status == 204:
            st.sidebar.success("✅ ¡Orden enviada con éxito!")
            st.sidebar.warning("GitHub está trabajando (aprox. 1 min). Refresque en un momento.")
            
            bar = st.progress(0)
            for i in range(100):
                time.sleep(0.5)
                bar.progress(i + 1)
            st.rerun()
        else:
            st.sidebar.error(f"Fallo al iniciar. Revise la configuración de Secrets. Código: {status}")

# --- Lógica de carga de datos (desde JSON) ---
def load_saved_data():
    try:
        with open('visa_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data:
                if p.get('date'): 
                    p['date'] = pd.to_datetime(p['date'])
            return data
    except Exception:
        return []

# Carga automática de datos almacenados
st.session_state.all_data = load_saved_data()

# Mostrar resultados y filtros secundarios
if st.session_state.all_data:
    # 不在这里转换成字符串，保留 datetime 格式，这样 dataframe 的点击排序功能才能正确识别时间先后
    df = pd.DataFrame(st.session_state.all_data)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.sort_values('date', ascending=False)

    # ========================================================
    # 新增需求 1 & 4：国家筛选按钮与 Google 翻译
    # ========================================================
    top_col1, top_col2 = st.columns([2, 1])
    
    with top_col1:
        st.write("**Filtro de País:**")
        # 需求1：左右切换的国家分类按钮
        category = sac.segmented(
            items=[
                sac.SegmentedItem(label='Pais tenemos', icon='check-circle'),
                sac.SegmentedItem(label='Pais pendiente', icon='question-circle'),
            ], align='start', use_container_width=True
        )

    with top_col2:
        st.write("**Google Traductor:**")
        # 需求4：翻译功能
        lang_options = {"Original": None, "Spanish": "es", "English": "en", "Chinese": "zh-CN"}
        target_lang_name = st.selectbox("Seleccionar Idioma", list(lang_options.keys()), label_visibility="collapsed")
        
        if target_lang_name != "Original":
            if st.button("🔄 Traducir Títulos Ahora", use_container_width=True):
                with st.spinner('Traduciendo con Google...'):
                    target_code = lang_options[target_lang_name]
                    df['title'] = df['title'].apply(
                        lambda x: GoogleTranslator(source='auto', target=target_code).translate(str(x)) if pd.notna(x) else x
                    )

    # 逻辑处理：区分有无国家名称
    def check_country(title):
        if not isinstance(title, str): return False
        return any(c.lower() in title.lower() for c in COUNTRY_LIST)

    df['has_country'] = df['title'].apply(check_country)
    
    # 按照按钮选择过滤数据
    if category == 'Pais tenemos':
        filtered_df = df[df['has_country'] == True].copy()
    else:
        filtered_df = df[df['has_country'] == False].copy()

    # ========================================================
    # 应用你原有的侧边栏过滤逻辑 (日期、天数、关键词)
    # ========================================================
    st.markdown("---")
    st.subheader(f"Resultados de Búsqueda ({len(filtered_df)} artículos)")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        filter_keyword = st.text_input("Filtrar por palabra clave en resultados", key="result_keyword")
    with col_filter2:
        filter_start = st.date_input("Fecha inicio filtro", key="result_start", format="DD-MM-YYYY", value=None)
    with col_filter3:
        filter_end = st.date_input("Fecha fin filtro", key="result_end", format="DD-MM-YYYY", value=None)

    filter_days_option = st.number_input("Últimos días (0 = usar rango, 1 = Hoy, 2 = Hoy+Ayer)", min_value=0, max_value=365, value=0, key="result_days")

    if filter_keyword:
        filtered_df = filtered_df[filtered_df['title'].str.contains(filter_keyword, case=False, na=False)]

    if filter_days_option > 0:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = today - timedelta(days=filter_days_option - 1)
        filtered_df = filtered_df[filtered_df['date'] >= cutoff_date]
    elif filter_start or filter_end:
        start_dt = datetime.combine(filter_start, datetime.min.time()) if filter_start else datetime.min
        end_dt = datetime.combine(filter_end, datetime.max.time()) if filter_end else datetime.max
        filtered_df = filtered_df[(filtered_df['date'] >= start_dt) & (filtered_df['date'] <= end_dt)]

    # ========================================================
    # 新增需求 2 & 3：交互式表格（支持上下箭头排序、蓝色链接）
    # ========================================================
    # 将包含原网址的 link 列配置为蓝色的 LinkColumn。Streamlit 原生表格最稳定的做法是将具体跳转做成独立链接列。
    
    st.dataframe(
        filtered_df[['title', 'source', 'date', 'link']],
        column_config={
            "title": st.column_config.TextColumn(
                "Título (↕️ Clic para ordenar)", 
                width="large"
            ),
            "source": st.column_config.TextColumn(
                "Fuente (↕️)",
                width="medium"
            ),
            "date": st.column_config.DatetimeColumn(
                "Fecha (↕️)", 
                format="DD-MM-YYYY",
                width="small"
            ),
            "link": st.column_config.LinkColumn(
                "Enlace de Noticia (Azul)", 
                display_text="Abrir Enlace 🔗", 
                help="Haz clic para abrir en una nueva pestaña"
            )
        },
        hide_index=True,
        use_container_width=True
    )

    # ========================================================
    # 导出下载的 HTML 逻辑 (保持你的原有代码)
    # ========================================================
    def generate_html(df):
        html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Noticias de Visado Filtradas</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
    th { background-color: #f2f2f2; }
    a { color: #007bff; text-decoration: none; }
    .filters { margin-bottom: 20px; }
  </style>
</head>
<body>
  <h1>Noticias de Visado Filtradas</h1>
  <table id="newsTable">
    <thead>
      <tr><th>Título</th><th>Fuente</th><th>Fecha</th><th>Enlace</th></tr>
    </thead>
    <tbody>'''
        for _, row in df.iterrows():
            f_date = row['date'].strftime('%d-%m-%Y') if pd.notnull(row['date']) else 'Desconocida'
            html_content += f'''
      <tr>
        <td><strong>{row['title']}</strong></td>
        <td>{row['source']}</td>
        <td>{f_date}</td>
        <td><a href="{row['link']}" target="_blank">Ver Noticia</a></td>
      </tr>'''
        html_content += '</tbody></table></body></html>'
        return html_content

    # Botón de descarga
    html_data = generate_html(filtered_df)
    st.download_button(
        label="📥 Descargar resultados en HTML",
        data=html_data,
        file_name="visa_news_filtradas.html",
        mime="text/html"
    )

else:
    st.info("No hay datos disponibles. Haga clic en 'Iniciar extracción en la nube' en la barra lateral para actualizar la información.")
