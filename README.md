# Fathom

A powerful deep research agent built with LangGraph and LangChain that conducts comprehensive research using parallel AI agents and web search.

## Features

- 🔍 **Intelligent Web Search**: Powered by Tavily API for high-quality search results
- 🤖 **Multi-Agent Architecture**: Parallel researcher agents for efficient information gathering
- 📊 **Comprehensive Reports**: Automatically generates well-structured markdown reports with full citations
- 🔄 **Streaming Output**: Real-time feedback during research and report generation
- 📝 **Smart File Naming**: Automatically extracts report titles for meaningful filenames
- 🌐 **Multilingual Support**: Works with any language (English, Chinese, etc.)
- 🎯 **Source Tracking**: Preserves and displays all source URLs with clickable links

## Architecture

Fathom uses a hierarchical multi-agent system:

```
User Query
    ↓
Clarification Agent (optional)
    ↓
Supervisor Agent
    ↓
├─→ Researcher 1 (parallel)
├─→ Researcher 2 (parallel)
├─→ Researcher 3 (parallel)
└─→ Researcher 4 (parallel)
    ↓
Report Generator
    ↓
Final Report (auto-saved)
```

### Agent Roles

- **Clarification Agent**: Asks clarifying questions if the user's request is ambiguous
- **Supervisor Agent**: Plans research strategy and delegates tasks to researchers
- **Researcher Agents**: Conduct focused research on specific topics using web search
- **Report Generator**: Synthesizes all findings into a comprehensive report

## Installation

### Prerequisites

- Python 3.13+
- API keys for:
  - DeepSeek API (or OpenAI/Anthropic)
  - Tavily Search API

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd fathom
```

2. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -e .
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:

```env
API_KEY=your_deepseek_api_key
BASE_URL=https://api.deepseek.com/v1
TAVILY_API_KEY=your_tavily_api_key
```

5. Configure settings in `src/fathom/config/config.toml`:

```toml
[llm]
provider = "deepseek"
report_model_name = "deepseek-reasoner"
summary_model_name = "deepseek-chat"
research_model_name = "deepseek-chat"

[search]
provider = "tavily"
max_results = 5

[output]
dir = "./reports"
format = "markdown"
language = "Chinese"  # or "English"
```

## Usage

### Command Line

```bash
# Run the research agent
fathom

# Or run directly with Python
python -m fathom.cli
```

### Example Session

```
Welcome to Fathom Research Agent!

You: I need a comprehensive analysis of US population growth from 2006 to 2026

[Clarification Agent may ask questions if needed]

[Supervisor delegates research to multiple parallel agents]
[R-50cb78] RESEARCHER LOOP: Starting
[R-50cb78] Topic: Overall US population growth trends (2006-2026)...

[R-e878aa] RESEARCHER LOOP: Starting
[R-e878aa] Topic: Birth and death rate factors (2006-2026)...

[Research in progress with streaming output...]

[Report generation with streaming output...]

✓ Report saved to: ./reports/report_20260115_004607_US_Population_Growth_Analysis_2006-2026.md
```

## Configuration

### Model Configuration

Edit `src/fathom/config/config.toml`:

```toml
[llm]
provider = "deepseek"  # Options: openai, anthropic, deepseek
report_model_name = "deepseek-reasoner"  # For final report generation
summary_model_name = "deepseek-chat"     # For summarization
research_model_name = "deepseek-chat"    # For research agents
clarify_model_name = "deepseek-chat"     # For clarification
temperature = 0.0
timeout = 60
```

### Research Strategy

```toml
[research]
allow_clarification = true    # Ask clarifying questions
max_depth = 6                 # Maximum research iterations
max_sub_questions = 3         # Max sub-questions per iteration
total_query_limit = 20        # Safety limit for API calls
max_tool_calls = 40           # Max tool calls per researcher
concurrency = 4               # Number of parallel researchers
```

### Output Configuration

```toml
[output]
dir = "./reports"              # Output directory
format = "markdown"            # Output format
language = "Chinese"           # Report language
tone = "professional"          # Writing tone
include_citations = true       # Include source citations
```

## Project Structure

```
fathom/
├── src/fathom/
│   ├── agents/
│   │   ├── clarification.py    # Clarification agent
│   │   ├── supervisor.py       # Supervisor agent
│   │   ├── researcher.py       # Researcher agents
│   │   ├── report.py           # Report generator
│   │   └── workflow.py         # Main workflow
│   ├── tools/
│   │   ├── search.py           # Tavily search integration
│   │   └── utils.py            # Utility tools
│   ├── models/
│   │   └── schema.py           # Data models
│   ├── config/
│   │   ├── config.toml         # Configuration file
│   │   └── loader.py           # Config loader
│   ├── prompts.py              # System prompts
│   └── cli.py                  # CLI entry point
├── reports/                    # Generated reports
├── logs/                       # Application logs
├── tests/                      # Unit tests
└── pyproject.toml             # Project metadata
```

## Key Features Explained

### Parallel Research

The supervisor agent can delegate multiple research tasks simultaneously:

```python
# Supervisor delegates 4 research tasks in parallel
[R-50cb78] Researching: Overall population trends
[R-e878aa] Researching: Birth/death rates
[R-9b864c] Researching: Immigration factors
[R-8f2e91] Researching: Economic factors
```

Each researcher has a unique ID (e.g., `R-50cb78`) for easy log tracking.

### Streaming Output

Both compression and report generation use streaming for real-time feedback:

```python
# Compression phase
[R-50cb78] Starting compression with streaming output...
Based on the research findings, the US population...

