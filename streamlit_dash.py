import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="H2 Electrolyser Dashboard", layout="wide")
st.title("Electrolyser Performance Dashboard")

@st.cache_data
def load_data(file_path):
    try:
        # 1. Read the data portion (ignoring lines starting with #)
        df = pd.read_csv(file_path, comment='#')
        df.columns = [col.strip() for col in df.columns]
        
        # 2. Extract Active_Area_cm2 from the commented metadata lines
        area = 1.0  # Default fallback if not found
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if "Active_Area_cm2" in line:
                        # Extract the numerical value (e.g., 25.0)
                        area = float(line.split(':')[-1].strip())
                        break
        except Exception:
            st.warning("Could not parse 'Active_Area_cm2' from file header. Using default (1.0).")

        df['Active_Area_cm2_val'] = area
        
        # 3. Calculations with safety for zero-division
        # Voltage Efficiency (1.48V / V_measured)
        df['Voltage_Efficiency_%'] = (1.48 / df['Voltage_V']).replace([float('inf'), -float('inf')], 0) * 100
        
        # Faradaic Efficiency
        F = 96485
        # Theoretical H2 flow (mL/min) = (I * 60 * 22414) / (2 * F)
        df['Theoretical_H2_mLmin'] = (df['Current_A'] * 60 * 22414) / (2 * F)
        df['Faradaic_Efficiency_%'] = (df['H2_Flow_mLmin'] / df['Theoretical_H2_mLmin']).fillna(0) * 100
        
        return df
    except FileNotFoundError:
        st.error(f"File '{file_path}' not found. Please ensure it is in the same directory.")
        return None
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None

# Load the data
df_all = load_data('electrolysis_test.csv')

# Safety check: Only run the app if data was loaded successfully
if df_all is not None:
    # Sidebar Setup Selection
    st.sidebar.header("Navigation")
    
    # Check if Setup_ID exists before unique() call to prevent the TypeError you saw
    if 'Setup_ID' in df_all.columns:
        setup_list = df_all['Setup_ID'].unique()
        selected_setup = st.sidebar.selectbox("Select Experiment Setup", options=setup_list)
        
        # Filter data based on selection
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

        # 3. UPDATED DETAILED METHODOLOGY & PHYSICS
        st.divider()
        st.header("Detailed Methodology & Physics")
        st.markdown(f"""
        This dashboard evaluates electrolyser performance using standard electrochemical equations. 
        **Voltage Efficiency** is calculated as $\eta_{{v}} = (1.48V / V_{{cell}}) \\times 100$, referencing the thermoneutral voltage. 
        **Faradaic Efficiency** is the ratio of actual $H_2$ flow to theoretical flow: $\eta_{{f}} = (Q_{{act}} / Q_{{th}}) \\times 100$. 
        The **Theoretical Flow** follows Faraday's Law: $Q_{{th}} = (I \cdot t \cdot V_{{m}}) / (z \cdot F)$, where $z=2$ and $F=96485\,C/mol$. 
        **Current Density** ($j$) normalizes performance by area: $j = I / Area$ ($A/cm^2$).
        """)

        # 4. EXPORT
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.sidebar.download_button("📥 Export Selected Setup", data=buffer.getvalue(), file_name=f"{selected_setup}_report.xlsx")
        except:
            st.sidebar.warning("Export requires 'xlsxwriter' library.")
    else:
        st.error("Column 'Setup_ID' not found in CSV. Please verify your file headers.")
