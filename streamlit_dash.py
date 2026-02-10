import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="H2 Electrolyser Dashboard", layout="wide")
st.title("⚡ Electrolyser Performance Dashboard")

@st.cache_data
def load_data(file_path):
    try:
        # Load the raw CSV
        df = pd.read_csv(file_path, comment='#')
        df.columns = [col.strip() for col in df.columns]
        
        # Load metadata separately for Area (using first experiment as reference)
        with open(file_path, 'r') as f:
            for line in f:
                if "Active_Area_cm2" in line:
                    area = float(line.split(': ')[1])
                    break
        df['Active_Area_cm2'] = area
        
        # Calculations
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']).replace([float('inf'), -float('inf')], 0) * 100
        F = 96485
        # Theoretical Flow in mL/min
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']).fillna(0) * 100
        
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

df_all = load_data('electrolysis_test.csv')

if df_all is not None:
    # Sidebar Setup Selection
    st.sidebar.header("Navigation")
    setup_list = df_all['Setup_ID'].unique()
    selected_setup = st.sidebar.selectbox("Select Experiment Setup", options=setup_list)
    
    # Filter data
    df = df_all[df_all['Setup_ID'] == selected_setup].copy()

    # 1. DATA TABLE
    st.subheader(f"Raw Data & Calculations: {selected_setup}")
    st.dataframe(df, use_container_width=True)

    # 2. PERFORMANCE PLOTS
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.line(df, x='Current_Density_Acm2', y='Voltage_V', markers=True, 
                       title="Polarization Curve (V-J)", template="plotly_white",
                       hover_data=['Voltage_Efficiency_%', 'Temp_C'])
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.line(df, x='Time_Elapsed_s', y=['Faradaic_Efficiency_%', 'Voltage_Efficiency_%'], 
                       title="Efficiency Profile (%)", template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    # 3. DETAILED METHODOLOGY SECTION
    st.divider()
    st.header("🔬 Detailed Methodology & Physics")
    
    with st.expander("Click to view Calculation Logic and Definitions", expanded=True):
        st.markdown("""
        ### I. Voltage Efficiency ($\eta_{voltage}$)
        Voltage efficiency represents how much of the electrical potential energy is consumed by the chemical reaction versus how much is wasted as heat due to internal resistance (overpotentials).
        
        * **Standard Reference:** We use the **Thermoneutral Voltage ($1.48V$)**. Unlike the reversible voltage ($1.23V$), the thermoneutral voltage accounts for the enthalpy of the water-splitting reaction.
        * **Equation:** $$ \eta_{voltage} = \\frac{1.48V}{V_{measured}} \\times 100 $$
        
        ### II. Faradaic Efficiency ($\eta_{Faraday}$)
        Also known as current efficiency, this measures the "leakage" of electrons. It is the ratio of the actual amount of Hydrogen produced to the amount predicted by Faraday's Law.
        
        * **Theoretical Production Rate ($Q_{th}$):**
        $$ Q_{th} = \\frac{I \cdot t}{z \cdot F} $$
        Where $I$ is current, $z=2$ (electrons per $H_2$ molecule), and $F$ is Faraday's Constant ($96485 \, C/mol$). 
        * **Molar Volume:** We assume Standard Temperature and Pressure (STP) where $1$ mole of gas occupies $22,414 \, mL$.
        * **Final Formula:**
        $$ \eta_{Faraday} = \\frac{Actual \, Flow \, (mL/min)}{Theoretical \, Flow \, (mL/min)} \\times 100 $$

        ### III. Current Density ($j$)
        To compare different electrolyser sizes, we normalize the current against the active surface area of the electrodes.
        * **Formula:** $j = I / Area \, (A/cm^2)$
        """)

    # 4. EXPORT
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.sidebar.download_button("📥 Export Selected Setup", data=buffer.getvalue(), file_name=f"{selected_setup}_report.xlsx")
    except:
        st.sidebar.warning("Export requires 'xlsxwriter' library.")
