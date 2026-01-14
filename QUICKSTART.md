# Quick Start Guide

Get Fathom up and running in 5 minutes.

## Prerequisites

- Python 3.13 or higher
- API keys for:
  - DeepSeek (or OpenAI/Anthropic)
  - Tavily Search

## Installation Steps

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd fathom

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

Add your keys:
```env
API_KEY=sk-your-deepseek-key
BASE_URL=https://api.deepseek.com/v1
TAVILY_API_KEY=tvly-your-tavily-key
```

### 3. Run Your First Research

```bash
# Start Fathom
fathom

# Or run directly
python -m fathom.cli
```

Example query:
```
You: Analyze the impact of AI on software development in 2024-2025
```

### 4. Check Your Report

Reports are automatically saved to `./reports/`:
```bash
ls -lt reports/
# Shows: report_20260115_120530_AI_Impact_on_Software_Development.md
```

## Configuration (Optional)

Edit `src/fathom/config/config.toml` to customize:

```toml
[research]
concurrency = 4        # Number of parallel researchers
max_depth = 6          # Research iterations

[output]
language = "English"   # or "Chinese"
tone = "professional"  # or "academic", "easy-to-read"
```

## Verify Installation

Check that everything works:

```bash
# Check logs for successful initialization
tail -f logs/fathom.log

# Look for these messages:
# - "SUPERVISOR ITERATION #1: Starting"
# - "[R-xxxxxx] RESEARCHER LOOP: Starting"
# - "Tavily search invoked with X querie(s)"
# - "Report saved to: ./reports/..."
```

## Common Issues

### "No module named 'fathom'"
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Reinstall in editable mode
pip install -e .
```

### "Tavily search not working"
```bash
# Check your API key
cat .env | grep TAVILY

# Test the key
python -c "from tavily import TavilyClient; print(TavilyClient(api_key='your-key').search('test'))"
```

### "Reports not saving"
```bash
# Create reports directory
mkdir -p reports

# Check permissions
ls -ld reports/
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CHANGELOG.md](CHANGELOG.md) for recent updates
- Explore `src/fathom/config/config.toml` for advanced configuration
- Review `src/fathom/agents/README.md` for architecture details

## Example Queries

Try these to test different features:

**Simple fact-finding:**
```
Compare Python vs JavaScript for web development
```

**Complex analysis:**
```
Analyze the economic impact of renewable energy adoption in Europe from 2020-2025
```

**Multi-aspect research:**
```
Research the causes, effects, and solutions for urban air pollution in major cities
```

## Getting Help

- Check logs: `tail -f logs/fathom.log`
- Enable debug mode: Set `level = "DEBUG"` in config.toml
- Review architecture: `src/fathom/agents/README.md`

## Performance Tips

For faster results:
```toml
[research]
concurrency = 8      # More parallel researchers
max_depth = 3        # Fewer iterations

[llm]
summary_model_name = "deepseek-chat"  # Faster model
```

---

**Ready to research!** 🚀

For more details, see the [full documentation](README.md).
