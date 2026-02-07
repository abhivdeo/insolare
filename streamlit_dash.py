import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(page_title="Electrochemical Data Dashboard", layout="wide")

st.title("⚡ Interactive Electrochemical Dashboard")
st.markdown("Use the charts below to explore your data. You can hover, zoom, and pan on the graphs.")

# Load and clean data
@st.cache_data
def load_data():
    # Skip row 1 which contains unit labels (A, V, I, A/cm2)
    df = pd.read_csv('sample_data1.csv', skiprows=[1]) 
    
    # Clean column names by stripping whitespace
    df.columns = [col.strip() for col in df.columns]
    
    # Convert all columns to numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

try:
    df = load_data()

    # Sidebar Settings
    st.sidebar.header("Display Settings")
    show_table = st.sidebar.checkbox("Show Data Table", value=True)
    show_stats = st.sidebar.checkbox("Show Summary Statistics", value=True)

    # --- Interactive Visualization Section using Plotly ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Polarization Curve")
        # Plotly Line Chart
        fig1 = px.line(
            df, 
            x='Current Density', 
            y='Volatge (02/12/25)', 
            markers=True,
            title="Voltage vs. Current Density",
            labels={
                'Volatge (02/12/25)': 'Voltage (V)',
                'Current Density': 'Current Density (A/cm²)'
            },
            template="plotly_white"
        )
        fig1.update_traces(line_color='royalblue', marker=dict(size=8))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("V-I Characteristic")
        # Plotly Scatter Chart
        fig2 = px.scatter(
            df, 
            x='Current', 
            y='Volatge (02/12/25)',
            title="Voltage vs. Current",
            labels={
                'Volatge (02/12/25)': 'Voltage (V)',
                'Current': 'Current (I)'
            },
            template="plotly_white",
            trendline="ols"  # Adds a linear trendline for analysis
        )
        fig2.update_traces(marker=dict(size=10, color='crimson'))
        st.plotly_chart(fig2, use_container_width=True)

    # --- Data Display Section ---
    if show_table:
        st.divider()
        st.subheader("Dataset Preview")
        st.dataframe(df, use_container_width=True)

    if show_stats:
        st.subheader("Statistical Summary")
        st.write(df.describe())

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Please ensure 'sample_data1.csv' is present in the same directory.")
