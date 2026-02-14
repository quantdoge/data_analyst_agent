"""
Data Analyst Agent - Auto Launcher
==================================
Automatically launches the Streamlit app and opens it in the browser.
"""

import subprocess
import webbrowser
import time
import threading
import sys
from pathlib import Path

def launch_streamlit():
    """Launch Streamlit app with auto browser opening."""
    script_dir = Path(__file__).parent
    streamlit_app = script_dir / "streamlit_app.py"

    print("🚀 Starting Data Analyst Agent...")
    print("📊 Opening Streamlit interface...")

    # Launch Streamlit
    try:
        # Use conda environment 'crewaitut'
        conda_cmd = [
            "C:/Users/jason/anaconda3/Scripts/conda.exe", "run", "-n", "crewaitut",
            "--no-capture-output", "python", "-m", "streamlit", "run", str(streamlit_app),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]

        # Start Streamlit in background
        process = subprocess.Popen(conda_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Wait a moment for server to start
        time.sleep(3)

        # Open browser
        print("🌐 Opening browser...")
        webbrowser.open("http://localhost:8501")

        print("✅ Data Analyst Agent is running at http://localhost:8501")
        print("Press Ctrl+C to stop the server")

        # Wait for process to complete
        process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down Data Analyst Agent...")
        process.terminate()
    except Exception as e:
        print(f"❌ Error launching Streamlit: {e}")

if __name__ == "__main__":
    launch_streamlit()