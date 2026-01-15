# Fathom Documentation

Welcome to the Fathom Deep Research Agent documentation!

## Quick Links

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes

### Setup & Configuration
- **[LANGFUSE_SETUP.md](LANGFUSE_SETUP.md)** - Complete guide for LLM observability with Langfuse
- **[.env.example](../.env.example)** - Environment variables template

### Troubleshooting & Optimization
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[STREAMING_IMPROVEMENTS.md](STREAMING_IMPROVEMENTS.md)** - How streaming prevents timeouts

### Technical Documentation
- **[TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md)** - Complete technical summary of all improvements
- **[API.md](API.md)** - API reference and programmatic usage
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

## Documentation Overview

### For New Users

1. Start with **[QUICKSTART.md](QUICKSTART.md)** to set up your environment
2. Configure **[Langfuse](LANGFUSE_SETUP.md)** for observability (optional but recommended)
3. Run your first research query

### For Troubleshooting

1. Check **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for common issues
2. Review **[STREAMING_IMPROVEMENTS.md](STREAMING_IMPROVEMENTS.md)** if you see timeout errors
3. Check logs in `logs/fathom.log`

### For Developers

1. Read **[TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md)** for complete technical details
2. Review **[API.md](API.md)** for programmatic API usage
3. Check **[CHANGELOG.md](CHANGELOG.md)** for version history
4. See **[STREAMING_IMPROVEMENTS.md](STREAMING_IMPROVEMENTS.md)** for streaming implementation details

## Key Features

### 🔍 Deep Research
- Multi-agent architecture with supervisor and researchers
- Parallel research execution
- Automatic web search and summarization

### 📊 Real-Time Streaming
- Live progress updates during research
- Streaming report generation
- No timeouts with reasoning models

### 🔭 Full Observability
- Langfuse integration for LLM tracing
- Track all API calls, costs, and performance
- Debug issues easily

### ⚙️ Highly Configurable
- Multiple LLM providers (DeepSeek, OpenAI, Anthropic, Ollama)
- Adjustable research depth and concurrency
- Customizable output format and language

## Quick Reference

### Environment Variables
```bash
# Required
API_KEY=your_llm_api_key
BASE_URL=https://api.deepseek.com
TAVILY_API_KEY=your_tavily_key

# Optional (for observability)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### Configuration File
Edit `src/fathom/config/config.toml`:
```toml
[research]
max_depth = 8              # Research iterations
concurrency = 4            # Parallel researchers

[llm]
timeout = 60              # Request timeout (seconds)
max_retries = 3           # Retry attempts
```

### Running Research
```bash
# Simple query
fathom "What is LangGraph?"

# From stdin
echo "Explain quantum computing" | fathom

# View logs
tail -f logs/fathom.log
```

## Common Issues

### API Retries
See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md#api-retries-and-rate-limiting)**

### Slow Performance
See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md#slow-report-generation)**

### Langfuse Not Working
See **[LANGFUSE_SETUP.md](LANGFUSE_SETUP.md#troubleshooting)**

## Contributing

When adding new documentation:
1. Place `.md` files in the `docs/` directory
2. Update this README with links
3. Follow the existing documentation style
4. Include code examples where relevant

## Support

- **Issues**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Logs**: `tail -f logs/fathom.log`
- **Configuration**: `cat src/fathom/config/config.toml`

## Recent Updates

- ✅ Added streaming to prevent timeouts with reasoning models
- ✅ Integrated Langfuse for full LLM observability
- ✅ Real-time progress indicators during research
- ✅ Comprehensive troubleshooting guide
- ✅ Organized documentation in `docs/` directory

---

**Happy Researching with Fathom! 🔍**
