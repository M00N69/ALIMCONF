import streamlit as st
import pandas as pd
import requests
import folium

# Fonction pour récupérer les données de l'API
def get_data_from_api(year, month=None):
    url = f"https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/records?limit=100&refine=date_inspection%3A%22{year}%22"
    if month is not None:
        url += f"&refine=date_inspection%3A%22{year}-{month:02}%22"
    response = requests.get(url)
    data = response.json()
    
    if 'results' in data:
        df = pd.DataFrame(data['results'])
    else:
        st.error("Erreur : format de réponse JSON incorrect.")
        return None

    df['date_inspection'] = pd.to_datetime(df['date_inspection'])
    return df

# Fonction pour créer la carte interactive
def create_map(df):
    map_center = [46.2276, 2.2137]
    map = folium.Map(location=map_center, zoom_start=6)

    for _, row in df.iterrows():
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

# Interface utilisateur Streamlit
st.title('Données AlimConfiance')

# Récupérer les données de l'API
year = st.sidebar.selectbox("Année d'inspection", [2024, 2023])
month = st.sidebar.selectbox("Mois d'inspection", range(1, 13), format_func=lambda x: f"{x:02}")
df = get_data_from_api(year, month)

if df is not None:
    # Filtrage
    st.sidebar.title('Filtrage')

    niveau_resultat = st.sidebar.selectbox("Niveau de résultat", ['Tous'] + df['synthese_eval_sanit'].unique().tolist())

    activite_etablissement_unique = set()
    for activites in df['app_libelle_activite_etablissement']:
        activite_etablissement_unique.update(activites)

    activite_etablissement = st.sidebar.multiselect(
        "Activité de l'établissement", list(activite_etablissement_unique)
    )

    filtre_categorie_unique = set()
    for filtres in df['filtre']:
        if isinstance(filtres, list):
            filtre_categorie_unique.update(filtres)

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
        df = df[df['synthese_eval_sanit'] == niveau_resultat]
    
    if activite_etablissement:
        df = df[df['app_libelle_activite_etablissement'].apply(lambda x: any(item in x for item in activite_etablissement))]
    
    if filtre_categorie:
        df = df[df['filtre'].apply(lambda x: any(item in x for item in filtre_categorie) if isinstance(x, list) else False)]
    
    if ods_type_activite:
        df = df[df['ods_type_activite'].isin(ods_type_activite)]
    
    if nom_etablissement:
        df = df[df['app_libelle_etablissement'].str.contains(nom_etablissement, case=False)]
    
    if adresse:
        df = df[df['adresse_2_ua'].str.contains(adresse, case=False)]

    # Afficher la carte interactive
    st.subheader('Carte des établissements')
    map = create_map(df)
    st.components.v1.html(map._repr_html_(), width=700, height=500)

    # Afficher les informations détaillées
    st.subheader('Données détaillées')
    st.write(df)

    # Permettre de télécharger les données filtrées
    csv = df.to_csv(index=False)
    st.download_button("Télécharger les données", csv, file_name="data.csv", mime="text/csv")
else:
    st.error("Impossible de récupérer les données. Veuillez réessayer plus tard.")