# Report generation
FINAL REPORT: starting generation
Using astream for report generation
# US Population Growth Analysis (2006-2026)

The United States experienced...
```

### Smart Filename Generation

Reports are automatically saved with meaningful filenames:

1. **Primary**: Extract title from report content (first H1 heading)

   ```
   report_20260115_004607_US_Population_Growth_Analysis_2006-2026.md
   ```

2. **Fallback**: Use first 30 chars of research brief

   ```
   report_20260115_004607_US_population_analysis.md
   ```

3. **Last resort**: Timestamp only
   ```
   report_20260115_004607.md
   ```

### Source Citations

Reports include comprehensive source citations:

**Inline citations**:

```markdown
According to the [U.S. Census Bureau 2024 Report](https://www.census.gov/...),
the population grew by 15% from 2006 to 2026.
```

**Sources section**:

```markdown
## Sources

- [U.S. Census Bureau Population Estimates](https://www.census.gov/programs-surveys/popest.html)
- [CDC National Vital Statistics Reports](https://www.cdc.gov/nchs/products/nvsr.htm)
- [Pew Research Center Immigration Data](https://www.pewresearch.org/...)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project uses Ruff for linting:

```bash
ruff check src/
ruff format src/
```

### Logging

Logs are written to `logs/fathom.log`:

```toml
[logging]
level = "INFO"              # DEBUG, INFO, WARNING, ERROR
log_to_file = true
log_file = "logs/fathom.log"
```

## Troubleshooting

### Tavily Search Not Working

If search is not being called:

1. Check that `TAVILY_API_KEY` is set in `.env`
2. Verify the `@tool` decorator is present on `tavily_search` function
3. Check logs for "Tavily search invoked" messages

### Type Errors

If you see type errors related to `BaseTool`:

```python
# Correct import
from langchain_core.tools import BaseTool, tool

# Correct type annotation
def get_all_tools() -> list[BaseTool]:
    ...
```

### Report Not Saving

Check:

1. Output directory exists and is writable: `./reports`
2. Permissions on the directory
3. Logs for "Report saved to:" message

### Parallel Execution Issues

To verify researchers are running in parallel:

```bash
# Check logs for simultaneous timestamps
grep "RESEARCHER LOOP: Starting" logs/fathom.log

# Should show multiple researchers starting within milliseconds
[R-50cb78] RESEARCHER LOOP: Starting  # 23:01:43.742
[R-e878aa] RESEARCHER LOOP: Starting  # 23:01:43.756 (14ms later)
[R-9b864c] RESEARCHER LOOP: Starting  # 23:01:43.772 (30ms later)
```

## Performance Tips

1. **Adjust concurrency**: Increase `concurrency` in config for faster research

   ```toml
   [research]
   concurrency = 8  # Run up to 8 researchers in parallel
   ```

2. **Limit search depth**: Reduce `max_depth` for quicker results

   ```toml
   [research]
   max_depth = 3  # Fewer iterations
   ```

3. **Use faster models**: Switch to lighter models for summarization
   ```toml
   [llm]
   summary_model_name = "deepseek-chat"  # Faster than deepseek-reasoner
   ```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

Built with:

- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [Tavily](https://tavily.com/) - Search API
- [DeepSeek](https://www.deepseek.com/) - LLM provider

## Support

For issues and questions:

- GitHub Issues: [Create an issue]
- Documentation: See `src/fathom/agents/README.md` for architecture details

---

**Note**: This is a research tool. Always verify information from generated reports with original sources.
