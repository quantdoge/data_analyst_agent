"""
Data Analyst Agent - Streamlit Interface
========================================
Streamlit web interface for the data analyst agent.
Supports uploading multiple CSV or XLSX files for analysis.
For XLSX files the user is prompted to select which sheet to use.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import webbrowser
import threading
import time
from io import BytesIO
from data_analyst_agent import run_agent, OUTPUT_DIR

# Configure Streamlit page
st.set_page_config(
    page_title="Data Analyst Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def auto_launch_browser():
    """Auto-launch browser after a short delay."""
    time.sleep(1)
    webbrowser.open("http://localhost:8501")


def get_excel_sheets(file_bytes: bytes) -> list:
    """Return the list of sheet names in an Excel file."""
    try:
        xl = pd.ExcelFile(BytesIO(file_bytes))
        return xl.sheet_names
    except Exception:
        return []


def main():
    st.title("📊 Data Analyst Agent")
    st.markdown(
        "Upload one or more datasets and ask questions to get insights with visualizations!"
    )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Input")

        # Multi-file upload — only CSV and XLSX are accepted
        uploaded_files = st.file_uploader(
            "Choose CSV or XLSX files",
            type=["csv", "xlsx"],
            accept_multiple_files=True,
            help="Upload one or more datasets for analysis (CSV or XLSX only)",
        )

        # Sheet selection for every Excel file that was uploaded
        sheet_selections: dict = {}
        if uploaded_files:
            excel_files = [
                f for f in uploaded_files
                if f.name.lower().endswith((".xlsx", ".xls"))
            ]

            if excel_files:
                st.subheader("Excel Sheet Selection")
                for uf in excel_files:
                    sheets = get_excel_sheets(uf.getvalue())
                    if not sheets:
                        st.warning(f"Could not read sheets from **{uf.name}**")
                        continue

                    if len(sheets) == 1:
                        # Only one sheet — select it automatically
                        sheet_selections[uf.name] = sheets[0]
                        st.info(f"**{uf.name}** → sheet `{sheets[0]}`")
                    else:
                        selected = st.selectbox(
                            f"Sheet for **{uf.name}**",
                            options=sheets,
                            key=f"sheet_{uf.name}",
                            help=f"Select which sheet to analyse from {uf.name}",
                        )
                        sheet_selections[uf.name] = selected

            # Show a brief summary of all uploaded files
            st.subheader("Uploaded Files")
            for uf in uploaded_files:
                size_kb = len(uf.getvalue()) / 1024
                sheet_tag = ""
                if uf.name in sheet_selections:
                    sheet_tag = f" · sheet: `{sheet_selections[uf.name]}`"
                st.markdown(f"- **{uf.name}** ({size_kb:.1f} KB){sheet_tag}")

        # Query input
        query = st.text_area(
            "Analysis Query",
            placeholder=(
                "e.g. 'Show me sales trends by month' or "
                "'Compare revenue across uploaded datasets'"
            ),
            height=100,
            help="Describe what you want to analyse or visualise",
        )

        analyze_button = st.button(
            "🔍 Analyse", type="primary", use_container_width=True
        )

    # ── Main content ─────────────────────────────────────────────────────────
    if uploaded_files and query and analyze_button:
        temp_paths: list = []
        original_names: list = []

        try:
            # Write every uploaded file to a temporary location on disk
            for uf in uploaded_files:
                suffix = Path(uf.name).suffix
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp:
                    tmp.write(uf.getvalue())
                    temp_paths.append(tmp.name)
                original_names.append(uf.name)

            # Map each temp path back to the user-selected sheet name
            sheet_names_map: dict = {}
            for tp, orig_name in zip(temp_paths, original_names):
                if orig_name in sheet_selections:
                    sheet_names_map[tp] = sheet_selections[orig_name]

            # Use the original filename stems as human-readable dataset labels
            file_labels = [Path(name).stem for name in original_names]

            with st.spinner("🔬 Analysing your data..."):
                result = run_agent(
                    temp_paths,
                    query,
                    sheet_names=sheet_names_map,
                    file_labels=file_labels,
                )

            if result.get("error"):
                st.error(f"❌ Error: {result['error']}")
            else:
                tab1, tab2, tab3, tab4 = st.tabs(
                    ["📊 Summary", "📈 Visualisation", "💻 Analysis Code", "📋 Data Info"]
                )

                with tab1:
                    st.subheader("Analysis Summary")
                    st.markdown(result["summary"])

                with tab2:
                    st.subheader("Visualisation")
                    if result.get("viz_path") and Path(result["viz_path"]).exists():
                        st.image(
                            result["viz_path"],
                            caption="Generated Chart",
                            use_container_width=True,
                        )
                        with open(result["viz_path"], "rb") as f:
                            st.download_button(
                                label="📥 Download Chart",
                                data=f.read(),
                                file_name="chart.png",
                                mime="image/png",
                            )
                    else:
                        st.info("No visualisation was generated for this query.")

                with tab3:
                    st.subheader("Generated Analysis Code")
                    if result.get("analysis_code"):
                        st.code(result["analysis_code"], language="python")
                    if result.get("viz_code"):
                        st.subheader("Visualisation Code")
                        st.code(result["viz_code"], language="python")

                with tab4:
                    st.subheader("Dataset Information")
                    if result.get("df_info"):
                        st.text(result["df_info"])

        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")

        finally:
            # Clean up every temporary file
            for tp in temp_paths:
                try:
                    Path(tp).unlink()
                except Exception:
                    pass

    elif not uploaded_files:
        st.info("👆 Please upload one or more CSV or XLSX files to get started")

        with st.expander("💡 Sample Analysis Queries"):
            st.markdown("""
            **Single Dataset:**
            - "Show me sales trends over time"
            - "Which products are performing best?"
            - "Analyse customer segments and their purchasing patterns"
            - "Show me data completeness and identify any outliers"

            **Multiple Datasets:**
            - "Compare revenue trends across all uploaded datasets"
            - "Find common records between datasets and analyse them"
            - "What are the key differences between these datasets?"
            - "Merge the datasets on the customer ID column and summarise"

            **Data Quality:**
            - "Analyse this dataset for anomalies, missing values, and data quality issues"
            - "Show correlations between different variables"
            """)

    elif not query:
        st.info("✏️ Please enter your analysis query")

    # Footer
    st.markdown("---")
    st.markdown("*Powered by LangChain, LangGraph, and Claude AI*")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto-launch":
        threading.Thread(target=auto_launch_browser, daemon=True).start()

    main()
