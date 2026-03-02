import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

# -----------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------
st.set_page_config(
    page_title="H2 Electrolyser Performance Dashboard",
    layout="wide",
    page_icon="⚡"
)

st.title("Electrolyser Performance Dashboard")
st.markdown("Advanced performance analytics for electrochemical hydrogen systems")

# -----------------------------------------------------------
# Data Loader
# -----------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(file_path):
    try:
        df = pd.read_csv(file_path, comment='#')
        df.columns = df.columns.str.strip()

        # Extract Active Area from metadata
        active_area = 1.0
        try:
            with open(file_path, "r") as f:
                for line in f:
                    if "Active_Area_cm2" in line:
                        active_area = float(line.split(":")[-1].strip())
                        break
        except:
            st.warning("Active_Area_cm2 not found. Defaulting to 1.0 cm²")

        df["Active_Area_cm2"] = active_area

        # --- Calculations ---
        F = 96485  # Faraday constant

        df["Voltage_Efficiency_%"] = (
            1.48 / df["Voltage_V"]
        ).replace([float("inf"), -float("inf")], 0) * 100

        df["Theoretical_H2_mLmin"] = (
            df["Current_A"] * 60 * 22414
        ) / (2 * F)

        df["Faradaic_Efficiency_%"] = (
            df["H2_Flow_mLmin"] / df["Theoretical_H2_mLmin"]
        ).fillna(0) * 100

        return df

    except Exception as e:
        st.error(f"Data loading error: {e}")
        return None


# -----------------------------------------------------------
# Load Data
# -----------------------------------------------------------
df_all = load_data("electrolysis_test.csv")

if df_all is not None:

    # -------------------------------------------------------
    # Sidebar Controls
    # -------------------------------------------------------
    st.sidebar.header("🔎 Experiment Selection")

    if "Setup_ID" in df_all.columns:

        setup_list = sorted(df_all["Setup_ID"].unique())
        selected_setup = st.sidebar.selectbox(
            "Select Setup",
            setup_list
        )

        df = df_all[df_all["Setup_ID"] == selected_setup].copy()

        # -------------------------------------------------------
        # KPI SECTION
        # -------------------------------------------------------
        st.subheader(f"📊 Summary Metrics — {selected_setup}")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Max Voltage Efficiency (%)",
            f"{df['Voltage_Efficiency_%'].max():.2f}"
        )

        col2.metric(
            "Avg Faradaic Efficiency (%)",
            f"{df['Faradaic_Efficiency_%'].mean():.2f}"
        )

        col3.metric(
            "Max Current Density (A/cm²)",
            f"{df['Current_Density_Acm2'].max():.3f}"
        )

        st.divider()

        # -------------------------------------------------------
        # VISUALIZATION SECTION
        # -------------------------------------------------------
        st.subheader("📈 Performance Visualization")

        c1, c2 = st.columns(2)

        with c1:
            fig1 = px.line(
                df,
                x="Current_Density_Acm2",
                y="Voltage_V",
                markers=True,
                template="plotly_white",
                title="Polarization Curve (Voltage vs Current Density)",
                hover_data=[
                    "Voltage_Efficiency_%",
                    "Temp_C"
                ]
            )
            fig1.update_layout(title_x=0.05)
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            fig2 = px.line(
                df,
                x="Time_Elapsed_s",
                y=[
                    "Faradaic_Efficiency_%",
                    "Voltage_Efficiency_%"
                ],
                template="plotly_white",
                title="Efficiency Profile Over Time"
            )
            fig2.update_layout(title_x=0.05)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # -------------------------------------------------------
        # DATA TABLE
        # -------------------------------------------------------
        with st.expander("📄 View Detailed Data Table"):
            st.dataframe(df, use_container_width=True)

        # -------------------------------------------------------
        # METHODOLOGY SECTION
        # -------------------------------------------------------
        st.subheader("📘 Methodology & Electrochemical Framework")

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


        # -------------------------------------------------------
        # EXPORT
        # -------------------------------------------------------
        st.sidebar.divider()
        st.sidebar.header("📤 Export")

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Performance_Data")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        st.sidebar.download_button(
            label="Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"{selected_setup}_Performance_Report_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.error("Column 'Setup_ID' not found in dataset.")
