"""
Data Analyst Agent - Streamlit Interface
========================================
Streamlit web interface for the data analyst agent.
Supports uploading multiple CSV or XLSX files for analysis.
For XLSX files the user can select one, several, or all sheets — each
selected sheet is loaded as its own independent dataset.
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


def get_excel_sheets(file_bytes: bytes) -> tuple:
    """Return (sheet_names, error_message). error_message is '' on success."""
    try:
        xl = pd.ExcelFile(BytesIO(file_bytes))
        return xl.sheet_names, ""
    except Exception as e:
        return [], str(e)


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
                    sheets, read_error = get_excel_sheets(uf.getvalue())
                    if read_error:
                        st.error(
                            f"**{uf.name}** could not be read: {read_error}\n\n"
                            "This file will be skipped. Try re-uploading or check "
                            "that the file is not corrupted."
                        )
                        continue

                    if len(sheets) == 1:
                        # Only one sheet — select it automatically
                        sheet_selections[uf.name] = sheets
                        st.info(f"**{uf.name}** → sheet `{sheets[0]}` (auto-selected)")
                    else:
                        selected = st.multiselect(
                            f"Sheets in **{uf.name}**",
                            options=sheets,
                            default=sheets,
                            key=f"sheet_{uf.name}",
                            help=(
                                "Select one or more sheets. "
                                "Each selected sheet becomes a separate dataset."
                            ),
                        )
                        if not selected:
                            st.warning(
                                f"No sheets selected for **{uf.name}** — "
                                "this file will be skipped during analysis."
                            )
                        else:
                            sheet_selections[uf.name] = selected
                            n_sel, n_tot = len(selected), len(sheets)
                            if n_sel == n_tot:
                                st.caption(
                                    f"All {n_tot} sheets selected — "
                                    "each will be loaded as a separate dataset."
                                )
                            else:
                                names_str = ", ".join(f"`{s}`" for s in selected)
                                st.caption(
                                    f"{n_sel} of {n_tot} sheets selected: {names_str}"
                                )

            # Show a brief summary of all uploaded files
            st.subheader("Uploaded Files")
            for uf in uploaded_files:
                size_kb = len(uf.getvalue()) / 1024
                sheet_tag = ""
                if uf.name in sheet_selections:
                    sel = sheet_selections[uf.name]
                    sheet_tag = " · sheets: " + ", ".join(f"`{s}`" for s in sel)
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

            # Build filtered file list and sheet mapping.
            # Skip xlsx files where no sheets were selected or the file was unreadable.
            analysis_paths: list = []
            analysis_labels: list = []
            sheet_names_map: dict = {}
            for tp, orig_name in zip(temp_paths, original_names):
                is_excel = orig_name.lower().endswith((".xlsx", ".xls"))
                if is_excel and orig_name not in sheet_selections:
                    continue
                analysis_paths.append(tp)
                analysis_labels.append(Path(orig_name).stem)
                if orig_name in sheet_selections:
                    sheet_names_map[tp] = sheet_selections[orig_name]

            if not analysis_paths:
                st.warning(
                    "No valid datasets to analyse. "
                    "Please check your file and sheet selections."
                )
            else:
                with st.spinner("🔬 Analysing your data..."):
                    result = run_agent(
                        analysis_paths,
                        query,
                        sheet_names=sheet_names_map,
                        file_labels=analysis_labels,
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
