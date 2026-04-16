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
# 2. 终极版：国家别名/变体字典 (已优化搜索词顺序)
# ==========================================
COUNTRY_ALIASES = {
    # 亚洲 & 大洋洲
    "South Korea": [
        "Korea", "Corea", "Corea del Sur", "ROK", "S. Korea", 
        "South Korean", "South Koreans", "Korean", "Koreans",
        "Surcoreano", "Surcoreanos", "Surcoreana", "Surcoreanas", 
        "Coreano", "Coreanos", "Coreana", "Coreanas"
    ],
    "Vietnam": ["Viet Nam", "Vietnamita", "Viet-nam", "Vietnamese", "Vietnamitas"],
    "Thailand": ["Tailandia", "Thai", "Thais", "Tailandés", "Tailandeses", "Tailandesa", "Tailandesas"],
    "Singapore": ["Singapur", "Singaporean", "Singaporeans", "Singapurense", "Singapurenses"],
    "Cambodia": ["Camboya", "Cambodian", "Cambodians", "Camboyano", "Camboyanos", "Camboyana", "Camboyanas"],
    "Myanmar": ["Burma", "Birmania", "Burmese", "Birmano", "Birmanos", "Birmana", "Birmanas"],
    "Indonesia": ["Indonesian", "Indonesio", "Indonesians", "Indonesios", "Indonesia", "Indonesias"],
    "India": ["Indian", "Indio", "Indians", "Indios", "India", "Indias"],
    "Sri Lanka": ["Sri Lankan", "Ceylon", "Sri Lankans", "Ceilanés", "Ceilaneses", "Ceilanesa", "Ceilanesas"],
    "Nepal": ["Nepali", "Nepalí", "Nepalis", "Nepalese", "Nepalíes", "Nepaleses"],
    "Laos": ["Lao", "Laos", "Laotian", "Laotians", "Laosiano", "Laosianos", "Laosiana", "Laosianas"],
    "Australia": [
        "Australian", "Australiano", "Australians", "Aussie", "Aussies", 
        "Australianos", "Australiana", "Australianas"
    ],
    "New Zealand": [
        "NZ", "Nueva Zelanda", "Kiwi", "New Zealand's", "Nueva Zelandia", 
        "New Zealander", "New Zealanders", "Kiwis", 
        "Neozelandés", "Neozelandeses", "Neozelandesa", "Neozelandesas"
    ],
    "Papua New Guinea": ["PNG", "Papúa Nueva Guinea", "Papuan", "Papuans", "Papú", "Papúes"],
    
    # 中东 & 欧亚交界
    "Turkey": [
        "Turquía", "Turkiye", "Turco", "Türkiye", "Turquia", 
        "Turkish", "Turk", "Turks", "Turcos", "Turca", "Turcas"
    ],
    "Saudi Arabia": [
        "Arabia Saudí", "Arabia Saudita", "KSA", "Saudi", "Saudis", 
        "Saudi Arabian", "Saudi Arabians", "Saudí", "Saudíes", "Saudita", "Sauditas"
    ],
    "Kuwait": ["Kuwaiti", "Kuwaití", "Kuwaitis", "Kuwaitíes"],
    "Oman": ["Omán", "Omani", "Omanis", "Omaní", "Omaníes"],
    "Bahrain": ["Baréin", "Bahrein", "Bahraini", "Bahrainis", "Bahreiní", "Bahreiníes"],
    "Armenia": ["Armenian", "Armenio", "Armenians", "Armenios", "Armenia", "Armenias"],
    "Azerbaijan": ["Azerbaiyán", "Azerbaiyan", "Azerbaijani", "Azerbaijanis", "Azeri", "Azeris", "Azerbaiyano", "Azerbaiyanos"],

    # 美洲
    "USA": [
        "US", "EEUU", "Estados Unidos", "United States", "America", "U.S.", "EE.UU.", "U.S.A.", 
        "American", "Americans", "Estadounidense", "Estadounidenses", "Norteamericano", "Norteamericanos"
    ],
    "Canada": ["Canadá", "Canadian", "Canadiense", "Canadians", "Canadienses"],
    "Mexico": ["México", "Mexican", "Mexicano", "Mexicans", "Mexicanos", "Mexicana", "Mexicanas"],
    "Colombia": ["Colombian", "Colombiano", "Colombians", "Colombianos", "Colombiana", "Colombianas"],
    "Cuba": ["Cuban", "Cubano", "Cubans", "Cubanos", "Cubana", "Cubanas"],
    "Dominican Republic": [
        "Republica Dominicana", "República Dominicana", "Dominicano",
        "Dominican", "Dominicans", "Dominicanos", "Dominicana", "Dominicanas"
    ],
    "Puerto Rico": [
        "Puerto Rican", "Puertorriqueño", "Boricua", "Puerto Ricans", "Boricuas", 
        "Puertorriqueños", "Puertorriqueña", "Puertorriqueñas"
    ],
    
    # 非洲
    "Egypt": ["Egipto", "Egyptian", "Egipcio", "Egyptians", "Egipcios", "Egipcia", "Egipcias"],
    "Kenya": ["Kenia", "Kenyan", "Keniano", "Kenyans", "Kenianos", "Keniana", "Kenianas", "Keniata", "Keniatas"],
    "Ivory Coast": ["Costa de Marfil", "Cote d'Ivoire", "Côte d'Ivoire", "Ivorian", "Ivorians", "Marfileño", "Marfileños"],
    "Djibouti": ["Yibuti", "Djiboutian", "Djiboutians", "Yibutiano", "Yibutianos"],
    "Ethiopia": ["Etiopía", "Ethiopian", "Etíope", "Etiopia", "Ethiopians", "Etíopes"],
    "Madagascar": ["Malagasy", "Malgache", "Malagasies", "Malgaches"],
    "Rwanda": ["Ruanda", "Rwandan", "Ruandés", "Rwandans", "Ruandeses", "Ruandesa", "Ruandesas"],
    "Tanzania": ["Tanzanian", "Tanzano", "Tanzanians", "Tanzanos", "Tanzana", "Tanzanas"],
    "Uganda": ["Ugandan", "Ugandés", "Ugandans", "Ugandeses", "Ugandesa", "Ugandesas"],
    "Zambia": ["Zambian", "Zambiano", "Zambians", "Zambianos", "Zambiana", "Zambianas"],
    "Zimbabwe": ["Zimbabue", "Zimbabwean", "Zimbabuense", "Zimbabweans", "Zimbabuenses"],
    "Angola": ["Angolan", "Angoleño", "Angolans", "Angoleños", "Angoleña", "Angoleñas"],
    "Benin": ["Benín", "Beninese", "Beninés", "Benineses", "Beninesa", "Beninesas"],
    "Guinea": ["Guinean", "Guineano", "Guineans", "Guineanos", "Guineana", "Guineanas"],

    # 英国及其海外领地
    "United Kingdom": [
        "UK", "Reino Unido", "England", "Inglaterra", "Britain", "Great Britain", "British", 
        "U.K.", "Briton", "Britons", "Británico", "Británicos", "Británica", "Británicas",
        "English", "Englishmen", "Inglés", "Ingleses", "Inglesa", "Inglesas",
        "Scotland", "Escocia", "Scottish", "Scot", "Scots", "Escocés", "Escoceses", "Escocesa", "Escocesas",
        "Wales", "Gales", "Welsh", "Welshmen", "Galés", "Galeses", "Galesa", "Galesas",
        "Northern Ireland", "Irlanda del Norte", "Northern Irish", "Norirlandés", "Norirlandeses",
        "Isle of Man", "Isla de Man", "Mann", "Manx", "Manxman", "Manxmen", "Manxwoman", "Manxwomen", 
        "Manés", "Maneses", "Manesa", "Manesas",        
        "Jersey", "Bailiwick of Jersey", "Bailiazgo de Jersey", "Jerseyman", "Jerseymen", "Jerseywoman", "Jerseywomen",
        "Guernsey", "Guernesey", "Bailiwick of Guernsey", "Bailiazgo de Guernsey", "Guernseyman", "Guernseymen", "Guernseywoman", "Guernseywomen",
        "Channel Islands", "Channel Island", "Islas del Canal", "Isla del Canal",
        "Channel Islander", "Channel Islanders", "Anglonormando", "Anglonormandos", "Anglonormanda", "Anglonormandas",
        "Bermuda", "Bermudas", "Bermudian", "Bermudians", "Bermudeño", "Bermudeños",
        "Cayman Islands", "Islas Caimán", "Cayman", "Caymanian", "Caymanians", "Caimanés", "Caimaneses",
        "British Virgin Islands", "BVI", "Islas Vírgenes Británicas", "Virgin Islander", "Virgin Islanders",
        "Gibraltar", "Gibraltarian", "Gibraltarians", "Gibraltareño", "Gibraltareños",
        "Turks and Caicos", "Islas Turcas y Caicos",
        "Falkland Islands", "Islas Malvinas", "Falklands", "Falklander", "Falklanders", "Malvinense", "Malvinenses",
        "Anguilla", "Anguila", "Anguillan", "Anguillans", "Anguilano", "Anguilanos",
        "Montserrat", "Montserratian", "Montserratians", "Montserratense", "Montserratenses",
        "Pitcairn", "Pitcairn Islands", "Islas Pitcairn",
        "Saint Helena", "Santa Elena", "Ascension", "Tristan da Cunha"
    ]
}

