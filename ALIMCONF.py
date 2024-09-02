import streamlit as st
import pandas as pd
import folium
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Configurer le mode wide
st.set_page_config(layout="wide")

# Custom CSS for changing sidebar background color and resizing the banner
st.markdown(
    """
    <style>
    /* Sidebar background color */
    [data-testid="stSidebar"] {
        background-color: #2398B2; /* Light blue color */
    }

    /* Sidebar header text color (optional) */
    [data-testid="stSidebar"] .css-1lcbmhc {
        color: black;
    }
    
    /* Sidebar widget text color (optional) */
    [data-testid="stSidebar"] .css-17eq0hr {
        color: black;
    }

    /* Banner styling */
    .banner {
        background-image: url('https://github.com/M00N69/BUSCAR/blob/main/logo%2002%20copie.jpg?raw=true');
        background-size: cover;
        padding: 75px;
        text-align: center;
    }
    .dataframe td {
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    </style>
    <div class="banner"></div>
    """,
    unsafe_allow_html=True
)

# --- Logo and Link in Sidebar ---
st.sidebar.markdown(
        f"""
        <div class="sidebar-logo-container">
            <a href="https://www.visipilot.com" target="_blank">
                <img src="https://raw.githubusercontent.com/M00N69/RAPPELCONSO/main/logo%2004%20copie.jpg" alt="Visipilot Logo" class="sidebar-logo">
            </a>
        </div>
        """, unsafe_allow_html=True
)


# Fonction pour récupérer les données du CSV avec mise en cache
@st.cache_data(ttl=3600)
def get_data():
    url = "https://dgal.opendatasoft.com/api/explore/v2.1/catalog/datasets/export_alimconfiance/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
    df = pd.read_csv(url, sep=";")
    df['Date_inspection'] = pd.to_datetime(df['Date_inspection'], format='%Y-%m-%dT%H:%M:%S%z', errors='coerce')
    return df

# Fonction pour convertir les coordonnées en float de manière sûre
def safe_float(value):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None

def get_icon_color(synthese_eval_sanit):
    if synthese_eval_sanit == 'Très satisfaisant':
        return 'green'
    elif synthese_eval_sanit == 'Satisfaisant':
        return 'orange'
    elif synthese_eval_sanit == 'À améliorer':
        return 'red'
    elif synthese_eval_sanit == 'À corriger de manière urgente':
        return 'black'
    else:
        return 'gray'  # Couleur par défaut si aucune correspondance


