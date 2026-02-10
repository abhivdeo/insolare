import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io  # New import for file handling

# Set page configuration
st.set_page_config(page_title="H2 Electrolyser Dashboard", layout="wide")

st.title("⚡ Electrolyser Performance Dashboard")

@st.cache_data
def load_data(file_path):
    # Read metadata (lines starting with #)
    metadata = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    parts = line.replace('#', '').strip().split(': ')
                    if len(parts) == 2:
                        metadata[parts[0]] = parts[1]
                else:
                    break
        
        df = pd.read_csv(file_path, comment='#')
        df.columns = [col.strip() for col in df.columns]
        for col in df.columns:
            if col not in ['Timestamp', 'Notes']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # --- Efficiency Calculations ---
        # Voltage Efficiency (compared to thermoneutral 1.48V)
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']) * 100

        # Faradaic Efficiency (H2)
        # Theoretical H2 (mL/min) = (I * 60 * 22414) / (2 * 96485)
        F = 96485
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']) * 100
        
        return df, metadata
    except FileNotFoundError:
        return None, None

df, meta = load_data('electrolysis_test.csv')

if df is not None:
    # Sidebar: Display Metadata
    st.sidebar.header("Experiment Metadata")
    for key, value in meta.items():
        st.sidebar.write(f"**{key}:** {value}")
    
    # --- NEW: Export Section ---
    st.sidebar.divider()
    st.sidebar.header("Export Data")
    
    # Create Excel buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Calculated_Results')
        # Also save metadata to a second sheet
        meta_df = pd.DataFrame(list(meta.items()), columns=['Parameter', 'Value'])
        meta_df.to_excel(writer, index=False, sheet_name='Experiment_Metadata')
        writer.close()

    st.sidebar.download_button(
        label="📥 Download Results as Excel",
        data=buffer.getvalue(),
        file_name=f"Electrolysis_Results_{meta.get('Experiment_ID', 'Test')}.xlsx",
        mime="application/vnd.ms-excel"
    )

    show_table = st.sidebar.checkbox("Show Data Table", value=True)

    # --- Metrics Row ---
    m1, m2, m3, m4 = st.columns(4)
    avg_faraday = df['Faradaic_Efficiency_%'].mean()
    m1.metric("Avg Faradaic Efficiency", f"{avg_faraday:.2f}%")
    m2.metric("Avg Voltage Efficiency", f"{df['Voltage_Efficiency_%'].mean():.2f}%")
    m3.metric("Peak Current Density", f"{df['Current_Density_Acm2'].max()} A/cm²")
    m4.metric("Total Energy", f"{df['Energy_kWh'].max()} kWh")

    st.divider()

    # --- Charts Section ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Polarization & Efficiency")
        fig1 = px.line(df, x='Current_Density_Acm2', y=['Voltage_V', 'Voltage_Efficiency_%'],
                       markers=True, template="plotly_white")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Gas Production Stability")
        fig2 = px.line(df, x='Time_Elapsed_s', y=['H2_Flow_mLmin', 'Theoretical_H2_mLmin'],
                          template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    # --- Data Display ---
    if show_table:
        st.divider()
        st.subheader("Calculated Dataset")
        st.dataframe(df, use_container_width=True)
else:
    st.error("File 'electrolysis_test.csv' not found.")
