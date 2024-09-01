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

    # Renommer les colonnes pour correspondre à ce qui est attendu dans le code
    df.rename(columns={
        'APP_Libelle_etablissement': 'app_libelle_etablissement',
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

    # Convertir la colonne 'date_inspection' en datetime
    df['date_inspection'] = pd.to_datetime(df['date_inspection'], errors='coerce')

    # Supprimer les lignes où la conversion en datetime a échoué
    df = df.dropna(subset=['date_inspection'])

    # Extraire la date uniquement (sans heure)
    df['date_inspection'] = df['date_inspection'].dt.date

    return df

# Charger les données
st.title('Données AlimConfiance')
df = load_data()

if not df.empty:
    # Filtrer sur le dernier mois et "A améliorer"
    last_month = pd.to_datetime(df['date_inspection'].max()).to_period('M').to_timestamp()
    df_filtered = df[(pd.to_datetime(df['date_inspection']) >= last_month) & (df['synthese_eval_sanit'] == 'A améliorer')]

    # Ajout des filtres dans la barre latérale
    st.sidebar.title('Filtres supplémentaires')

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

    # Appliquer les filtres supplémentaires
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

    if not df_filtered.empty:
        # Afficher la carte interactive
        st.subheader('Carte des établissements "A améliorer" (Dernier Mois)')
        map = folium.Map(location=[46.2276, 2.2137], zoom_start=6)
        for _, row in df_filtered.iterrows():
            if row['geores'] is not None:
                folium.Marker(
                    location=[row['geores']['lat'], row['geores']['lon']],
                    popup=row['app_libelle_etablissement'],
                    tooltip=row['app_libelle_etablissement'],
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

