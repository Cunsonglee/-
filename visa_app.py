import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import streamlit_antd_components as sac
import re
from urllib.parse import urlparse
import main
import json
import time

# ==========================================
# 1. 基础国家列表 (标准名称)
# ==========================================
COUNTRY_LIST = [
    "Angola", "Armenia", "Australia", "Azerbaijan", "Benin", "Bahrain", 
    "Canada", "Ivory Coast", "Colombia", "Cuba", "Djibouti", "Dominican Republic", 
    "Egypt", "Ethiopia", "United Kingdom", "Guinea", "Indonesia", "India", 
    "Kenya", "Cambodia", "South Korea", "Kuwait", "Laos", "Sri Lanka", 
    "Madagascar", "Mexico", "Myanmar", "Nepal", "New Zealand", "Oman", 
    "Papua New Guinea", "Puerto Rico", "Rwanda", "Saudi Arabia", "Singapore", 
    "Thailand", "Turkey", "Tanzania", "Uganda", "USA", "Vietnam", 
    "Zambia", "Zimbabwe"
]

# ==========================================
# 2. 增强版：国家别名/变体字典 (全方位兼容不同叫法、国籍、西语)
# ==========================================
COUNTRY_ALIASES = {
    # 亚洲 & 大洋洲
    "South Korea": ["Korea", "Corea", "Corea del Sur", "ROK", "S. Korea", "South Korean", "Korean", "Surcoreano"],
    "Vietnam": ["Viet Nam", "Viet-nam", "Vietnamese", "Vietnamita"],
    "Thailand": ["Tailandia", "Thai", "Tailandés"],
    "Singapore": ["Singapur", "Singaporean", "Singapurense"],
    "Cambodia": ["Camboya", "Cambodian", "Camboyano"],
    "Myanmar": ["Burma", "Birmania", "Burmese"],
    "Indonesia": ["Indonesian", "Indonesio"],
    "India": ["Indian", "Indio"],
    "Sri Lanka": ["Sri Lankan", "Ceylon", "Ceylonese"],
    "Nepal": ["Nepali", "Nepalese", "Nepalí"],
    "Laos": ["Lao", "Laotian"],
    "Australia": ["Australian", "Australiano", "Aussie"],
    "New Zealand": ["Nueva Zelanda", "Nueva Zelandia", "New Zealand's", "NZ", "Kiwi", "New Zealander", "Neozelandés"],
    "Papua New Guinea": ["Papúa Nueva Guinea", "PNG", "Papuan"],
    
    # 中东 & 欧亚交界
    "Turkey": ["Turkiye", "Türkiye", "Turquia", "Turquía", "Turkish", "Turco"],
    "Saudi Arabia": ["Saudi", "Arabia Saudí", "Arabia Saudita", "KSA", "Saudi Arabian", "Saudí"],
    "Kuwait": ["Kuwaiti", "Kuwaití"],
    "Oman": ["Omán", "Omani", "Omaní"],
    "Bahrain": ["Baréin", "Bahrein", "Bahraini"],
    "Armenia": ["Armenian", "Armenio"],
    "Azerbaijan": ["Azerbaiyán", "Azerbaiyan", "Azerbaijani"],

    # 美洲
    "USA": ["US", "U.S.", "United States", "America", "Estados Unidos", "EEUU", "EE.UU.", "U.S.A.", "American", "Estadounidense"],
    "Canada": ["Canadá", "Canadian", "Canadiense"],
    "Mexico": ["México", "Mexican", "Mexicano"],
    "Colombia": ["Colombian", "Colombiano"],
    "Cuba": ["Cuban", "Cubano"],
    "Dominican Republic": ["Republica Dominicana", "República Dominicana", "Dominican"],
    "Puerto Rico": ["Puerto Rican", "Puertorriqueño", "Boricua"],
    
    # 非洲
    "Egypt": ["Egipto", "Egyptian", "Egipcio"],
    "Kenya": ["Kenia", "Kenyan", "Keniata"],
    "Ivory Coast": ["Cote d'Ivoire", "Côte d'Ivoire", "Costa de Marfil", "Ivorian"],
    "Djibouti": ["Yibuti", "Djiboutian"],
    "Ethiopia": ["Etiopía", "Etiopia", "Ethiopian", "Etíope"],
    "Madagascar": ["Malagasy", "Malgache"],
    "Rwanda": ["Ruanda", "Rwandan", "Ruandés"],
    "Tanzania": ["Tanzanian", "Tanzano"],
    "Uganda": ["Ugandan", "Ugandés"],
    "Zambia": ["Zambian", "Zambiano"],
    "Zimbabwe": ["Zimbabue", "Zimbabwean", "Zimbabuense"],
    "Angola": ["Angolan", "Angoleño"],
    "Benin": ["Benín", "Beninese"],
    "Guinea": ["Guinean", "Guineano"],

"United Kingdom": [
        # 核心称呼与国籍 (包含西语)
        "UK", "U.K.", "Britain", "Great Britain", "British", "Reino Unido", "Británico", "Británica",
        
        # 四大构成国 (Constituent Countries)
        "England", "Inglaterra", "English", "Inglés", 
        "Scotland", "Escocia", "Scottish", "Escocés",
        "Wales", "Gales", "Welsh", "Galés",
        "Northern Ireland", "Irlanda del Norte",
        
        # 皇家属地 (Crown Dependencies)
        "Isle of Man", "Isla de Man", "Jersey", "Guernsey",
        
        # 主要海外领土 (Overseas Territories)
        "Bermuda", "Bermudas", 
        "Cayman Islands", "Islas Caimán", "Cayman",
        "British Virgin Islands", "BVI", "Islas Vírgenes Británicas",
        "Gibraltar", 
        "Turks and Caicos", "Islas Turcas y Caicos",
        "Falkland Islands", "Islas Malvinas", "Falklands",
        "Anguilla", "Anguila",
        "Montserrat",
        "Pitcairn", "Pitcairn Islands", "Islas Pitcairn",
        "Saint Helena", "Santa Elena", "Ascension", "Tristan da Cunha"]
    
}

