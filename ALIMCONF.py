import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# URL du fichier CSV complet
CSV_URL = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

# Fonction pour charger les données depuis le CSV
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL, delimiter=';', parse_dates=['Date d\'inspection'])
    df.rename(columns={
        'Date d\'inspection': 'date_inspection',
        'Libellé de l\'établissement': 'app_libelle_etablissement',
        'Synthèse de l\'évaluation sanitaire': 'synthese_eval_sanit',
        'Activité de l\'établissement': 'app_libelle_activite_etablissement',
        'Type d\'activité': 'ods_type_activite',
        'Adresse 2 (UA)': 'adresse_2_ua',
        'Coordonnées géographiques': 'geores',
        'Catégorie': 'filtre'
    }, inplace=True)
    df['geores'] = df['geores'].apply(lambda x: {'lat': float(x.split(',')[0]), 'lon': float(x.split(',')[1])} if pd.notnull(x) else None)
    return df

# Charger les données
st.title('Données AlimConfiance')
df = load_data()

# Filtrer par plage de dates
start_date, end_date = st.sidebar.date_input(
    "Sélectionnez la période d'inspection",
    value=[pd.to_datetime("2023-01-01"), pd.to_datetime("2024-12-31")],
    min_value=pd.to_datetime("2015-01-01"),
    max_value=pd.to_datetime("2024-12-31")
)

df = df[(df['date_inspection'] >= pd.to_datetime(start_date)) & (df['date_inspection'] <= pd.to_datetime(end_date))]

if not df.empty:
    # Filtrage supplémentaire
    st.sidebar.title('Filtrage')

    all_levels = ['Tous', 'Très satisfaisant', 'Satisfaisant', 'A améliorer', 'A corriger de manière urgente']
    niveau_resultat = st.sidebar.selectbox("Niveau de résultat", all_levels)

    activite_etablissement_unique = df['app_libelle_activite_etablissement'].dropna().unique()
    activite_etablissement = st.sidebar.multiselect(
        "Activité de l'établissement", sorted(activite_etablissement_unique)
    )

    filtre_categorie_unique = df['filtre'].dropna().unique()
    filtre_categorie = st.sidebar.multiselect(
        "Catégorie de filtre", sorted(filtre_categorie_unique)
    )

    ods_type_activite = st.sidebar.multiselect(
        "Type d'activité", sorted(df['ods_type_activite'].unique())
    )

    nom_etablissement = st.sidebar.text_input("Nom de l'établissement")
    adresse = st.sidebar.text_input("Adresse")

    # Appliquer les filtres
    if niveau_resultat != 'Tous':
        df = df[df['synthese_eval_sanit'] == niveau_resultat]

    if activite_etablissement:
        df = df[df['app_libelle_activite_etablissement'].apply(lambda x: any(item in x for item in activite_etablissement))]

    if filtre_categorie:
        df = df[df['filtre'].apply(lambda x: any(item in x for item in filtre_categorie))]

    if ods_type_activite:
        df = df[df['ods_type_activite'].isin(ods_type_activite)]

    if nom_etablissement:
        df = df[df['app_libelle_etablissement'].str.contains(nom_etablissement, case=False)]

    if adresse:
        df = df[df['adresse_2_ua'].str.contains(adresse, case=False)]

    # Afficher la carte interactive
    st.subheader('Carte des établissements')
    map = folium.Map(location=[46.2276, 2.2137], zoom_start=6)
    for _, row in df.iterrows():
        if row['geores'] is not None:
            folium.Marker(
                location=[row['geores']['lat'], row['geores']['lon']],
                popup=row['app_libelle_etablissement'],
                tooltip=row['app_libelle_etablissement'],
                icon=folium.Icon(
                    color='green' if row['synthese_eval_sanit'] == 'Très satisfaisant' else 
                          'orange' if row['synthese_eval_sanit'] == 'Satisfaisant' else 
                          'red' if row['synthese_eval_sanit'] == 'A améliorer' else 'black',
                    icon='star',
                    prefix='fa'
                )
            ).add_to(map)

    folium_static(map, width=700, height=500)

    # Afficher les informations détaillées
    st.subheader('Données détaillées')
    st.write(df)

    # Permettre de télécharger les données filtrées
    csv = df.to_csv(index=False)
    st.download_button("Télécharger les données", csv, file_name="data.csv", mime="text/csv")
else:
    st.error("Aucune donnée disponible pour la période sélectionnée.")

