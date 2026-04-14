import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
from urllib.parse import urlparse
import main
import json
import time

# --- 1. Configuración ---
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

# --- 3. El núcleo de parsing lo proporciona main.py ---

# --- 4. Interfaz Streamlit ---
st.set_page_config(page_title="Asistente de Visados", layout="wide")
st.title("🌍 Extracción de noticias de visado")

# inicializar estado de sesión
if 'all_data' not in st.session_state:
    st.session_state.all_data = []

# selección de rango de fecha
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=2), format="DD-MM-YYYY")
with col2:
    end_date = st.date_input("Fecha fin", value=datetime.now(), format="DD-MM-YYYY")

# filtros
keyword = st.sidebar.text_input("Buscar palabra clave")
filter_days = st.sidebar.number_input("O seleccionar últimos días (opcional)", min_value=0, max_value=30, value=0, help="Si se rellena, sobrescribe el rango de fechas")

# --- 定义远程触发函数 ---
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
        st.error(f"Secret配置错误: {e}")
        return 0

# --- 修改后的按钮执行逻辑 ---
if st.sidebar.button("🚀 启动云端实时抓取"):
    with st.spinner("正在远程唤醒 GitHub 引擎以绕过防火墙..."):
        status = trigger_github_action()
        if status == 204:
            st.sidebar.success("✅ 指令已送达！")
            st.sidebar.warning("GitHub 正在抓取（约需1分钟），请稍后刷新。")
            # 进度条模拟
            bar = st.progress(0)

            for i in range(100):
                time.sleep(0.5)
                bar.progress(i + 1)
            st.rerun()


        else:
            st.sidebar.error(f"启动失败，请检查Secrets配置。错误码: {status}")

# --- 修改后的数据加载逻辑 (不再实时爬取，而是读JSON) ---
def load_saved_data():
    try:
        with open('visa_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data:
                if p['date']: p['date'] = pd.to_datetime(p['date'])
            return data
    except:
        return []

# 自动从JSON加载数据
st.session_state.all_data = load_saved_data()

# mostrar resultados y filtros
if st.session_state.all_data:
    df = pd.DataFrame(st.session_state.all_data).sort_values('date', ascending=False, na_position='last')
    df['Fecha'] = df['date'].dt.strftime('%d-%m-%Y').fillna('Desconocida')

    # filtro de resultados
    st.subheader("Filtrado de resultados")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        filter_keyword = st.text_input("Filtrar por palabra clave", key="result_keyword")
    with col_filter2:
        filter_start = st.date_input("Fecha inicio filtro", key="result_start", format="DD-MM-YYYY", value=None)
    with col_filter3:
        filter_end = st.date_input("Fecha fin filtro", key="result_end", format="DD-MM-YYYY", value=None)

    filter_days_option = st.number_input("Últimos días (0 = usar rango de fechas, 1 = Hoy, 2 = Hoy+ayer)", min_value=0, max_value=365, value=0, key="result_days")

    # aplicar filtro de resultados
    filtered_df = df.copy()

    # filtro por palabra clave
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

    def render_results_html(df):
        html = '''<div>
  <style>
    .visa-results-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .visa-results-table th, .visa-results-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    .visa-results-table th { background-color: #f2f2f2; }
    .visa-results-table a { color: #007bff; text-decoration: none; }
    .visa-results-table a:hover { text-decoration: underline; }
    .visa-results-table td strong { font-weight: bold; color: #000; }
  </style>
  <table class="visa-results-table">
    <thead>
      <tr>
        <th>Título</th>
        <th>Fuente</th>
        <th>Fecha</th>
        <th>Enlace</th>
      </tr>
    </thead>
    <tbody>'''
        for _, row in df.iterrows():
            title = row['title']
            source = row['source']
            fecha = row['Fecha']
            link = row['link']
            html += f'''
      <tr>
        <td><strong>{title}</strong></td>
        <td>{source}</td>
        <td>{fecha}</td>
        <td><a href="{link}" target="_blank">Abrir Enlace</a></td>
      </tr>'''
        html += '''
    </tbody>
  </table>
</div>'''
        return html

    st.markdown(render_results_html(filtered_df), unsafe_allow_html=True)

    def generate_html(df):
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
  <h1>Noticias de Visado Filtradas</h1>
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
        for _, row in df.iterrows():
            title = row['title']
            source = row['source']
            fecha = row['Fecha']
            link = row['link']
            row_date = row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else '—'
            html_content += f'''
      <tr data-date="{row_date}" data-title="{title.lower()}">
        <td><strong style='color:#000'>{title}</strong></td>
        <td>{source}</td>
        <td>{fecha}</td>
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
        return html_content

    # Botón de descarga HTML
    html_data = generate_html(filtered_df)
    st.download_button(
        label="Descargar resultados en HTML",
        data=html_data,
        file_name="visa_news_filtradas.html",
        mime="text/html"
    )

else:
    st.info("Primero haga clic en 'Ejecutar' en la barra lateral para obtener los datos.")
