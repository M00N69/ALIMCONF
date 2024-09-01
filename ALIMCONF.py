import streamlit as st
import pandas as pd
import folium
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Fonction pour récupérer les données du CSV
def get_data():
    url = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
    df = pd.read_csv(url, sep=";")
    df['Date_inspection'] = pd.to_datetime(df['Date_inspection'], format='%Y-%m-%dT%H:%M:%S%z')
    return df

# Fonction pour convertir les coordonnées en float de manière sûre
def safe_float(value):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None

# Fonction pour créer la carte interactive
def create_map(df):
    map_center = [46.2276, 2.2137]
    map = folium.Map(location=map_center, zoom_start=6)

    for _, row in df.iterrows():
        if pd.notna(row['geores']) and isinstance(row['geores'], str):
            coords = row['geores'].split(',')
            if len(coords) == 2:
                latitude = safe_float(coords[0])
                longitude = safe_float(coords[1])
                if latitude is not None and longitude is not None:
                    tooltip = row['APP_Libelle_etablissement']
                    folium.Marker(
                        location=[latitude, longitude],
                        popup=row['APP_Libelle_etablissement'],
                        tooltip=tooltip,
                        icon=folium.Icon(color='green' if row['Synthese_eval_sanit'] == 'Très satisfaisant' else 'orange' if row['Synthese_eval_sanit'] == 'Satisfaisant' else 'red' if row['Synthese_eval_sanit'] == 'A améliorer' else 'black', icon='star', prefix='fa')
                    ).add_to(map)

    return map

# Interface utilisateur Streamlit
st.set_page_config(layout="wide")
st.title('Données AlimConfiance')

# Récupérer les données du CSV
df = get_data()

# Créer un slider pour sélectionner la plage de dates
start_date = datetime(2023, 9, 1)
end_date = datetime.now()

months = pd.date_range(start=start_date, end=end_date, freq='MS')
selected_start, selected_end = st.select_slider(
    "Sélectionnez la plage de dates",
    options=months,
    value=(months[-2], months[-1]),
    format_func=lambda x: x.strftime('%B %Y')
)

# Convertir les dates sélectionnées en datetime
selected_start = pd.to_datetime(selected_start).tz_localize('UTC')
selected_end = pd.to_datetime(selected_end).tz_localize('UTC') + relativedelta(months=1) - timedelta(days=1)

# Filtrer les données en fonction de la plage de dates sélectionnée
df_filtered = df[(df['Date_inspection'] >= selected_start) & (df['Date_inspection'] <= selected_end)]

# Filtres pour Synthese_eval_sanit et APP_Libelle_activite_etablissement
synthese_options = ['Tous'] + list(df_filtered['Synthese_eval_sanit'].unique())
selected_synthese = st.selectbox("Filtrer par Synthèse d'évaluation sanitaire", synthese_options)

activite_options = ['Tous'] + list(df_filtered['APP_Libelle_activite_etablissement'].unique())
selected_activite = st.selectbox("Filtrer par Activité de l'établissement", activite_options)

if selected_synthese != 'Tous':
    df_filtered = df_filtered[df_filtered['Synthese_eval_sanit'] == selected_synthese]

if selected_activite != 'Tous':
    df_filtered = df_filtered[df_filtered['APP_Libelle_activite_etablissement'] == selected_activite]

# Afficher la carte interactive
st.subheader('Carte des établissements')
map = create_map(df_filtered)
st.components.v1.html(map._repr_html_(), width=1200, height=600)

# Afficher les informations détaillées
st.subheader('Données détaillées des établissements')
st.dataframe(df_filtered)

# Permettre de télécharger les données filtrées
csv = df_filtered.to_csv(index=False)
st.download_button("Télécharger les données", csv, file_name="data_filtered.csv", mime="text/csv")

# Afficher la fiche complète d'un site sélectionné avec un meilleur design
if not df_filtered.empty:
    selected_site = st.selectbox("Sélectionner un site", df_filtered['APP_Libelle_etablissement'])
    selected_site_data = df_filtered[df_filtered['APP_Libelle_etablissement'] == selected_site].iloc[0]
    st.subheader('Fiche complète du site sélectionné')
    
    # CSS pour un design attrayant et professionnel
    st.markdown("""
    <style>
    .site-info {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .site-info h3 {
        color: #0e1117;
        border-bottom: 2px solid #0e1117;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .site-info p {
        margin-bottom: 10px;
    }
    .site-info strong {
        color: #0e1117;
    }
    </style>
    """, unsafe_allow_html=True)

    # Fonction pour obtenir une valeur sûre
    def safe_get(data, key, default="Non spécifié"):
        return data[key] if key in data and pd.notna(data[key]) else default

    # Affichage des informations du site
    st.markdown(f"""
    <div class="site-info">
        <h3>{safe_get(selected_site_data, 'APP_Libelle_etablissement')}</h3>
        <p><strong>Adresse:</strong> {safe_get(selected_site_data, 'Adresse_2_UA')}</p>
        <p><strong>Code postal:</strong> {safe_get(selected_site_data, 'Code_postal_UA')}</p>
        <p><strong>Commune:</strong> {safe_get(selected_site_data, 'Libelle_commune_UA')}</p>
        <p><strong>Activité:</strong> {safe_get(selected_site_data, 'APP_Libelle_activite_etablissement')}</p>
        <p><strong>Date d'inspection:</strong> {selected_site_data['Date_inspection'].strftime('%d/%m/%Y')}</p>
        <p><strong>Synthèse de l'évaluation sanitaire:</strong> {safe_get(selected_site_data, 'Synthese_eval_sanit')}</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.write("Aucun établissement trouvé dans la période sélectionnée.")
