"""
Demo Runner: Data Analyst Agent (LangChain + LangGraph)
========================================================
Demonstrates the full pipeline without requiring an API key.
Uses deterministic analysis to showcase the architecture.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from typing import TypedDict, Literal
from pathlib import Path

from langgraph.graph import StateGraph, END

OUTPUT_DIR = Path("./result")
OUTPUT_DIR.mkdir(exist_ok=True)


# ─── State ───────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    file_path: str
    user_query: str
    df_info: str
    analysis_result: str
    needs_visualization: bool
    viz_path: str
    summary: str
    error: str
    step_log: list  # tracks which nodes were visited


def load_dataframe(file_path: str) -> pd.DataFrame:
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported: {ext}")


def get_df_info(df: pd.DataFrame) -> str:
    parts = [
        f"Shape: {df.shape[0]} rows × {df.shape[1]} columns",
        f"\nColumns: {', '.join(df.columns.tolist())}",
        f"\nTypes:\n{df.dtypes.to_string()}",
        f"\nFirst 3 rows:\n{df.head(3).to_string()}",
        f"\nStats:\n{df.describe(include='all').to_string()}",
    ]
    nulls = df.isnull().sum()
    if nulls.any():
        parts.append(f"\nNull Values:\n{nulls[nulls > 0].to_string()}")
    return "\n".join(parts)


# ─── Node: Router ────────────────────────────────────────────────────────────
def router_node(state: AgentState) -> AgentState:
    print("🔀 [Router] Loading data and determining route...")
    try:
        df = load_dataframe(state["file_path"])
        df_info = get_df_info(df)

        # Simple heuristic routing (LLM would do this in production)
        query_lower = state["user_query"].lower()
        viz_keywords = ["chart", "plot", "graph", "visual", "trend", "distribution",
                        "compare", "top", "breakdown", "over time", "by region",
                        "by product", "show", "display"]
        needs_viz = any(kw in query_lower for kw in viz_keywords)
        # Default to True for most analytical queries
        if not needs_viz and any(w in query_lower for w in ["revenue", "sales", "profit", "rating"]):
            needs_viz = True

        print(f"   → Data loaded: {df.shape[0]} rows × {df.shape[1]} cols")
        print(f"   → Visualization needed: {needs_viz}")

        return {
            **state,
            "df_info": df_info,
            "needs_visualization": needs_viz,
            "error": "",
            "step_log": state.get("step_log", []) + ["router"],
        }
    except Exception as e:
        return {**state, "error": str(e), "step_log": state.get("step_log", []) + ["router(error)"]}


# ─── Node: Analyze ───────────────────────────────────────────────────────────
def analyze_node(state: AgentState) -> AgentState:
    print("🔍 [Analyze] Running data analysis...")
    if state.get("error"):
        return state

    try:
        df = load_dataframe(state["file_path"])
        query_lower = state["user_query"].lower()
        results = []

        # ── Comprehensive analysis based on query keywords ──

        # Revenue analysis
        if any(w in query_lower for w in ["revenue", "sales", "income", "money"]):
            total = df["Revenue"].sum()
            avg = df["Revenue"].mean()
            results.append(f"💰 Total Revenue: ${total:,.2f}")
            results.append(f"   Average per transaction: ${avg:,.2f}")

            if "Region" in df.columns:
                by_region = df.groupby("Region")["Revenue"].agg(["sum", "mean", "count"])
                by_region.columns = ["Total Revenue", "Avg Revenue", "Transactions"]
                by_region = by_region.sort_values("Total Revenue", ascending=False)
                results.append(f"\n📍 Revenue by Region:\n{by_region.to_string()}")

            if "Product" in df.columns:
                by_product = df.groupby("Product")["Revenue"].agg(["sum", "mean", "count"])
                by_product.columns = ["Total Revenue", "Avg Revenue", "Transactions"]
                by_product = by_product.sort_values("Total Revenue", ascending=False)
                results.append(f"\n📦 Revenue by Product:\n{by_product.to_string()}")

        # Profit analysis
        if any(w in query_lower for w in ["profit", "margin", "cost"]):
            if "Profit" in df.columns:
                total_profit = df["Profit"].sum()
                avg_profit = df["Profit"].mean()
                profitable = (df["Profit"] > 0).sum()
                results.append(f"📈 Total Profit: ${total_profit:,.2f}")
                results.append(f"   Average Profit: ${avg_profit:,.2f}")
                results.append(f"   Profitable transactions: {profitable}/{len(df)} ({profitable/len(df)*100:.1f}%)")

                if "Product" in df.columns:
                    profit_by_prod = df.groupby("Product")["Profit"].agg(["sum", "mean"])
                    profit_by_prod.columns = ["Total Profit", "Avg Profit"]
                    profit_by_prod = profit_by_prod.sort_values("Total Profit", ascending=False)
                    results.append(f"\n📦 Profit by Product:\n{profit_by_prod.to_string()}")

        # Rating analysis
        if any(w in query_lower for w in ["rating", "satisfaction", "customer"]):
            if "Customer_Rating" in df.columns:
                avg_rating = df["Customer_Rating"].mean()
                results.append(f"⭐ Average Customer Rating: {avg_rating:.2f}/5.0")
                if "Product" in df.columns:
                    rating_by_prod = df.groupby("Product")["Customer_Rating"].agg(["mean", "min", "max"])
                    rating_by_prod.columns = ["Avg Rating", "Min", "Max"]
                    rating_by_prod = rating_by_prod.sort_values("Avg Rating", ascending=False)
                    results.append(f"\n📦 Ratings by Product:\n{rating_by_prod.to_string()}")

        # Trend / time analysis
        if any(w in query_lower for w in ["trend", "time", "month", "date", "over time"]):
            if "Date" in df.columns:
                monthly = df.groupby("Date").agg({
                    "Revenue": "sum",
                    "Units_Sold": "sum",
                    "Profit": "sum"
                }).sort_index()
                results.append(f"\n📅 Monthly Trends:\n{monthly.to_string()}")

        # General / overview
        if any(w in query_lower for w in ["overview", "summary", "tell me about", "describe", "overall"]):
            results.append(f"📊 Dataset Overview:")
            results.append(f"   Rows: {len(df)}, Columns: {len(df.columns)}")
            for col in df.select_dtypes(include=[np.number]).columns:
                results.append(f"   {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")

        if not results:
            # Fallback: provide general stats
            results.append("📊 General Dataset Analysis:")
            results.append(f"   Rows: {len(df)}, Columns: {len(df.columns)}")
            for col in df.select_dtypes(include=[np.number]).columns[:5]:
                results.append(f"   {col}: sum={df[col].sum():,.2f}, mean={df[col].mean():,.2f}")

        analysis_result = "\n".join(results)
        print(f"   → Analysis complete ({len(results)} findings)")

        return {
            **state,
            "analysis_result": analysis_result,
            "step_log": state.get("step_log", []) + ["analyze"],
        }
    except Exception as e:
        return {
            **state,
            "analysis_result": f"Analysis error: {str(e)}",
            "step_log": state.get("step_log", []) + ["analyze(error)"],
        }


# ─── Node: Visualize ────────────────────────────────────────────────────────
def visualize_node(state: AgentState) -> AgentState:
    print("📈 [Visualize] Generating charts...")
    if state.get("error"):
        return state

    try:
        df = load_dataframe(state["file_path"])
        query_lower = state["user_query"].lower()

        sns.set_style("whitegrid")
        palette = sns.color_palette("husl", 8)

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f"Data Analysis: {state['user_query']}", fontsize=16, fontweight="bold", y=0.98)

        # Chart 1: Revenue by Region (bar)
        if "Region" in df.columns and "Revenue" in df.columns:
            region_rev = df.groupby("Region")["Revenue"].sum().sort_values(ascending=True)
            bars = axes[0, 0].barh(region_rev.index, region_rev.values, color=palette[:len(region_rev)])
            axes[0, 0].set_title("Revenue by Region", fontsize=13, fontweight="bold")
            axes[0, 0].set_xlabel("Total Revenue ($)")
            for bar, val in zip(bars, region_rev.values):
                axes[0, 0].text(val + val * 0.01, bar.get_y() + bar.get_height() / 2,
                               f"${val:,.0f}", va="center", fontsize=10)

        # Chart 2: Revenue by Product (bar)
        if "Product" in df.columns and "Revenue" in df.columns:
            prod_rev = df.groupby("Product")["Revenue"].sum().sort_values(ascending=False)
            bars = axes[0, 1].bar(prod_rev.index, prod_rev.values, color=palette[:len(prod_rev)])
            axes[0, 1].set_title("Revenue by Product", fontsize=13, fontweight="bold")
            axes[0, 1].set_ylabel("Total Revenue ($)")
            axes[0, 1].tick_params(axis="x", rotation=30)

        # Chart 3: Monthly Trend (line)
        if "Date" in df.columns and "Revenue" in df.columns:
            monthly = df.groupby("Date")["Revenue"].sum().sort_index()
            axes[1, 0].plot(range(len(monthly)), monthly.values, marker="o",
                           linewidth=2.5, color=palette[0], markersize=8)
            axes[1, 0].fill_between(range(len(monthly)), monthly.values, alpha=0.15, color=palette[0])
            axes[1, 0].set_title("Monthly Revenue Trend", fontsize=13, fontweight="bold")
            axes[1, 0].set_ylabel("Revenue ($)")
            axes[1, 0].set_xticks(range(len(monthly)))
            axes[1, 0].set_xticklabels(monthly.index, rotation=45, ha="right", fontsize=9)

        # Chart 4: Profit Distribution or Rating Distribution
        if "Profit" in df.columns:
            colors = ["#2ecc71" if x > 0 else "#e74c3c" for x in df["Profit"]]
            axes[1, 1].hist(df["Profit"], bins=25, color=palette[2], edgecolor="white", alpha=0.8)
            axes[1, 1].axvline(x=0, color="red", linestyle="--", linewidth=1.5, label="Break-even")
            axes[1, 1].axvline(x=df["Profit"].mean(), color="blue", linestyle="--",
                              linewidth=1.5, label=f"Mean: ${df['Profit'].mean():,.0f}")
            axes[1, 1].set_title("Profit Distribution", fontsize=13, fontweight="bold")
            axes[1, 1].set_xlabel("Profit ($)")
            axes[1, 1].set_ylabel("Frequency")
            axes[1, 1].legend()

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        viz_path = str(OUTPUT_DIR / "analysis_chart.png")
        plt.savefig(viz_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()

        print(f"   → Chart saved: {viz_path}")

        return {
            **state,
            "viz_path": viz_path,
            "step_log": state.get("step_log", []) + ["visualize"],
        }
    except Exception as e:
        plt.close("all")
        print(f"   → Visualization error: {e}")
        return {
            **state,
            "viz_path": "",
            "step_log": state.get("step_log", []) + ["visualize(error)"],
        }


# ─── Node: Summarize ────────────────────────────────────────────────────────
def summarize_node(state: AgentState) -> AgentState:
    print("📝 [Summarize] Generating summary...")
    if state.get("error"):
        return {**state, "summary": f"Error: {state['error']}"}

    df = load_dataframe(state["file_path"])

    summary_parts = [
        f"## Data Analysis Report",
        f"**Query:** {state['user_query']}",
        f"**Dataset:** {df.shape[0]} rows × {df.shape[1]} columns",
        f"\n### Key Findings\n",
        state.get("analysis_result", "No analysis available."),
    ]

    if state.get("viz_path"):
        summary_parts.append(f"\n### Visualization")
        summary_parts.append(f"A comprehensive dashboard has been generated with 4 charts:")
        summary_parts.append(f"  1. Revenue by Region (horizontal bar)")
        summary_parts.append(f"  2. Revenue by Product (vertical bar)")
        summary_parts.append(f"  3. Monthly Revenue Trend (line chart)")
        summary_parts.append(f"  4. Profit Distribution (histogram)")

    # Add insights
    summary_parts.append(f"\n### Insights")
    if "Profit" in df.columns:
        profitable_pct = (df["Profit"] > 0).mean() * 100
        summary_parts.append(f"  • {profitable_pct:.1f}% of transactions are profitable")
    if "Region" in df.columns and "Revenue" in df.columns:
        top_region = df.groupby("Region")["Revenue"].sum().idxmax()
        summary_parts.append(f"  • Top performing region: {top_region}")
    if "Product" in df.columns and "Revenue" in df.columns:
        top_product = df.groupby("Product")["Revenue"].sum().idxmax()
        summary_parts.append(f"  • Highest revenue product: {top_product}")

    summary = "\n".join(summary_parts)
    print(f"   → Summary complete")

    return {
        **state,
        "summary": summary,
        "step_log": state.get("step_log", []) + ["summarize"],
    }


# ─── Conditional Edge ────────────────────────────────────────────────────────
def should_visualize(state: AgentState) -> str:
    if state.get("error"):
        return "summarize"
    if state.get("needs_visualization", False):
        return "visualize"
    return "summarize"


# ─── Build Graph ─────────────────────────────────────────────────────────────
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("visualize", visualize_node)
    workflow.add_node("summarize", summarize_node)

    workflow.set_entry_point("router")
    workflow.add_edge("router", "analyze")
    workflow.add_conditional_edges(
        "analyze",
        should_visualize,
        {"visualize": "visualize", "summarize": "summarize"}
    )
    workflow.add_edge("visualize", "summarize")
    workflow.add_edge("summarize", END)

    return workflow.compile()


# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("  🤖 Data Analyst Agent (LangChain + LangGraph)")
    print("=" * 70)

    file_path = "./sample_sales.csv"
    query = "Show me revenue breakdown by region and product, with monthly trends and profit analysis"

    print(f"\n📂 File: {file_path}")
    print(f"❓ Query: {query}")
    print("-" * 70)

    graph = build_graph()

    initial_state: AgentState = {
        "file_path": file_path,
        "user_query": query,
        "df_info": "",
        "analysis_result": "",
        "needs_visualization": False,
        "viz_path": "",
        "summary": "",
        "error": "",
        "step_log": [],
    }

    print("\n🚀 Running agent pipeline...\n")
    result = graph.invoke(initial_state)

    print("\n" + "=" * 70)
    print("  📋 RESULTS")
    print("=" * 70)
    print(f"\n🔄 Graph path: {' → '.join(result['step_log'])}")
    print(f"\n{result['summary']}")

    if result.get("viz_path"):
        print(f"\n📈 Chart: {result['viz_path']}")

    print("\n✅ Agent pipeline complete!")
