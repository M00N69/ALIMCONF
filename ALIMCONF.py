import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# Fonction pour récupérer les données de l'API
def get_data_from_api(year, month=None):
    url = f"https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/records?refine=date_inspection%3A%22{year}%22"
    if month is not None:
        url += f"&refine=date_inspection%3A%22{year}-{month:02}%22"
    response = requests.get(url)
    data = response.json()

    if 'results' in data:
        df = pd.DataFrame(data['results'])
    else:
        st.error("Erreur : format de réponse JSON incorrect.")
        return None

    if 'date_inspection' in df.columns:
        df['date_inspection'] = pd.to_datetime(df['date_inspection'])
    else:
        st.error("Erreur : la colonne 'date_inspection' est manquante.")
        return None

    return df

# Interface utilisateur Streamlit
st.title('Données AlimConfiance')

# Slider pour sélectionner l'année et le mois
start_year, end_year = st.sidebar.slider(
    "Sélectionnez la période d'inspection (année)",
    min_value=2015,
    max_value=2024,
    value=(2023, 2024),
    step=1
)

# Récupérer les données de l'API pour chaque année de la période
dfs = []
for year in range(start_year, end_year + 1):
    df = get_data_from_api(year)
    if df is not None:
        dfs.append(df)

# Concatenate data for all selected years
if dfs:
    df = pd.concat(dfs, ignore_index=True)
else:
    st.error("Aucune donnée disponible pour la période sélectionnée.")
    df = None

if df is not None:
    # Filtrage
    st.sidebar.title('Filtrage')

    all_levels = ['Tous', 'Très satisfaisant', 'Satisfaisant', 'A améliorer', 'A corriger de manière urgente']
    niveau_resultat = st.sidebar.selectbox("Niveau de résultat", all_levels)

    activite_etablissement_unique = set()
    for activites in df['app_libelle_activite_etablissement']:
        activite_etablissement_unique.update(activites)
    activite_etablissement = st.sidebar.multiselect(
        "Activité de l'établissement", sorted(activite_etablissement_unique)
    )

    filtre_categorie_unique = set()
    for filtres in df['filtre']:
        if isinstance(filtres, list):
            filtre_categorie_unique.update(filtres)
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
        df = df[df['filtre'].apply(lambda x: any(item in x for item in filtre_categorie) if isinstance(x, list) else False)]

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
    st.error("Impossible de récupérer les données. Veuillez réessayer plus tard.")
