import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import main  # Conexión con el extractor

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Daily Visa Scraper", layout="wide")

# --- 2. BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("⚙️ Configuración y Reglas")

st.sidebar.subheader("1. Rango de Fechas (Vista)")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_dt = st.sidebar.date_input("Desde", datetime.now() - timedelta(days=7))
with col2:
    end_dt = st.sidebar.date_input("Hasta", datetime.now())

days_slider = st.sidebar.slider("O filtrar últimos X días", 1, 60, 7)

st.sidebar.markdown("---")
st.sidebar.subheader("2. Ejecución en la Nube")
if st.sidebar.button("🚀 Iniciar extracción en la nube"):
    with st.spinner(f"Extrayendo noticias de los últimos {days_slider} días..."):
        added, total = main.run_main_extraction(days_limit=days_slider)
        st.sidebar.success(f"¡Éxito! {added} noticias nuevas.")
        st.rerun()

# --- 3. PANEL PRINCIPAL ---
st.title("🌍 Extracción de noticias de visado")

if os.path.exists('visa_data.json'):
    # A. Mostrar última actualización
    mtime = os.path.getmtime('visa_data.json')
    last_sync = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')
    st.info(f"📅 **Última sincronización de Daily Visa Scraper:** {last_sync} (UTC)")

    # B. Cargar datos
    with open('visa_data.json', 'r', encoding='utf-8') as f:
        db_data = json.load(f)
    
    df = pd.DataFrame(db_data)
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')

    # C. Aplicar filtros (Instantáneo)
    # Filtro por Slider
    cutoff = datetime.now() - timedelta(days=days_slider)
    filtered = df[df['date_dt'] >= pd.to_datetime(cutoff)].copy()
    
    # Filtro por Calendario
    filtered = filtered[(filtered['date_dt'].dt.date >= start_dt) & 
                        (filtered_df['date_dt'].dt.date <= end_dt)] if 'filtered' in locals() else filtered
    
    filtered = filtered.sort_values(by='date_dt', ascending=False)

    # D. Selección y Tabla Interactiva
    st.subheader(f"📋 Resultados actuales: {len(filtered)} noticias")
    
    filtered.insert(0, "Seleccionar", True)
    
    # Editor de datos para seleccionar noticias
    edited_df = st.data_editor(
        filtered.drop(columns=['date_dt', 'date']),
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Selección", default=True),
            "link": st.column_config.LinkColumn("Enlace"),
            "title": "Título",
            "source": "Fuente",
            "date_text": "Publicado el"
        },
        disabled=["title", "source", "date_text", "link"],
        hide_index=True,
        use_container_width=True
    )

    # E. Función de descarga
    selected_news = edited_df[edited_df["Seleccionar"] == True]
    
    def make_html(df_rows):
        html = """<html><head><meta charset='utf-8'><style>
        body { font-family: Arial; } table { width:100%; border-collapse:collapse; }
        th, td { border:1px solid #ccc; padding:8px; text-align:left; }
        th { background:#f2f2f2; } a { color:#007bff; text-decoration:none; }
        </style></head><body><h1>Reporte de Visados</h1><table>
        <tr><th>Título</th><th>Fuente</th><th>Fecha</th></tr>"""
        for _, row in df_rows.iterrows():
            html += f"<tr><td><a href='{row['link']}'>{row['title']}</a></td><td>{row['source']}</td><td>{row['date_text']}</td></tr>"
        html += "</table></body></html>"
        return html

    if not selected_news.empty:
        st.download_button(
            label=f"📥 Descargar {len(selected_news)} noticias seleccionadas (HTML)",
            data=make_html(selected_news),
            file_name=f"visa_noticias_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
    else:
        st.warning("Seleccione al menos una noticia para habilitar la descarga.")

else:
    st.warning("⚠️ No se encontró visa_data.json. Inicie una extracción en la barra lateral.")