# Fonction pour créer la carte interactive
def create_map(df):
    map_center = [46.2276, 2.2137]  # Centre de la France
    map = folium.Map(location=map_center, zoom_start=6)

    for _, row in df.iterrows():
        if pd.notna(row['geores']) and isinstance(row['geores'], str):
            coords = row['geores'].split(',')
            if len(coords) == 2:
                latitude = safe_float(coords[0])
                longitude = safe_float(coords[1])
                if latitude is not None and longitude is not None:
                    site_name = row['APP_Libelle_etablissement']
                    date_inspection = row['Date_inspection'].strftime('%d/%m/%Y') if pd.notna(row['Date_inspection']) else "Date non spécifiée"

                    # Déterminer la couleur de l'icône en fonction de la synthèse
                    icon_color = get_icon_color(row['Synthese_eval_sanit'])

                    # Contenu HTML pour la popup
                    popup_html = f"""
                    <div style="font-family: Arial; color: #333;">
                        <h4 style="margin-bottom: 5px;">{site_name}</h4>
                        <p style="margin: 0;">Date d'inspection: <strong>{date_inspection}</strong></p>
                    </div>
                    """

                    folium.Marker(
                        location=[latitude, longitude],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=site_name,
                        icon=folium.Icon(
                            color=icon_color,  # Utilisation de la couleur déterminée
                            icon_color='white',  # Couleur de l'icône, souvent blanc pour un bon contraste
                            icon='fa-solid fa-circle-exclamation',  # Icône pour meilleure visibilité
                            prefix='fa'
                        )
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
    # Ensure the data is numeric and replace NaN values with 0
    data = data.fillna(0)
    data = data.astype(float)  # Ensure all values are float for the bar chart

    fig, ax = plt.subplots()
    ax.bar(data.index.astype(str), data.values)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    return fig

# Interface utilisateur Streamlit
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

# Add the clickable logo at the bottom of the sidebar
st.sidebar.markdown(
    f"""
    <div class="sidebar-bottom-logo-container">
        <a href="https://dgal.opendatasoft.com/explore/dataset/export_alimconfiance/table/?disjunctive.app_libelle_activite_etablissement&disjunctive.filtre&disjunctive.ods_type_activite&refine.synthese_eval_sanit=A+corriger+de+mani%C3%A8re+urgente&dataChart=eyJxdWVyaWVzIjpbeyJjb25maWciOnsiZGF0YXNldCI6ImV4cG9ydF9hbGltY29uZmlhbmNlIiwib3B0aW9ucyI6eyJkaXNqdW5jdGl2ZS5hcHBfbGliZWxsZV9hY3Rpdml0ZV9ldGFibGlzc2VtZW50Ijp0cnVlLCJkaXNqdW5jdGl2ZS5maWx0cmUiOnRydWUsImRpc2p1bmN0aXZlLm9kc190eXBlX2FjdGl2aXRlIjp0cnVlLCJsb2NhdGlvbiI6IjUsNDEuNjg5MzIsNS45NzY1NiJ9fSwiY2hhcnRzIjpbeyJhbGlnbk1vbnRoIjp0cnVlLCJ0eXBlIjoiYmFyIiwiZnVuYyI6IkNPVU5UIiwieUF4aXMiOiJhcHBfY29kZV9zeW50aGVzZV9ldmFsX3Nhbml0Iiwic2NpZW50aWZpY0Rpc3BsYXkiOnRydWUsImNvbG9yIjoicmFuZ2UtQWNjZW50IiwicG9zaXRpb24iOiJjZW50ZXIifSx7ImFsaWduTW9udGgiOnRydWUsInR5cGUiOiJsaW5lIiwiZnVuYyI6IkFWRyIsInlBeGlzIjoiYXBwX2NvZGVfc3ludGhlc2VfZXZhbF9zYW5pdCIsInNjaWVudGlmaWNEaXNwbGF5Ijp0cnVlLCJjb2xvciI6InJhbmdlLUFjY2VudCJ9XSwieEF4aXMiOiJkYXRlX2luc3BlY3Rpb24iLCJtYXhwb2ludHMiOm51bGwsInRpbWVzY2FsZSI6Im1vbnRoIiwic29ydCI6IiIsInNlcmllc0JyZWFrZG93biI6Im9kc190eXBlX2FjdGl2aXRlIiwic2VyaWVzQnJlYWtkb3duVGltZXNjYWxlIjoiIn1dLCJkaXNwbGF5TGVnZW5kIjp0cnVlLCJhbGlnbk1vbnRoIjp0cnVlfQ%3D%3D&location=5,41.68932,5.97656" target="_blank">
            <img src="https://github.com/M00N69/ALIMCONF/blob/main/logo-alimconfiance.svg?raw=true" alt="Logo Alim Confiance" class="sidebar-bottom-logo">
        </a>
    </div>
    """, unsafe_allow_html=True
)



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

    # Afficher la fiche complète d'un site sélectionné avec un meilleur design
    if not df_filtered.empty:
        selected_site = st.selectbox("Sélectionner un site", df_filtered['APP_Libelle_etablissement'])
        selected_site_data = df_filtered[df_filtered['APP_Libelle_etablissement'] == selected_site].iloc[0]
        st.subheader('Fiche complète du site sélectionné')
        
        # CSS pour un design attrayant et professionnel
        st.markdown("""
        <style>
        .site-info {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .site-info h3 {
            color: #0e1117;
            border-bottom: 2px solid #0e1117;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .site-info p {
            margin-bottom: 10px;
        }
        .site-info strong {
            color: #0e1117;
        }
        </style>
        """, unsafe_allow_html=True)

        # Fonction pour obtenir une valeur sûre
        def safe_get(data, key, default="Non spécifié"):
            return data[key] if key in data and pd.notna(data[key]) else default

        # Affichage des informations du site
        st.markdown(f"""
        <div class="site-info">
            <h3>{safe_get(selected_site_data, 'APP_Libelle_etablissement')}</h3>
            <p><strong>Adresse:</strong> {safe_get(selected_site_data, 'Adresse_2_UA')}</p>
            <p><strong>Code postal:</strong> {safe_get(selected_site_data, 'Code_postal')}</p>
            <p><strong>Commune:</strong> {safe_get(selected_site_data, 'com_name')}</p>
            <p><strong>Activité:</strong> {safe_get(selected_site_data, 'APP_Libelle_activite_etablissement')}</p>
            <p><strong>Date d'inspection:</strong> {selected_site_data['Date_inspection'].strftime('%d/%m/%Y')}</p>
            <p><strong>Synthèse de l'évaluation sanitaire:</strong> {safe_get(selected_site_data, 'Synthese_eval_sanit')}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.write("Aucun établissement trouvé dans la période sélectionnée.")

elif page == "Statistiques":
    # Assurez-vous que la colonne Date_inspection est correctement convertie en datetime
    df_filtered = df_filtered.dropna(subset=['Date_inspection'])
    df_filtered['Date_inspection'] = pd.to_datetime(df_filtered['Date_inspection'], errors='coerce')
    df_filtered['month'] = df_filtered['Date_inspection'].dt.to_period('M')

    # Graphique en camembert pour la Synthèse d'évaluation sanitaire
    synthese_counts = df_filtered['Synthese_eval_sanit'].value_counts()
    fig1 = create_pie_chart(synthese_counts.values, synthese_counts.index, "Répartition des Synthèses d'évaluation sanitaire")

    # Graphique en camembert pour les types d'activité
    activite_counts = df_filtered['ods_type_activite'].value_counts()
    fig2 = create_pie_chart(activite_counts.values, activite_counts.index, "Répartition des Types d'activité")

    # Graphique en barres pour "A corriger immédiatement" et "A améliorer"
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

    

