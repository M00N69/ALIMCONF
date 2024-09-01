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

    # Conversion des coordonnées géographiques en dictionnaires
    df['geores'] = df['geores'].apply(lambda x: {'lat': float(x.split(',')[0]), 'lon': float(x.split(',')[1])} if pd.notnull(x) else None)

    return df

# Charger les données
st.title('Données AlimConfiance')
df = load_data()

if not df.empty:
    # Filtrer pour ne garder que les établissements avec une synthèse "A améliorer"
    df_filtered = df[df['synthese_eval_sanit'] == 'A améliorer']

    if not df_filtered.empty:
        # Afficher la carte interactive
        st.subheader('Carte des établissements "A améliorer"')
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
        st.subheader('Données détaillées des établissements "A améliorer"')
        st.write(df_filtered)

        # Permettre de télécharger les données filtrées
        csv = df_filtered.to_csv(index=False)
        st.download_button("Télécharger les données", csv, file_name="data_a_ameliorer.csv", mime="text/csv")
    else:
        st.warning("Aucun établissement trouvé avec une évaluation 'A améliorer'.")
else:
    st.error("Aucune donnée disponible.")