# ==========================================
# 3. 生成反向映射表 (用于提取具体国家名)
# ==========================================
ALIAS_TO_STANDARD = {}
for std_name in COUNTRY_LIST:
    clean_std = f" {re.sub(r'[^\w\s]', ' ', std_name.lower()).strip()} "
    ALIAS_TO_STANDARD[clean_std] = std_name
    if std_name in COUNTRY_ALIASES:
        for alias in COUNTRY_ALIASES[std_name]:
            clean_alias = f" {re.sub(r'[^\w\s]', ' ', alias.lower()).strip()} "
            ALIAS_TO_STANDARD[clean_alias] = std_name

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
st.sidebar.header("⚙️ Parámetros de búsqueda")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=2), format="DD-MM-YYYY")
with col2:
    end_date = st.date_input("Fecha fin", value=datetime.now(), format="DD-MM-YYYY")

filter_days = st.sidebar.number_input("O seleccionar últimos días", min_value=0, max_value=45, value=0)

st.sidebar.markdown("---")
if st.sidebar.button("🚀 Iniciar extracción en la nube", use_container_width=True):
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
    
    st.write("") # 空出一行美化排版

    # ==========================================
    # 移动到主界面：特定国家多选筛选器 (支持通过别名/缩写搜索)
    # ==========================================
    def format_country_search(country):
        """格式化下拉框显示，将最常用的前 5 个别名附加在括号里，实现别名搜索功能"""
        if country in COUNTRY_ALIASES and COUNTRY_ALIASES[country]:
            # 取前 5 个最具代表性的别名（已在字典头部排好序）
            aliases = COUNTRY_ALIASES[country][:5]
            return f"{country} ({', '.join(aliases)})"
        return country

    st.subheader("🎯 Filtro de País Específico")
    selected_countries_filter = st.multiselect(
        "Selecciona uno o más países para buscar:", 
        options=sorted(COUNTRY_LIST),
        format_func=format_country_search, # 核心：使用自定义显示函数以支持搜索
        help="Puedes buscar por siglas (ej. UK, US, NZ) o en español (ej. Reino Unido, Corea)."
    )

    # ==========================================
    # 智能提取具体国家名称并判断分类
    # ==========================================
    def extract_countries(title):
        if not isinstance(title, str): return []
        clean_title = f" {re.sub(r'[^\w\s]', ' ', title.lower())} "
        found = set()
        for alias, std_name in ALIAS_TO_STANDARD.items():
            if alias in clean_title:
                found.add(std_name)
        return list(found)

    df['matched_countries'] = df['title'].apply(extract_countries)
    # 如果识别出的国家列表长度 > 0，说明它是 Pais tenemos
    df['has_country'] = df['matched_countries'].apply(lambda x: len(x) > 0)
    
    # 1. 根据顶部三段按钮过滤
    if category == 'Total':
        filtered_df = df.copy()
    elif category == 'Pais tenemos':
        filtered_df = df[df['has_country'] == True].copy()
    else:
        filtered_df = df[df['has_country'] == False].copy()

    # 2. 根据主界面的【特定国家筛选器】进行二次过滤
    if selected_countries_filter:
        filtered_df = filtered_df[filtered_df['matched_countries'].apply(lambda x: any(c in selected_countries_filter for c in x))]

    # 3. 原有侧边栏过滤逻辑
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
    # HTML 渲染风格 + 蓝色可点击 Fuente + 显示国家
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
        <th>País Detectado</th>
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
            # 将检测到的国家用逗号拼接，没有就显示 -
            detected = ", ".join(row['matched_countries']) if row['matched_countries'] else "-"
            
            html += f'''
      <tr>
        <td><strong>{title}</strong></td>
        <td><span style="color: #d9534f; font-weight: bold;">{detected}</span></td>
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
    
    select_all = st.checkbox("✅ Seleccionar todos los artículos", value=True)
    
    if select_all:
        download_df = filtered_df
    else:
        st.write("👉 Marca las casillas de las noticias que deseas descargar:")
        
        # 为复选框表格准备数据，并把列表转成字符串以便显示
        selection_df = filtered_df[['title', 'matched_countries', 'source', 'Fecha']].copy()
        selection_df['matched_countries'] = selection_df['matched_countries'].apply(lambda x: ", ".join(x) if x else "-")
        selection_df.insert(0, "Descargar", False)
        
        edited_df = st.data_editor(
            selection_df,
            column_config={
                "Descargar": st.column_config.CheckboxColumn("Seleccionar ", default=False),
                "title": "Título",
                "matched_countries": "País Detectado",
                "source": "Fuente",
                "Fecha": "Fecha"
            },
            hide_index=True,
            use_container_width=True
        )
        
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
      <tr><th>Título</th><th>País Detectado</th><th>Fuente</th><th>Fecha</th></tr>
    </thead>
    <tbody>'''
        for _, row in df.iterrows():
            detected = ", ".join(row['matched_countries']) if row['matched_countries'] else "-"
            html_content += f'''
      <tr>
        <td><strong>{row['title']}</strong></td>
        <td>{detected}</td>
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
