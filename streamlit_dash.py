import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Set page configuration
st.set_page_config(page_title="H2 Electrolyser Dashboard", layout="wide")

st.title("⚡ Electrolyser Performance Dashboard")

@st.cache_data
def load_data(file_path):
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
        
        # Add Setup_ID Column from metadata or default
        df['Setup_ID'] = metadata.get('Experiment_ID', 'Unknown_Setup')
        
        # Numeric conversion
        for col in df.columns:
            if col not in ['Timestamp', 'Notes', 'Setup_ID']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # --- Calculations ---
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']) * 100
        F = 96485
        # Theoretical H2 flow (mL/min)
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']) * 100
        
        return df, metadata
    except FileNotFoundError:
        return None, None

df_raw, meta = load_data('electrolysis_test.csv')

if df_raw is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Data Filters")
    # Dropdown for Setup_ID (handles future cases with multiple IDs)
    unique_setups = df_raw['Setup_ID'].unique()
    selected_setup = st.sidebar.selectbox("Select Setup_ID", options=unique_setups)
    
    # Filter dataframe based on selection
    df = df_raw[df_raw['Setup_ID'] == selected_setup].copy()

    st.sidebar.divider()
    st.sidebar.header("Experiment Metadata")
    for key, value in meta.items():
        st.sidebar.write(f"**{key}:** {value}")

    # --- 1. DATA TABLE (First) ---
    st.subheader(f"Dataset Preview - Setup: {selected_setup}")
    # Reordering to show Setup_ID first
    cols = ['Setup_ID'] + [c for c in df.columns if c != 'Setup_ID']
    st.dataframe(df[cols], use_container_width=True)

    # --- 2. METRICS ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Faradaic Efficiency", f"{df['Faradaic_Efficiency_%'].mean():.2f}%")
    m2.metric("Avg Voltage Efficiency", f"{df['Voltage_Efficiency_%'].mean():.2f}%")
    m3.metric("Peak Current Density", f"{df['Current_Density_Acm2'].max()} A/cm²")
    m4.metric("Total Energy", f"{df['Energy_kWh'].max()} kWh")

    # --- 3. PLOTS WITH HOVER INFO ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Polarization & Efficiency")
        # Added hover_data for calculated columns
        fig1 = px.line(df, x='Current_Density_Acm2', y='Voltage_V',
                       hover_data=['Voltage_Efficiency_%', 'Faradaic_Efficiency_%', 'Temp_C'],
                       markers=True, template="plotly_white", title="V vs J (with Efficiency Hover)")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Gas Production Stability")
        fig2 = px.line(df, x='Time_Elapsed_s', y=['H2_Flow_mLmin', 'Theoretical_H2_mLmin'],
                       hover_data=['Faradaic_Efficiency_%', 'Current_A'],
                       template="plotly_white", title="H2 Flow (Actual vs Theoretical)")
        st.plotly_chart(fig2, use_container_width=True)

    # --- 4. EXPORT ---
    buffer = io.BytesIO()
    # Note: Ensure xlsxwriter is in your requirements.txt
    try:
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')
        
        st.sidebar.download_button(
            label="📥 Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"Report_{selected_setup}.xlsx",
            mime="application/vnd.ms-excel"
        )
    except:
        st.sidebar.warning("Install 'xlsxwriter' to enable Excel export.")

else:
    st.error("Please ensure 'electrolysis_test.csv' is in the directory.")
