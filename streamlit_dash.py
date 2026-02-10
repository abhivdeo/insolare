import streamlit as st
import pandas as pd
import plotly.express as px
import io

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
        
        # Pull metadata
        df['Setup_ID'] = metadata.get('Experiment_ID', 'Unknown')
        df['Active_Area_cm2'] = float(metadata.get('Active_Area_cm2', 0))
        
        # Calculations
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']) * 100
        F = 96485
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']) * 100
        
        return df, metadata
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None, None

df_raw, meta = load_data('electrolysis_test.csv')

if df_raw is not None:
    # Sidebar Filter
    unique_setups = df_raw['Setup_ID'].unique()
    selected_setup = st.sidebar.selectbox("Select Setup_ID", options=unique_setups)
    df = df_raw[df_raw['Setup_ID'] == selected_setup].copy()

    # 1. DATA TABLE (Safe column selection)
    st.subheader(f"Dataset Preview - {selected_setup}")
    cols_to_show = ['Setup_ID', 'Active_Area_cm2', 'Timestamp', 'Voltage_V', 'Current_A', 
                    'Temp_C', 'pH', 'Pressure_bar', 'H2_Flow_mLmin', 'O2_Flow_mLmin', 
                    'Voltage_Efficiency_%', 'Faradaic_Efficiency_%']
    # Filter only columns that actually exist
    final_cols = [c for c in cols_to_show if c in df.columns]
    st.dataframe(df[final_cols], use_container_width=True)

    # 2. PLOTS
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        # We check if required columns for the plot exist
        if 'Current_Density_Acm2' in df.columns and 'Voltage_V' in df.columns:
            # Safely build hover data
            h_data = [c for c in ['Temp_C', 'pH', 'Pressure_bar'] if c in df.columns]
            fig1 = px.line(df, x='Current_Density_Acm2', y='Voltage_V', 
                           hover_data=h_data, markers=True, title="Polarization Curve", template="plotly_white")
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.line(df, x='Time_Elapsed_s', y=['H2_Flow_mLmin', 'O2_Flow_mLmin'], 
                       title="Gas Production Rates", template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    # 3. LOGIC BOX
    st.divider()
    st.subheader("Calculation Methodology")
    st.info("""
    * **Voltage Efficiency**: $\eta_v = (1.48V / V_{measured}) \\times 100$
    * **Faradaic Efficiency**: Compares measured $H_2$ vs theoretical gas produced per Ampere-second.
    """)

    # 4. EXPORT
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.sidebar.download_button("📥 Download Excel Report", data=buffer.getvalue(), file_name="Report.xlsx")
    except ImportError:
        st.sidebar.warning("Add 'xlsxwriter' to requirements.txt for Excel downloads.")
else:
    st.warning("Ensure 'electrolysis_test.csv' is uploaded and formatted correctly.")
