import streamlit as st
import pandas as pd
import requests
import folium

# Fonction pour récupérer les données de l'API
def get_data_from_api(year, month=None):
    url = f"https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/records?limit=20&refine=date_inspection%3A%22{year}%22"
    if month is not None:
        url += f"&refine=date_inspection%3A%22{year}-{month:02}%22"
    response = requests.get(url)
    data = response.json()
    
    # Vérifier si la clé "results" existe dans la réponse
    if 'results' in data:
        df = pd.DataFrame(data['results'])
    else:
        st.error("Erreur : format de réponse JSON incorrect.")
        return None

    df['date_inspection'] = pd.to_datetime(df['date_inspection'])
    return df

# Fonction pour créer la carte interactive
def create_map(df):
    # Créer une carte centrée sur la France
    map_center = [46.2276, 2.2137]
    map = folium.Map(location=map_center, zoom_start=6)

    # Créer des marqueurs pour chaque site
    for index, row in df.iterrows():
        if row['geores'] is not None:
            latitude = row['geores']['lat']
            longitude = row['geores']['lon']
            tooltip = row['app_libelle_etablissement']
            folium.Marker(
                location=[latitude, longitude],
                popup=row['app_libelle_etablissement'],
                tooltip=tooltip,
                icon=folium.Icon(color='green' if row['synthese_eval_sanit'] == 'Très satisfaisant' else 'orange' if row['synthese_eval_sanit'] == 'Satisfaisant' else 'red' if row['synthese_eval_sanit'] == 'A améliorer' else 'black', icon='star', prefix='fa')
            ).add_to(map)

    return map

# Récupérer les données de l'API
year = st.sidebar.selectbox("Année d'inspection", [2024, 2023])  # Ajouter d'autres années si nécessaire
month = st.sidebar.selectbox("Mois d'inspection", range(1, 13), format_func=lambda x: f"{x:02}")
df = get_data_from_api(year, month)

# Créer le menu latéral
st.sidebar.title('Filtrage')

# Filtrage par niveau de résultat
niveau_resultat = st.sidebar.selectbox("Niveau de résultat", ['Très satisfaisant', 'Satisfaisant', 'A améliorer', 'Non conforme'])

# Vérifier si les données ont été récupérées correctement avant d'afficher les menus
if df is not None:
    # Aplatir la colonne app_libelle_activite_etablissement
    activite_etablissement_unique = set()
    for activites in df['app_libelle_activite_etablissement']:
        for activite in activites:
            activite_etablissement_unique.add(activite)

    # Aplatir la colonne filtre
    filtre_categorie_unique = set()
    for categories in df['filtre']:  # Correction: Utiliser 'filtre' (sans 'fields.')
        if categories is not None:
            for categorie in categories:
                filtre_categorie_unique.add(categorie)

    # Filtrage par activité
    activite_etablissement = st.sidebar.multiselect(
        "Activité de l'établissement", list(activite_etablissement_unique)
    )

    # Filtrage par filtre
    filtre_categorie = st.sidebar.multiselect(
        "Catégorie de filtre", list(filtre_categorie_unique)
    )

    # Filtrage par ods_type_activite
    ods_type_activite = st.sidebar.multiselect(
        "Type d'activité", df['ods_type_activite'].unique()
    )

    # Recherche par nom d'établissement et adresse
    nom_etablissement = st.sidebar.text_input("Nom de l'établissement")
    adresse = st.sidebar.text_input("Adresse")

    # Appliquer les filtres
    df = df[df['synthese_eval_sanit'] == niveau_resultat]
    df = df[df['app_libelle_activite_etablissement'].apply(lambda x: any(item in x for item in activite_etablissement))]
    df = df[df['filtre'].apply(lambda x: any(item in x for item in filtre_categorie) if x is not None else False)]  # Correction: Utiliser 'filtre' (sans 'fields.')
    df = df[df['ods_type_activite'].isin(ods_type_activite)]
    df = df[df['app_libelle_etablissement'].str.contains(nom_etablissement)]
    df = df[df['adresse_2_ua'].str.contains(adresse)]

    # Afficher la carte interactive
    st.map(create_map(df))

    # Afficher les informations détaillées
    st.write(df)

    # Permettre de télécharger les données filtrées
    csv = df.to_csv(index=False)
    st.download_button("Télécharger les données", csv, file_name="data.csv", mime="text/csv")
