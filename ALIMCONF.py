import streamlit as st
import pandas as pd
import requests
import folium
from datetime import datetime

# Fonction pour récupérer les données du fichier CSV
def get_data(use_csv=True):
    if use_csv:
        url = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
        df = pd.read_csv(url, sep=";")
    else:
        st.error("Impossible de récupérer les données : seul le mode CSV est disponible.")
        return None

    # Convertir les dates en format datetime
    df['Date_inspection'] = pd.to_datetime(df['Date_inspection'], errors='coerce')

    return df

# Fonction pour créer la carte interactive
def create_map(df):
    map_center = [46.2276, 2.2137]
    map = folium.Map(location=map_center, zoom_start=6)

    for _, row in df.iterrows():
        if pd.notna(row['geores']):
            latitude, longitude = map(float, row['geores'].split(','))
            tooltip = row['APP_Libelle_etablissement']
            folium.Marker(
                location=[latitude, longitude],
                popup=row['APP_Libelle_etablissement'],
                tooltip=tooltip,
                icon=folium.Icon(color='green' if row['Synthese_eval_sanit'] == 'Très satisfaisant' else 'orange' if row['Synthese_eval_sanit'] == 'Satisfaisant' else 'red' if row['Synthese_eval_sanit'] == 'A améliorer' else 'black', icon='star', prefix='fa')
            ).add_to(map)

    return map

# Interface utilisateur Streamlit
st.set_page_config(layout="wide")  # Set page layout to wide

st.title('Données AlimConfiance')

# Récupérer les données du fichier CSV
df = get_data()

if df is not None:
    # Filtrage
    st.sidebar.title('Filtrage')

    # Liste complète des niveaux de résultat possibles
    all_levels = ['Tous', 'Très satisfaisant', 'Satisfaisant', 'A améliorer', 'A corriger de manière urgente']

    niveau_resultat = st.sidebar.selectbox("Niveau de résultat", all_levels)

    activite_etablissement_unique = df['APP_Libelle_activite_etablissement'].unique()
    activite_etablissement = st.sidebar.multiselect(
        "Activité de l'établissement", activite_etablissement_unique
    )

    filtre_categorie_unique = set()
    for filtres in df['filtre'].dropna():
        if isinstance(filtres, str):
            filtre_categorie_unique.update(filtres.split(','))

    filtre_categorie = st.sidebar.multiselect(
        "Catégorie de filtre", list(filtre_categorie_unique)
    )

    ods_type_activite = st.sidebar.multiselect(
        "Type d'activité", df['ods_type_activite'].unique()
    )

    nom_etablissement = st.sidebar.text_input("Nom de l'établissement")
    adresse = st.sidebar.text_input("Adresse")

    # Appliquer les filtres
    if niveau_resultat != 'Tous':
        df = df[df['Synthese_eval_sanit'] == niveau_resultat]

    if activite_etablissement:
        df = df[df['APP_Libelle_activite_etablissement'].isin(activite_etablissement)]

    if filtre_categorie:
        df = df[df['filtre'].apply(lambda x: any(item in x.split(',') for item in filtre_categorie) if isinstance(x, str) else False)]

    if ods_type_activite:
        df = df[df['ods_type_activite'].isin(ods_type_activite)]

    if nom_etablissement:
        df = df[df['APP_Libelle_etablissement'].str.contains(nom_etablissement, case=False)]

    if adresse:
        df = df[df['Adresse_2_UA'].str.contains(adresse, case=False)]

    # Afficher la carte interactive
    st.subheader('Carte des établissements')
    map = create_map(df)
    st.components.v1.html(map._repr_html_(), width=1200, height=600)

    # Afficher les informations détaillées
    st.subheader('Données détaillées')
    st.markdown(df.style.set_properties(**{'text-align': 'center'}).to_html(), unsafe_allow_html=True)

    # Permettre de télécharger les données filtrées
    csv = df.to_csv(index=False)
    st.download_button("Télécharger les données", csv, file_name="data.csv", mime="text/csv")

    # Afficher la fiche complète d'un site sélectionné
    selected_site = st.selectbox("Sélectionner un site", df['APP_Libelle_etablissement'])
    selected_site_data = df[df['APP_Libelle_etablissement'] == selected_site].iloc[0]
    st.subheader('Fiche complète du site sélectionné')
    st.write(selected_site_data)
else:
    st.error("Impossible de récupérer les données. Veuillez réessayer plus tard.")

