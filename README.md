# 🤖 Data Analyst Agent (LangChain + LangGraph)

A multi-node agent that accepts CSV/XLSX files, analyzes data, generates visualizations, and produces natural language summaries — all orchestrated by a LangGraph state machine.

## Architecture

```
┌─────────┐    ┌─────────┐    ┌───────────┐    ┌───────────┐
│  START   │───▶│ Router  │───▶│  Analyze  │───▶│ Visualize │──┐
└─────────┘    └─────────┘    └───────────┘    └───────────┘  │
                                    │                          │
                                    │ (no viz needed)          │
                                    ▼                          ▼
                               ┌───────────┐            ┌───────────┐
                               │ Summarize │◀───────────│ Summarize │
                               └─────┬─────┘            └───────────┘
                                     ▼
                                 ┌───────┐
                                 │  END  │
                                 └───────┘
```

## Nodes

| Node | Purpose |
|------|---------|
| **Router** | Loads data, inspects schema, decides if visualization is needed |
| **Analyze** | LLM generates & executes pandas code for data analysis |
| **Visualize** | LLM generates matplotlib/seaborn charts |
| **Summarize** | LLM writes natural language summary of findings |

## Files

| File | Description |
|------|-------------|
| `data_analyst_agent.py` | **Production version** — uses Claude API for all LLM nodes |
| `demo_runner.py` | **Demo version** — runs full pipeline with deterministic analysis |
| `sample_sales.csv` | Sample dataset (200 rows of sales data) |

## Quick Start

### Demo (no API key needed)
```bash
python demo_runner.py
```

### Production (requires Anthropic API key)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python data_analyst_agent.py sample_sales.csv "Show me revenue by region and product trends"
```

## Requirements

```
langchain
langchain-anthropic
langgraph
pandas
openpyxl
matplotlib
seaborn
```

## State Schema

```python
class AgentState(TypedDict):
    file_path: str           # Input CSV/XLSX path
    user_query: str          # User's analysis question
    df_info: str             # DataFrame metadata for LLM context
    analysis_code: str       # Generated pandas code
    analysis_result: str     # Execution output
    needs_visualization: bool # Router decision
    viz_code: str            # Generated matplotlib code
    viz_path: str            # Saved chart path
    summary: str             # Final natural language summary
    error: str               # Error tracking
```

## Supported Queries

- Revenue/sales breakdowns by dimension
- Profit and margin analysis
- Customer rating insights
- Time-series trends
- General dataset overviews
- Any custom analytical question (production version)
