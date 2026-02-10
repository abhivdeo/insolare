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
        
        # Add Setup and Area from metadata
        df['Setup_ID'] = metadata.get('Experiment_ID', 'Unknown')
        df['Active_Area_cm2'] = float(metadata.get('Active_Area_cm2', 0))
        
        # Numeric conversion
        for col in df.columns:
            if col not in ['Timestamp', 'Notes', 'Setup_ID']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculations
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']) * 100
        F = 96485
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']) * 100
        
        return df, metadata
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None

df_raw, meta = load_data('electrolysis_test.csv')

if df_raw is not None:
    # Sidebar Filters
    st.sidebar.header("Data Filters")
    selected_setup = st.sidebar.selectbox("Select Setup_ID", options=df_raw['Setup_ID'].unique())
    df = df_raw[df_raw['Setup_ID'] == selected_setup].copy()

    # --- 1. DATA TABLE (With requested columns) ---
    st.subheader(f"Dataset Preview - {selected_setup}")
    
    # Define exact order including new columns
    display_cols = [
        'Setup_ID', 'Active_Area_cm2', 'Timestamp', 'Voltage_V', 'Current_A', 
        'Temp_C', 'pH', 'Pressure_bar', 'H2_Flow_mLmin', 'O2_Flow_mLmin', 
        'Voltage_Efficiency_%', 'Faradaic_Efficiency_%'
    ]
    # Filter only columns that actually exist in the CSV to prevent KeyErrors
    final_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[final_cols], use_container_width=True)

    # --- 2. SUMMARY METRICS ---
    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Avg Faradaic Eff.", f"{df['Faradaic_Efficiency_%'].mean():.1f}%")
    m2.metric("Avg Voltage Eff.", f"{df['Voltage_Efficiency_%'].mean():.1f}%")
    m3.metric("Avg Temp", f"{df['Temp_C'].mean():.1f} °C")
    m4.metric("Avg pH", f"{df['pH'].mean():.2f}")
    # Display pressure if it exists
    if 'Pressure_bar' in df.columns:
        m5.metric("Avg Pressure", f"{df['Pressure_bar'].mean():.1f} bar")

    # --- 3. PLOTS ---
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.line(df, x='Current_Density_Acm2', y='Voltage_V', 
                       hover_data=['Temp_C', 'pH', 'Pressure_bar'],
                       markers=True, title="Polarization Curve", template="plotly_white")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.line(df, x='Time_Elapsed_s', y=['H2_Flow_mLmin', 'O2_Flow_mLmin'], 
                       title="Gas Production Rates", template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    # --- 4. LOGIC EXPLANATION ---
    st.divider()
    st.subheader("Calculation Methodology")
    st.info("""
    * **Voltage Efficiency**: Calculated using the thermoneutral voltage ($1.48V$). It represents the ratio of energy stored in hydrogen to the total electrical energy input.
    * **Faradaic Efficiency**: Compares the actual $H_2$ flow rate measured against the theoretical rate predicted by Faraday's Law ($2$ electrons per molecule of $H_2$).
    * **Pressure & Temperature**: These are critical environmental factors; higher pressures usually require specialized cell designs, and temperature impacts the ionic conductivity of the electrolyte.
    """)

    # --- EXPORT ---
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.sidebar.download_button("📥 Download Excel Report", data=buffer.getvalue(), file_name=f"{selected_setup}_Report.xlsx")
    except:
        st.sidebar.warning("Export disabled. Add 'xlsxwriter' to requirements.txt.")
