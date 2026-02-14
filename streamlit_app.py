"""
Data Analyst Agent - Streamlit Interface
========================================
Streamlit web interface for the data analyst agent with automatic visualization display.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import tempfile
import webbrowser
import threading
import time
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

def main():
    st.title("📊 Data Analyst Agent")
    st.markdown("Upload your data file and ask questions to get insights with visualizations!")

    # Sidebar for file upload and query
    with st.sidebar:
        st.header("Input")

        # File upload
        uploaded_file = st.file_uploader(
            "Choose a CSV or XLSX file",
            type=["csv", "xlsx", "xls"],
            help="Upload your dataset for analysis"
        )

        # Query input
        query = st.text_area(
            "Analysis Query",
            placeholder="e.g., 'Show me the sales trends by month' or 'Analyze customer demographics'",
            height=100,
            help="Describe what you want to analyze or visualize"
        )

        # Analysis button
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)

    # Main content area
    if uploaded_file and query and analyze_button:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name

        try:
            # Show progress
            with st.spinner("🔬 Analyzing your data..."):
                # Run the agent
                result = run_agent(temp_path, query)

            # Display results
            if result.get("error"):
                st.error(f"❌ Error: {result['error']}")
            else:
                # Create tabs for different outputs
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "📈 Visualization", "💻 Analysis Code", "📋 Data Info"])

                with tab1:
                    st.subheader("Analysis Summary")
                    st.markdown(result['summary'])

                with tab2:
                    st.subheader("Visualization")
                    if result.get('viz_path') and Path(result['viz_path']).exists():
                        st.image(result['viz_path'], caption="Generated Chart", use_container_width=True)

                        # Download button for chart
                        with open(result['viz_path'], "rb") as file:
                            st.download_button(
                                label="📥 Download Chart",
                                data=file.read(),
                                file_name="chart.png",
                                mime="image/png"
                            )
                    else:
                        st.info("No visualization was generated for this query.")

                with tab3:
                    st.subheader("Generated Analysis Code")
                    if result.get('analysis_code'):
                        st.code(result['analysis_code'], language='python')
                    if result.get('viz_code'):
                        st.subheader("Visualization Code")
                        st.code(result['viz_code'], language='python')

                with tab4:
                    st.subheader("Dataset Information")
                    if result.get('df_info'):
                        st.text(result['df_info'])

        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")

        finally:
            # Clean up temporary file
            try:
                Path(temp_path).unlink()
            except:
                pass

    elif not uploaded_file:
        # Show welcome message
        st.info("👆 Please upload a CSV or XLSX file to get started")

        # Show sample queries
        with st.expander("💡 Sample Analysis Queries"):
            st.markdown("""
            **Data Quality & Completeness:**
            - "Analyze this dataset for anomalies, missing values, and data quality issues"
            - "Show me data completeness and identify any outliers"

            **Sales Analysis:**
            - "Show me sales trends over time"
            - "Which products are performing best?"
            - "Analyze customer segments and their purchasing patterns"

            **General Analytics:**
            - "What are the key insights from this data?"
            - "Create a dashboard view of the most important metrics"
            - "Show correlations between different variables"
            """)

    elif not query:
        st.info("✏️ Please enter your analysis query")

    # Footer
    st.markdown("---")
    st.markdown("*Powered by LangChain, LangGraph, and Claude AI*")

if __name__ == "__main__":
    # Check if running in main thread (not imported)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-launch":
        # Start auto-launch in background thread
        threading.Thread(target=auto_launch_browser, daemon=True).start()

    main()