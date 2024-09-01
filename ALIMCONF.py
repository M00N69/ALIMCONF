import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# URL du fichier CSV complet
CSV_URL = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

# Fonction pour charger les données depuis le CSV
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL, delimiter=';', encoding='utf-8')

    # Afficher un aperçu des données brutes
    st.write("Aperçu des données avant manipulation:", df.head())

    # Vérifier les types de colonnes avant conversion
    st.write("Types de données avant conversion:", df.dtypes)

    # Forcer la conversion en datetime avec une gestion stricte des erreurs
    try:
        df['Date_inspection'] = pd.to_datetime(df['Date_inspection'], errors='coerce')
    except Exception as e:
        st.error(f"Erreur lors de la conversion de 'Date_inspection': {e}")

    # Vérifier les types après conversion
    st.write("Types de données après conversion:", df.dtypes)

    # Vérifier s'il y a des valeurs non converties
    if df['Date_inspection'].isnull().any():
        st.warning("Certaines dates n'ont pas pu être converties en datetime. Les lignes correspondantes seront supprimées.")
        st.write(df[df['Date_inspection'].isnull()])

    # Supprimer les lignes où la conversion a échoué
    df = df.dropna(subset=['Date_inspection'])

    # Extraire la partie date seulement (sans l'heure)
    df['Date_inspection'] = df['Date_inspection'].dt.date

    return df

# Charger les données
st.title('Données AlimConfiance')
df = load_data()

# Vérification des données chargées
st.write("Aperçu des données après conversion:", df.head())

if not df.empty:
    # Filtrer sur le dernier mois et "A améliorer"
    last_month = pd.to_datetime(df['Date_inspection'].max()).to_period('M').to_timestamp()
    df_filtered = df[(pd.to_datetime(df['Date_inspection']) >= last_month) & (df['Synthese_eval_sanit'] == 'A améliorer')]

    # Ajout des filtres dans la barre latérale
    st.sidebar.title('Filtres supplémentaires')

    activite_etablissement_unique = df_filtered['APP_Libelle_activite_etablissement'].dropna().unique()
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

    # Appliquer les filtres supplémentaires
    if activite_etablissement:
        df_filtered = df_filtered[df_filtered['APP_Libelle_activite_etablissement'].apply(lambda x: any(item in x for item in activite_etablissement))]

    if filtre_categorie:
        df_filtered = df_filtered[df_filtered['filtre'].apply(lambda x: any(item in x for item in filtre_categorie))]

    if ods_type_activite:
        df_filtered = df_filtered[df_filtered['ods_type_activite'].isin(ods_type_activite)]

    if nom_etablissement:
        df_filtered = df_filtered[df_filtered['APP_Libelle_etablissement'].str.contains(nom_etablissement, case=False)]

    if adresse:
        df_filtered = df_filtered[df_filtered['Adresse_2_UA'].str.contains(adresse, case=False)]

    if not df_filtered.empty:
        # Afficher la carte interactive
        st.subheader('Carte des établissements "A améliorer" (Dernier Mois)')
        map = folium.Map(location=[46.2276, 2.2137], zoom_start=6)
        for _, row in df_filtered.iterrows():
            if pd.notnull(row['geores']):
                latitude, longitude = map(float, row['geores'].split(','))
                folium.Marker(
                    location=[latitude, longitude],
                    popup=row['APP_Libelle_etablissement'],
                    tooltip=row['APP_Libelle_etablissement'],
                    icon=folium.Icon(color='red', icon='star', prefix='fa')
                ).add_to(map)

        folium_static(map, width=700, height=500)

        # Afficher les informations détaillées
        st.subheader('Données détaillées des établissements "A améliorer" (Dernier Mois)')
        st.write(df_filtered)

        # Permettre de télécharger les données filtrées
        csv = df_filtered.to_csv(index=False)
        st.download_button("Télécharger les données", csv, file_name="data_a_ameliorer.csv", mime="text/csv")
    else:
        st.warning("Aucun établissement trouvé avec les critères spécifiés.")
else:
    st.error("Aucune donnée disponible.")