# --- 智能生成匹配词库 ---
ALL_MATCH_WORDS = []
for c in COUNTRY_LIST:
    ALL_MATCH_WORDS.append(re.sub(r'[^\w\s]', ' ', c.lower()).strip())
    if c in COUNTRY_ALIASES:
        for alias in COUNTRY_ALIASES[c]:
            ALL_MATCH_WORDS.append(re.sub(r'[^\w\s]', ' ', alias.lower()).strip())
ALL_MATCH_WORDS = list(set(ALL_MATCH_WORDS)) # 去重

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
    "https://travel.economictimes.indiatimes.com/news/visas-and-passports"
]

# --- 功能函数 ---
def scrape_website_updated(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        found = main.parse_items_from_html(html, url)
        return found
    except Exception as e:
        st.sidebar.error(f"Error {urlparse(url).netloc}: {e}")
        return []

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

# --- 界面配置 ---
st.set_page_config(page_title="Asistente de Visados Pro", layout="wide")
st.title("🌍 Extracción de noticias de visado")

if 'all_data' not in st.session_state:
    st.session_state.all_data = load_saved_data()

# --- 侧边栏 ---
st.sidebar.header("Parámetros de búsqueda")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=2), format="DD-MM-YYYY")
with col2:
    end_date = st.date_input("Fecha fin", value=datetime.now(), format="DD-MM-YYYY")

filter_days = st.sidebar.number_input("O seleccionar últimos días", min_value=0, max_value=30, value=0)

if st.sidebar.button("🚀 Iniciar extracción en la nube"):
    with st.spinner("Despertando GitHub Actions..."):
        status = trigger_github_action()
        if status == 204:
            st.sidebar.success("✅ ¡Orden enviada con éxito!")
            bar = st.progress(0)
            for i in range(100):
                time.sleep(0.5)
                bar.progress(i + 1)
            st.rerun()
        else:
            st.sidebar.error(f"Fallo al iniciar. Código: {status}")

