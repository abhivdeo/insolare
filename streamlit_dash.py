#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  7 13:51:05 2026

@author: abhishekdeodhar
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set page configuration
st.set_page_config(page_title="Electrochemical Data Dashboard", layout="wide")

st.title("Electrochemical Data Visualization Dashboard")
st.markdown("This dashboard provides visualizations and analysis for the provided electrochemical dataset.")

# Load and clean data
@st.cache_data
def load_data():
    # skip row 1 which contains unit labels (A, V, I, A/cm2)
    df = pd.read_csv('sample_data1.csv', skiprows=[1]) 
    
    # Clean column names by stripping whitespace
    df.columns = [col.strip() for col in df.columns]
    
    # Convert all columns to numeric, handling potential errors
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

try:
    df = load_data()

    # Sidebar Settings
    st.sidebar.header("Display Settings")
    show_table = st.sidebar.checkbox("Show Data Table", value=True)
    show_stats = st.sidebar.checkbox("Show Summary Statistics", value=True)

    # Visualization Section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Polarization Curve")
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        sns.lineplot(data=df, x='Current Density', y='Volatge (02/12/25)', marker='o', color='royalblue', ax=ax1)
        ax1.set_title("Voltage vs. Current Density")
        ax1.set_xlabel("Current Density ($A/cm^2$)")
        ax1.set_ylabel("Voltage ($V$)")
        ax1.grid(True, linestyle='--', alpha=0.6)
        st.pyplot(fig1)

    with col2:
        st.subheader("Voltage vs. Current")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        sns.scatterplot(data=df, x='Current', y='Volatge (02/12/25)', color='crimson', s=100, ax=ax2)
        ax2.set_title("Voltage vs. Current")
        ax2.set_xlabel("Current ($I$)")
        ax2.set_ylabel("Voltage ($V$)")
        ax2.grid(True, linestyle='--', alpha=0.6)
        st.pyplot(fig2)

    # Data Display Section
    if show_table:
        st.divider()
        st.subheader("Dataset Preview")
        st.dataframe(df, use_container_width=True)

    if show_stats:
        st.subheader("Statistical Summary")
        st.write(df.describe())

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Please ensure 'sample_data1.csv' is present in the same directory as this script.")