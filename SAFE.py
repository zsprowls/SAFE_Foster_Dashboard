# app.py

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SAFE Foster Program Dashboard",
    page_icon="🐾",
    layout="wide"
)

# Title
st.title("SAFE Foster Program Dashboard")

# Load Data
@st.cache_data
def load_data():
    try:
        # Load Excel data
        df = pd.read_excel("SAFE FOSTER DATASET.xlsx")
        # Load GeoJSON data
        geo_df = gpd.read_file("erie_survey_zips.geojson")
        return df, geo_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

# Load the data
df, geo_df = load_data()

if df is not None and geo_df is not None:
    # Data preprocessing
    df['Intake Date'] = pd.to_datetime(df['Intake Date'])
    df['Foster Start Date'] = pd.to_datetime(df['Foster Start Date'])
    df['Foster End Date'] = pd.to_datetime(df['Foster End Date'])
    df['Intake Year'] = df['Intake Date'].dt.year
    
    # Convert ZIP codes to string for matching
    df['Zipcode'] = df['Zipcode'].astype(str)
    geo_df['ZCTA5CE10'] = geo_df['ZCTA5CE10'].astype(str)
    
    # Key Metrics
    total_people = df['PID'].nunique()
    total_animals = df['Animal #'].nunique()
    
    # Animal breakdown by type
    animal_breakdown = df.drop_duplicates('Animal #')['Animal Type'].value_counts()
    
    # Calculate average days in care
    care_duration = df.groupby('Animal #').agg({
        'Intake Date': 'min',
        'Foster End Date': 'max'
    }).reset_index()
    care_duration['Days in Our Care'] = (care_duration['Foster End Date'] - care_duration['Intake Date']).dt.days
    avg_days_our_care = care_duration['Days in Our Care'].mean()
    min_days_our_care = care_duration['Days in Our Care'].min()
    max_days_our_care = care_duration['Days in Our Care'].max()
    
    # Calculate average days in foster
    df['Foster Duration'] = (df['Foster End Date'] - df['Foster Start Date']).dt.days
    foster_duration = df.groupby('Animal #')['Foster Duration'].sum().reset_index()
    avg_days_foster = foster_duration['Foster Duration'].mean()
    min_days_foster = foster_duration['Foster Duration'].min()
    max_days_foster = foster_duration['Foster Duration'].max()
    
    # Spay/Neuter breakdown
    altered_animals = df[(df['Pre-Altered'] == 'No') & (df['Current Altered'] == 'Yes')]
    altered_unique = altered_animals.drop_duplicates('Animal #')
    spay_neuter = altered_unique.groupby(['Animal Type', 'Gender']).size().reset_index(name='Count')
    spay_neuter['Procedure'] = spay_neuter['Gender'].map({'F': 'Spay', 'M': 'Neuter'})
    
    # Yearly intake data (force only 2022-2025, no .5 years)
    animal_yearly = df.drop_duplicates('Animal #').groupby('Intake Year').size().reset_index(name='New Animals')
    # Ensure all years 2022-2025 are present
    all_years = pd.DataFrame({'Intake Year': [2022, 2023, 2024, 2025]})
    animal_yearly = all_years.merge(animal_yearly, on='Intake Year', how='left').fillna(0)
    animal_yearly['New Animals'] = animal_yearly['New Animals'].astype(int)
    # Custom labels for partial years
    animal_yearly['Label'] = animal_yearly['Intake Year'].astype(str)
    animal_yearly.loc[animal_yearly['Intake Year'] == 2022, 'Label'] += '\n(Data starts July)'
    animal_yearly.loc[animal_yearly['Intake Year'] == 2025, 'Label'] += '\n(Data ends today)'
    
    # Choropleth map data
    zip_counts = df.drop_duplicates('Animal #').groupby('Zipcode').size().reset_index(name='Animal Count')
    map_df = geo_df.merge(zip_counts, left_on='ZCTA5CE10', right_on='Zipcode', how='left').fillna(0)
    
    # --- Key Metrics and Animal Type Breakdown ---
    col1, col2 = st.columns([1, 1])
    with col1:
        # Add vertical space to center metrics with pie chart
        st.markdown("<div style='height: 80px'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='margin-bottom: 0.5em;'>Key Metrics</h2>", unsafe_allow_html=True)
        # Top row: Total People and Animals
        col1a, col1b = st.columns(2)
        with col1a:
            st.metric("Total People", f"{total_people}")
        with col1b:
            st.metric("Total Animals", f"{total_animals}")
        # Second row: Care duration metrics
        col1c, col1d = st.columns(2)
        with col1c:
            st.metric("Avg Days in Care", f"{avg_days_our_care:.1f}")
            st.caption(f"Min: {min_days_our_care} | Max: {max_days_our_care}")
        with col1d:
            st.metric("Avg Days in Foster", f"{avg_days_foster:.1f}")
            st.caption(f"Min: {min_days_foster} | Max: {max_days_foster}")
    with col2:
        st.markdown("<h2 style='margin-bottom: 0.5em;'>Animal Type Breakdown</h2>", unsafe_allow_html=True)
        fig_pie = px.pie(
            values=animal_breakdown.values,
            names=animal_breakdown.index
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        animal_table = animal_breakdown.reset_index()
        animal_table.columns = ['Species', 'Count']
        st.dataframe(animal_table, hide_index=True)
    
    # --- Spay/Neuter Breakdown ---
    st.markdown("<h2 style='margin-bottom: 0.5em;'>Spay/Neuter Breakdown by Species</h2>", unsafe_allow_html=True)
    if not spay_neuter.empty:
        fig_spay = px.bar(
            spay_neuter,
            x="Animal Type",
            y="Count",
            color="Procedure",
            title="Spay/Neuter Procedures by Animal Type",
            barmode="group",
            text="Count"
        )
        fig_spay.update_traces(textposition='outside')
        st.plotly_chart(fig_spay, use_container_width=True)
    else:
        st.info("No spay/neuter data available for animals that were not pre-altered.")
    
    # --- Yearly Intake Trends ---
    st.markdown("<h2 style='margin-bottom: 0.5em;'>Yearly Intake Trends</h2>", unsafe_allow_html=True)
    fig_bar = px.bar(
        animal_yearly,
        x='Label',
        y='New Animals',
        title="New Animals by Year",
        text='New Animals'
    )
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(
        xaxis_title="Year",
        yaxis_title="Number of Animals",
        xaxis = dict(type='category', tickmode='array', tickvals=animal_yearly['Label'], ticktext=animal_yearly['Label'])
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # --- Geographic Distribution ---
    st.markdown("<h2 style='margin-bottom: 0.5em;'>Geographic Distribution of Animals</h2>", unsafe_allow_html=True)
    fig_map = px.choropleth_mapbox(
        map_df,
        geojson=map_df.geometry,
        locations=map_df.index,
        color="Animal Count",
        mapbox_style="carto-positron",
        zoom=8,
        center={"lat": 42.9, "lon": -78.8},
        opacity=0.6,
        labels={"Animal Count": "Animals"},
        color_continuous_scale=["white", "red"]
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("*Dashboard created for SAFE Foster Program*")
else:
    st.error("Unable to load data. Please check that both 'SAFE FOSTER DATASET.xlsx' and 'erie_survey_zips.geojson' are in the current directory.")