# --- 主逻辑 ---
if st.session_state.all_data:
    df = pd.DataFrame(st.session_state.all_data)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.sort_values('date', ascending=False)
    # 格式化显示的日期，处理 NaT 为 Desconocida
    df['Fecha'] = df['date'].dt.strftime('%d-%m-%Y').fillna('Desconocida')

    # ==========================================
    # 顶部：三段式分类按钮 (Total / Tenemos / Pendiente)
    # ==========================================
    st.write("**Filtro de País:**")
    category = sac.segmented(
        items=[
            sac.SegmentedItem(label='Total', icon='globe'),
            sac.SegmentedItem(label='Pais tenemos', icon='check-circle'),
            sac.SegmentedItem(label='Pais pendiente', icon='question-circle'),
        ], align='center', use_container_width=True
    )

    # 智能匹配逻辑
    def check_country(title):
        if not isinstance(title, str): return False
        clean_title = f" {re.sub(r'[^\w\s]', ' ', title.lower())} "
        for keyword in ALL_MATCH_WORDS:
            if f" {keyword} " in clean_title:
                return True
        return False

    df['has_country'] = df['title'].apply(check_country)
    
    # 根据按钮选择过滤数据
    if category == 'Total':
        filtered_df = df.copy()
    elif category == 'Pais tenemos':
        filtered_df = df[df['has_country'] == True].copy()
    else:
        filtered_df = df[df['has_country'] == False].copy()

    # 原有侧边栏过滤逻辑
    st.markdown("---")
    st.subheader(f"Resultados de Búsqueda ({len(filtered_df)} artículos en {category})")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_keyword = st.text_input("Filtrar por palabra clave", key="result_keyword")
    with col_f2:
        filter_start = st.date_input("Fecha inicio filtro", key="result_start", format="DD-MM-YYYY", value=None)
    with col_f3:
        filter_end = st.date_input("Fecha fin filtro", key="result_end", format="DD-MM-YYYY", value=None)

    filter_days_option = st.number_input("Últimos días", min_value=0, max_value=365, value=0)

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

    # ==========================================
    # HTML 渲染风格 + 蓝色可点击 Fuente
    # ==========================================
    def render_results_html(df):
        html = '''<div>
  <style>
    .visa-results-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .visa-results-table th, .visa-results-table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    .visa-results-table th { background-color: #004a99; color: white; }
    .visa-results-table tr:nth-child(even) { background-color: #f2f2f2; }
    .visa-results-table a { color: #007bff; text-decoration: none; font-weight: bold; }
    .visa-results-table a:hover { text-decoration: underline; }
  </style>
  <table class="visa-results-table">
    <thead>
      <tr>
        <th>Título</th>
        <th>Fuente (Link)</th>
        <th>Fecha</th>
      </tr>
    </thead>
    <tbody>'''
        for _, row in df.iterrows():
            title = row['title']
            source = row['source']
            fecha = row['Fecha']
            link = row['link']
            # 这里将 Fuente 设置为蓝色的链接，并点击新标签打开
            html += f'''
      <tr>
        <td><strong>{title}</strong></td>
        <td><a href="{link}" target="_blank">{source}</a></td>
        <td>{fecha}</td>
      </tr>'''
        html += '</tbody></table></div>'
        return html

    # 在页面上显示 HTML 表格
    st.markdown(render_results_html(filtered_df), unsafe_allow_html=True)

    # ==========================================
    # 下载 HTML 区域（支持全选 / 打勾多选）
    # ==========================================
    st.markdown("---")
    st.markdown("### 📥 Descargar Resultados en HTML")
    
    # 选项：全选还是手动选择
    select_all = st.checkbox("✅ Seleccionar todos los artículos", value=True)
    
    if select_all:
        download_df = filtered_df
    else:
        st.write("👉 Marca las casillas de las noticias que deseas descargar:")
        # 创建一个带有打勾框的交互式表格供用户选择
        selection_df = filtered_df[['title', 'source', 'Fecha']].copy()
        selection_df.insert(0, "Descargar", False)
        
        edited_df = st.data_editor(
            selection_df,
            column_config={
                "Descargar": st.column_config.CheckboxColumn("Seleccionar ", default=False),
                "title": "Título",
                "source": "Fuente",
                "Fecha": "Fecha"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 获取用户打勾了的行的原始数据
        selected_indices = edited_df[edited_df["Descargar"]].index
        download_df = filtered_df.loc[selected_indices]

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
    a { color: #007bff; text-decoration: none; font-weight: bold; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>Noticias de Visado Filtradas</h1>
  <table id="newsTable">
    <thead>
      <tr><th>Título</th><th>Fuente</th><th>Fecha</th></tr>
    </thead>
    <tbody>'''
        for _, row in df.iterrows():
            # 下载版本同样包含了蓝色的链接
            html_content += f'''
      <tr>
        <td><strong>{row['title']}</strong></td>
        <td><a href="{row['link']}" target="_blank">{row['source']}</a></td>
        <td>{row['Fecha']}</td>
      </tr>'''
        html_content += '</tbody></table></body></html>'
        return html_content

    # 下载按钮
    if not download_df.empty:
        html_data = generate_html(download_df)
        st.download_button(
            label=f"📥 Descargar {len(download_df)} resultados",
            data=html_data,
            file_name=f"visa_news_{category.lower().replace(' ', '_')}.html",
            mime="text/html",
            type="primary"
        )
    else:
        st.warning("⚠️ No has seleccionado ninguna noticia para descargar.")

else:
    st.info("No hay datos disponibles. Haga clic en 'Iniciar extracción en la nube' en la barra lateral para actualizar.")
