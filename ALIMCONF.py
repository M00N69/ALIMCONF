import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# URL du fichier CSV complet
CSV_URL = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

# Fonction pour charger les données depuis le CSV
@st.cache_data
def load_data():
    # Chargement des données
    df = pd.read_csv(CSV_URL, delimiter=';', encoding='utf-8')

    # Renommer les colonnes pour correspondre à ce qui est attendu
    df.rename(columns={
        'Date_inspection': 'date_inspection',
        'Libelle_commune': 'libelle_commune',
        'SIRET': 'siret',
        'Adresse_2_UA': 'adresse_2_ua',
        'Code_postal': 'code_postal',
        'Libelle_commune': 'libelle_commune',
        'Numero_inspection': 'numero_inspection',
        'APP_Libelle_activite_etablissement': 'app_libelle_activite_etablissement',
        'Synthese_eval_sanit': 'synthese_eval_sanit',
        'APP_Code_synthese_eval_sanit': 'app_code_synthese_eval_sanit',
        'geores': 'geores',
        'filtre': 'filtre',
        'ods_type_activite': 'ods_type_activite'
    }, inplace=True)

    # Conversion des dates avec gestion des erreurs
    df['date_inspection'] = pd.to_datetime(df['date_inspection'], errors='coerce')

    # Vérifier s'il y a des valeurs non converties
    if df['date_inspection'].isnull().any():
        st.warning("Certaines dates n'ont pas pu être converties et seront ignorées.")

    # Filtrer les lignes avec des dates valides
    df = df[df['date_inspection'].notna()]

    # Extraire l'année et le mois pour faciliter le filtrage
    df['year_month'] = df['date_inspection'].dt.to_period('M')

    # Conversion des coordonnées géographiques en dictionnaires
    df['geores'] = df['geores'].apply(lambda x: {'lat': float(x.split(',')[0]), 'lon': float(x.split(',')[1])} if pd.notnull(x) else None)

    return df

# Charger les données
st.title('Données AlimConfiance')
df = load_data()

# Créer une liste des mois disponibles pour le filtrage
available_months = df['year_month'].dropna().unique()
available_months = sorted(available_months)

# Sélection de la plage de mois pour filtrer les données
start_month, end_month = st.sidebar.select_slider(
    "Sélectionnez la période d'inspection (mois)",
    options=available_months,
    value=(available_months[0], available_months[-1])
)

# Filtrer les données en fonction de la plage de mois sélectionnée
df_filtered = df[(df['year_month'] >= start_month) & (df['year_month'] <= end_month)]

if not df_filtered.empty:
    # Filtrage supplémentaire
    st.sidebar.title('Filtrage')

    all_levels = ['Tous', 'Très satisfaisant', 'Satisfaisant', 'A améliorer', 'A corriger de manière urgente']
    niveau_resultat = st.sidebar.selectbox("Niveau de résultat", all_levels)

    activite_etablissement_unique = df_filtered['app_libelle_activite_etablissement'].dropna().unique()
    activite_etablissement = st.sidebar.multiselect(
        "Activité de l'établissement", sorted(activite_etablissement_unique)
    )

    filtre_categorie_unique = df_filtered['filtre'].dropna().unique()
    filtre_categorie = st.sidebar.multiselect(
        "Catégorie de filtre", sorted(filtre_categorie_unique)
    )

    ods_type_activite = st.sidebar.multiselect(
        "Type d'activité", sorted(df_filtered['ods_type_activite'].unique())
    )

    nom_etablissement = st.sidebar.text_input("Nom de l'établissement")
    adresse = st.sidebar.text_input("Adresse")

    # Appliquer les filtres
    if niveau_resultat != 'Tous':
        df_filtered = df_filtered[df_filtered['synthese_eval_sanit'] == niveau_resultat]

    if activite_etablissement:
        df_filtered = df_filtered[df_filtered['app_libelle_activite_etablissement'].apply(lambda x: any(item in x for item in activite_etablissement))]

    if filtre_categorie:
        df_filtered = df_filtered[df_filtered['filtre'].apply(lambda x: any(item in x for item in filtre_categorie))]

    if ods_type_activite:
        df_filtered = df_filtered[df_filtered['ods_type_activite'].isin(ods_type_activite)]

    if nom_etablissement:
        df_filtered = df_filtered[df_filtered['app_libelle_etablissement'].str.contains(nom_etablissement, case=False)]

    if adresse:
        df_filtered = df_filtered[df_filtered['adresse_2_ua'].str.contains(adresse, case=False)]

    # Afficher la carte interactive
    st.subheader('Carte des établissements')
    map = folium.Map(location=[46.2276, 2.2137], zoom_start=6)
    for _, row in df_filtered.iterrows():
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
    st.write(df_filtered)

    # Permettre de télécharger les données filtrées
    csv = df_filtered.to_csv(index=False)
    st.download_button("Télécharger les données", csv, file_name="data.csv", mime="text/csv")
else:
    st.error("Aucune donnée disponible pour la période sélectionnée.")

