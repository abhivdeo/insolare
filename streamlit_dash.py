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
        
        # Pull constants from metadata
        setup_id = metadata.get('Experiment_ID', 'Unknown_Setup')
        active_area = float(metadata.get('Active_Area_cm2', 0))
        
        # Add Setup_ID and Area Columns
        df['Setup_ID'] = setup_id
        df['Active_Area_cm2'] = active_area
        
        # Numeric conversion
        for col in df.columns:
            if col not in ['Timestamp', 'Notes', 'Setup_ID']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # --- Calculations ---
        # 1. Voltage Efficiency
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']) * 100
        
        # 2. Faradaic Efficiency
        # Constant: 22414 mL is the molar volume of ideal gas at STP
        # Faraday constant F = 96485 C/mol
        F = 96485
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']) * 100
        
        return df, metadata
    except FileNotFoundError:
        return None, None

df_raw, meta = load_data('electrolysis_test.csv')

if df_raw is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Data Filters")
    unique_setups = df_raw['Setup_ID'].unique()
    selected_setup = st.sidebar.selectbox("Select Setup_ID", options=unique_setups)
    
    df = df_raw[df_raw['Setup_ID'] == selected_setup].copy()

    # --- 1. DATA TABLE (Top) ---
    st.subheader(f"Dataset Preview - Setup: {selected_setup}")
    # Organizing columns to show Setup and Area prominently
    display_cols = ['Setup_ID', 'Active_Area_cm2', 'Timestamp', 'Voltage_V', 'Current_A', 
                    'Current_Density_Acm2', 'H2_Flow_mLmin', 'Voltage_Efficiency_%', 'Faradaic_Efficiency_%']
    st.dataframe(df[display_cols], use_container_width=True)

    # --- 2. METRICS ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Faradaic Efficiency", f"{df['Faradaic_Efficiency_%'].mean():.2f}%")
    m2.metric("Avg Voltage Efficiency", f"{df['Voltage_Efficiency_%'].mean():.2f}%")
    m3.metric("Current Density", f"{df['Current_Density_Acm2'].max()} A/cm²")
    m4.metric("Active Area", f"{df['Active_Area_cm2'].iloc[0]} cm²")

    # --- 3. PLOTS ---
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.line(df, x='Current_Density_Acm2', y='Voltage_V',
                       hover_data=['Voltage_Efficiency_%', 'Faradaic_Efficiency_%'],
                       markers=True, template="plotly_white", title="Polarization Curve")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.line(df, x='Time_Elapsed_s', y=['Faradaic_Efficiency_%', 'Voltage_Efficiency_%'],
                       template="plotly_white", title="Efficiency Trends Over Time")
        st.plotly_chart(fig2, use_container_width=True)

    # --- 4. CALCULATION LOGIC BOX ---
    st.divider()
    st.subheader("Calculation Methodology")
    st.info(f"""
    **1. Voltage Efficiency ($\eta_v$):**
    This measures how much of the electrical energy is used for the reaction versus lost as heat.
    * **Formula:** $\eta_v = (V_{{thermoneutral}} / V_{{cell}}) \\times 100$
    * **Logic:** We use **1.48V** as the thermoneutral voltage (standard for water electrolysis). Values above 100% are physically impossible for long durations as they would require absorbing heat from the environment.

    **2. Faradaic Efficiency ($\eta_f$):**
    This measures the "selectivity" of the reaction—how much of the electrons (current) actually produced Hydrogen gas.
    * **Theoretical H₂ Flow Rate:** $Q_{{th}} = (I \\times 60 \\times 22414) / (z \\times F)$
        * $I$: Current (Amps)
        * $z$: Number of electrons for $H_2$ ($z=2$)
        * $F$: Faraday Constant ($96485 \, C/mol$)
        * $22414$: Molar volume of gas at STP (mL/mol)
    * **Formula:** $\eta_f = (Q_{{actual}} / Q_{{theoretical}}) \\times 100$
    """)

    # --- EXPORT ---
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')
        st.sidebar.download_button(label="📥 Download Excel", data=buffer.getvalue(), 
                                   file_name=f"Report_{selected_setup}.xlsx")
    except:
        st.sidebar.warning("Install 'xlsxwriter' to enable export.")

else:
    st.error("CSV File not found.")
