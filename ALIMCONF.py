import streamlit as st
import pandas as pd
import requests
import folium
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Fonction pour récupérer les données du CSV
def get_data():
    url = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
    df = pd.read_csv(url, sep=";")
    df['Date_inspection'] = pd.to_datetime(df['Date_inspection'], format='%Y-%m-%dT%H:%M:%S%z')
    return df

# Fonction pour créer la carte interactive
def create_map(df):
    map_center = [46.2276, 2.2137]
    map = folium.Map(location=map_center, zoom_start=6)

    for _, row in df.iterrows():
        if pd.notna(row['geores']) and isinstance(row['geores'], str):
            try:
                coords = row['geores'].split(',')
                if len(coords) == 2:
                    latitude, longitude = map(float, coords)
                    tooltip = row['APP_Libelle_etablissement']
                    folium.Marker(
                        location=[latitude, longitude],
                        popup=row['APP_Libelle_etablissement'],
                        tooltip=tooltip,
                        icon=folium.Icon(color='green' if row['Synthese_eval_sanit'] == 'Très satisfaisant' else 'orange' if row['Synthese_eval_sanit'] == 'Satisfaisant' else 'red' if row['Synthese_eval_sanit'] == 'A améliorer' else 'black', icon='star', prefix='fa')
                    ).add_to(map)
                else:
                    st.warning(f"Format de coordonnées invalide pour l'établissement : {row['APP_Libelle_etablissement']}")
            except ValueError:
                st.warning(f"Coordonnées invalides pour l'établissement : {row['APP_Libelle_etablissement']}")
        else:
            st.warning(f"Données de géolocalisation manquantes pour l'établissement : {row['APP_Libelle_etablissement']}")

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

# Filtrer les inspections "à améliorer"
df_a_ameliorer = df_filtered[df_filtered['Synthese_eval_sanit'] == 'A améliorer']

# Afficher la carte interactive
st.subheader('Carte des établissements à améliorer')
map = create_map(df_a_ameliorer)
st.components.v1.html(map._repr_html_(), width=1200, height=600)

# Afficher les informations détaillées
st.subheader('Données détaillées des établissements à améliorer')
st.dataframe(df_a_ameliorer)

# Permettre de télécharger les données filtrées
csv = df_a_ameliorer.to_csv(index=False)
st.download_button("Télécharger les données", csv, file_name="data_a_ameliorer.csv", mime="text/csv")

# Afficher la fiche complète d'un site sélectionné
if not df_a_ameliorer.empty:
    selected_site = st.selectbox("Sélectionner un site", df_a_ameliorer['APP_Libelle_etablissement'])
    selected_site_data = df_a_ameliorer[df_a_ameliorer['APP_Libelle_etablissement'] == selected_site].iloc[0]
    st.subheader('Fiche complète du site sélectionné')
    st.write(selected_site_data)
else:
    st.write("Aucun établissement à améliorer trouvé dans la période sélectionnée.")
