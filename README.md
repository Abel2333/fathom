# Fathom Deep Research Agent

A sophisticated multi-agent research system built with LangGraph and LangChain that conducts comprehensive, multi-layered research on any topic.

## Features

- 🔍 **Deep Research** - Multi-agent architecture with supervisor and parallel researchers
- 📊 **Real-Time Streaming** - Live progress updates and streaming report generation
- 🔭 **Full Observability** - Langfuse integration for LLM tracing and cost tracking
- ⚙️ **Highly Configurable** - Support for multiple LLM providers and customizable research strategies
- 📝 **Comprehensive Reports** - Markdown reports with citations and structured analysis

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run your first research
fathom "What is LangGraph?"
```

## Documentation

📚 **[Full Documentation](docs/)** - Complete guides and references

### Quick Links

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Langfuse Setup](docs/LANGFUSE_SETUP.md)** - Enable LLM observability
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Technical Overview](docs/TECHNICAL_OVERVIEW.md)** - Complete technical details
- **[API Reference](docs/API.md)** - Programmatic usage

## Architecture

```
User Query
    ↓
Clarification Agent → Research Brief
    ↓
Supervisor Agent → Plans research strategy
    ↓
Researcher Agents (parallel) → Conduct focused research
    ↓
Report Generator → Comprehensive markdown report
```

## Configuration

Edit `src/fathom/config/config.toml`:

```toml
[research]
max_depth = 8              # Research iterations
concurrency = 4            # Parallel researchers

[llm]
report_model_name = "kimi-k2-thinking"
research_model_name = "kimi-k2-thinking"
timeout = 60
max_retries = 3
```

## Environment Variables

Required:

```bash
API_KEY=your_llm_api_key
BASE_URL=https://api.deepseek.com
TAVILY_API_KEY=your_tavily_key
```

Optional (for observability):

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

See [.env.example](.env.example) for complete template.

## Example Usage

```bash
# Simple research
fathom "What are the latest developments in AI agents?"

# From stdin
echo "Explain quantum computing" | fathom

# View logs
tail -f logs/fathom.log

# Check reports
ls -lt reports/
```

## Recent Improvements

- ✅ **Streaming Output** - Real-time progress indicators during research
- ✅ **Langfuse Integration** - Full LLM observability and cost tracking
- ✅ **Timeout Prevention** - Streaming prevents timeouts with reasoning models
- ✅ **Better Error Handling** - Comprehensive retry logic and graceful degradation

## Requirements

- Python 3.13+
- LLM API key (DeepSeek, OpenAI, Anthropic, or compatible)
- Tavily API key for web search
- Optional: Langfuse account for observability

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Logs**: `logs/fathom.log`

## License

[Add your license here]

---

**Happy Researching! 🔍**

For detailed documentation, see [docs/README.md](docs/README.md)
