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
        # Clean column names
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
        # 1. Voltage Efficiency (Thermoneutral 1.48V)
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']) * 100
        
        # 2. Faradaic Efficiency
        # F = 96485 C/mol, Molar Vol = 22414 mL/mol
        F = 96485
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']) * 100
        
        return df, metadata
    except Exception as e:
        st.error(f"Error loading data: {e}")
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
    
    # Dynamically select columns that exist to avoid KeyError
    preferred_order = ['Setup_ID', 'Active_Area_cm2', 'Timestamp', 'Voltage_V', 'Current_A', 
                       'Current_Density_Acm2', 'H2_Flow_mLmin', 'Voltage_Efficiency_%', 'Faradaic_Efficiency_%']
    display_cols = [c for c in preferred_order if c in df.columns]
    
    st.dataframe(df[display_cols], use_container_width=True)

    # --- 2. METRICS & PLOTS ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Faradaic Efficiency", f"{df['Faradaic_Efficiency_%'].mean():.2f}%")
    m2.metric("Avg Voltage Efficiency", f"{df['Voltage_Efficiency_%'].mean():.2f}%")
    m3.metric("Peak Current Density", f"{df['Current_Density_Acm2'].max()} A/cm²")
    m4.metric("Active Area", f"{df['Active_Area_cm2'].iloc[0]} cm²")

    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.line(df, x='Current_Density_Acm2', y='Voltage_V',
                       hover_data=['Voltage_Efficiency_%', 'Faradaic_Efficiency_%'],
                       markers=True, template="plotly_white", title="Polarization Curve")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.line(df, x='Time_Elapsed_s', y=['Faradaic_Efficiency_%', 'Voltage_Efficiency_%'],
                       template="plotly_white", title="Efficiency Trends")
        st.plotly_chart(fig2, use_container_width=True)

    # --- 3. CALCULATION LOGIC ---
    st.divider()
    st.subheader("Calculation Methodology")
    st.info(f"""
    **Voltage Efficiency ($\eta_v$):**
    Measures energy converted to chemical bonds vs. heat.
    $$ \eta_v = \\frac{1.48V}{V_{{measured}}} \\times 100 $$
    *Uses 1.48V as the thermoneutral limit where the reaction is 100% thermally efficient.*

    **Faradaic Efficiency ($\eta_f$):**
    Measures the ratio of actual gas produced to the theoretical amount predicted by current.
    $$ Theoretical \, H_2 \, (mL/min) = \\frac{I \cdot 60 \cdot 22414}{2 \cdot 96485} $$
    $$ \eta_f = \\frac{Actual \, Flow}{Theoretical \, Flow} \\times 100 $$
    """)

    # --- EXPORT (Sidebar) ---
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.sidebar.download_button("📥 Download Excel Report", data=buffer.getvalue(), file_name="Electrolysis_Report.xlsx")
    except ImportError:
        st.sidebar.warning("Add 'xlsxwriter' to requirements.txt to enable Excel export.")
