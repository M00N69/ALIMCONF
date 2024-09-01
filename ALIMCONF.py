import streamlit as st
import pandas as pd
import folium
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Fonction pour récupérer les données du CSV avec mise en cache
@st.cache_data(ttl=3600)
def get_data():
    url = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
    df = pd.read_csv(url, sep=";")
    df['Date_inspection'] = pd.to_datetime(df['Date_inspection'], format='%Y-%m-%dT%H:%M:%S%z')
    return df

# Fonction pour convertir les coordonnées en float de manière sûre
def safe_float(value):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None

# Fonction pour créer la carte interactive
def create_map(df):
    map_center = [46.2276, 2.2137]
    map = folium.Map(location=map_center, zoom_start=6)

    for _, row in df.iterrows():
        if pd.notna(row['geores']) and isinstance(row['geores'], str):
            coords = row['geores'].split(',')
            if len(coords) == 2:
                latitude = safe_float(coords[0])
                longitude = safe_float(coords[1])
                if latitude is not None and longitude is not None:
                    tooltip = row['APP_Libelle_etablissement']
                    folium.Marker(
                        location=[latitude, longitude],
                        popup=row['APP_Libelle_etablissement'],
                        tooltip=tooltip,
                        icon=folium.Icon(color='red', icon='exclamation-sign', prefix='fa')
                    ).add_to(map)

    return map

# Fonction pour créer des graphiques en camembert et en barres
def create_pie_chart(data, labels, title):
    fig, ax = plt.subplots()
    ax.pie(data, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    plt.title(title)
    return fig

def create_bar_chart(data, title, x_label, y_label):
    fig, ax = plt.subplots()
    ax.bar(data.index, data.values)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    return fig

# Interface utilisateur Streamlit
st.set_page_config(layout="wide")
st.title('Données AlimConfiance')

# Navigation avec la sidebar
page = st.sidebar.selectbox("Choisissez une page", ["Carte des établissements", "Statistiques"])

# Récupérer les données du CSV
df = get_data()

# Créer un slider pour sélectionner la plage de dates
start_date = datetime(2023, 9, 1)
end_date = datetime.now()

months = pd.date_range(start=start_date, end=end_date, freq='MS')
selected_start, selected_end = st.sidebar.select_slider(
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

# Filtres dans la sidebar
synthese_options = ['A corriger de manière urgente', 'Tous'] + list(df_filtered['Synthese_eval_sanit'].unique())
selected_synthese = st.sidebar.selectbox("Filtrer par Synthèse d'évaluation sanitaire", synthese_options, index=0)

filtre_options = ['Tous'] + sorted(df_filtered['filtre'].dropna().unique().tolist())
selected_filtre = st.sidebar.selectbox("Filtrer par type de contrôle", filtre_options)

ods_type_options = ['Tous'] + sorted(df_filtered['ods_type_activite'].dropna().unique().tolist())
selected_ods_type = st.sidebar.selectbox("Filtrer par type d'activité", ods_type_options)

activite_options = ['Tous'] + list(df_filtered['APP_Libelle_activite_etablissement'].dropna().unique())
selected_activite = st.sidebar.selectbox("Filtrer par Activité de l'établissement", activite_options)

# Appliquer les filtres
if selected_synthese != 'Tous':
    df_filtered = df_filtered[df_filtered['Synthese_eval_sanit'] == selected_synthese]

if selected_filtre != 'Tous':
    df_filtered = df_filtered[df_filtered['filtre'] == selected_filtre]

if selected_ods_type != 'Tous':
    df_filtered = df_filtered[df_filtered['ods_type_activite'] == selected_ods_type]

if selected_activite != 'Tous':
    df_filtered = df_filtered[df_filtered['APP_Libelle_activite_etablissement'] == selected_activite]

# Logique pour afficher la page sélectionnée
if page == "Carte des établissements":
    # Afficher la carte interactive
    st.subheader('Carte des établissements')
    map = create_map(df_filtered)
    st.components.v1.html(map._repr_html_(), width=1200, height=600)

    # Afficher les informations détaillées
    st.subheader('Données détaillées des établissements')
    st.dataframe(df_filtered)

    # Permettre de télécharger les données filtrées
    csv = df_filtered.to_csv(index=False)
    st.download_button("Télécharger les données", csv, file_name="data_filtered.csv", mime="text/csv")

elif page == "Statistiques":
    # Graphique en camembert pour la Synthèse d'évaluation sanitaire
    synthese_counts = df_filtered['Synthese_eval_sanit'].value_counts()
    fig1 = create_pie_chart(synthese_counts.values, synthese_counts.index, "Répartition des Synthèses d'évaluation sanitaire")

    # Graphique en camembert pour les types d'activité
    activite_counts = df_filtered['ods_type_activite'].value_counts()
    fig2 = create_pie_chart(activite_counts.values, activite_counts.index, "Répartition des Types d'activité")

    # Graphique en barres pour "A corriger immédiatement" et "A améliorer"
    df_filtered['month'] = df_filtered['Date_inspection'].dt.to_period('M')
    correction_counts = df_filtered[df_filtered['Synthese_eval_sanit'].isin(['A corriger immédiatement', 'A améliorer'])].groupby(['month', 'Synthese_eval_sanit']).size().unstack().fillna(0)
    fig3 = create_bar_chart(correction_counts, "Évaluations par mois", "Mois", "Nombre d'évaluations")

    # Afficher les graphiques
    st.subheader('Statistiques')
    col1, col2 = st.columns(2)
    with col1:
        st.pyplot(fig1)
    with col2:
        st.pyplot(fig2)

    st.subheader('Évaluations mensuelles')
    st.pyplot(fig3)

