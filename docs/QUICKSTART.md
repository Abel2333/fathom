# Quick Setup Guide

Get your Fathom Deep Research Agent up and running in 5 minutes.

## Prerequisites

- Python 3.13 or higher
- `uv` package manager (recommended) or `pip`

## Step 1: Clone and Install

```bash
# Navigate to the project directory
cd fathom

# Install dependencies
uv sync
# or with pip:
# pip install -e .
```

## Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your credentials
nano .env  # or use your preferred editor
```

### Required Environment Variables

You need to set these in your `.env` file:

1. **LLM API Configuration** (Required)
   ```bash
   API_KEY=your_api_key_here
   BASE_URL=https://api.deepseek.com
   ```
   - Get DeepSeek API key at: https://platform.deepseek.com
   - Or use OpenAI, Anthropic, or any compatible API

2. **Search API Configuration** (Required)
   ```bash
   TAVILY_API_KEY=tvly-your_tavily_api_key_here
   ```
   - Get Tavily API key at: https://tavily.com
   - Free tier: 1000 searches/month

3. **Langfuse Observability** (Optional but Recommended)
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-your_public_key_here
   LANGFUSE_SECRET_KEY=sk-lf-your_secret_key_here
   ```
   - Get Langfuse keys at: https://cloud.langfuse.com
   - See [LANGFUSE_SETUP.md](LANGFUSE_SETUP.md) for detailed setup

## Step 3: Run Your First Research

```bash
# Run a simple research query
fathom "What is LangGraph?"

# Or pipe from stdin
echo "Explain quantum computing" | fathom
```

You should see real-time streaming output:

```
🔍 Starting Fathom Deep Research Agent
📝 Research Query: What is LangGraph?

🤔 Analyzing your request...

📋 Creating research plan...

🔬 Starting research phase...

📊 Research findings collected: 1

📝 Generating final report...

[Report streams in real-time...]

✅ Research completed!
```

## Step 4: View Your Report

Reports are automatically saved to the `./reports` directory with timestamps:

```bash
# View the latest report
ls -lt reports/ | head -5

# Read a report
cat reports/report_20260115_123456_What_is_LangGraph.md
```

## Step 5: Monitor with Langfuse (Optional)

If you configured Langfuse:

1. Visit https://cloud.langfuse.com
2. Go to your project
3. Click on **Traces** to see your research session
4. Explore:
   - All LLM calls and responses
   - Token usage and costs
   - Execution timeline
   - Performance metrics

## Configuration

### Customize Research Behavior

Edit `src/fathom/config/config.toml` to customize:

```toml
[research]
max_depth = 8              # Research depth (iterations)
max_sub_questions = 3      # Sub-questions per iteration
concurrency = 4            # Parallel researchers

[output]
dir = "./reports"          # Output directory
language = "Chinese"       # Output language
tone = "professional"      # Writing tone
```

### Enable/Disable Features

```toml
[research]
allow_clarification = true  # Ask clarifying questions

[langfuse]
enabled = true             # Enable LLM tracing
```

## Troubleshooting

### "No module named fathom"

```bash
# Make sure you installed the package
uv sync
# or
pip install -e .
```

### "API key not found"

```bash
# Check your .env file exists and has the correct keys
cat .env | grep API_KEY

# Make sure .env is in the project root
ls -la .env
```

### "Tavily API error"

```bash
# Verify your Tavily API key
cat .env | grep TAVILY_API_KEY

# Check you haven't exceeded the free tier limit
# Visit: https://app.tavily.com/usage
```

### Langfuse not working

```bash
# Check if Langfuse is enabled
grep "enabled" src/fathom/config/config.toml

# Verify environment variables
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY

# Check logs for Langfuse initialization
tail -f logs/fathom.log | grep -i langfuse
```

## Next Steps

1. **Read the documentation**:
   - [LANGFUSE_SETUP.md](LANGFUSE_SETUP.md) - Detailed Langfuse guide
   - [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

2. **Customize your agent**:
   - Modify prompts in `src/fathom/prompts.py`
   - Adjust models in `config.toml`
   - Add custom tools in `src/fathom/tools/`

3. **Monitor and optimize**:
   - Use Langfuse to track costs
   - Analyze which queries are expensive
   - Optimize prompts and models

## Getting Help

- Check logs: `tail -f logs/fathom.log`
- Review configuration: `cat src/fathom/config/config.toml`
- Read documentation in this repository

## Example Queries

Try these research queries:

```bash
# Technology
fathom "What are the latest developments in AI agents?"

# Science
fathom "Explain the current state of fusion energy research"

# Business
fathom "What are the key trends in SaaS pricing models?"

# Complex research
fathom "Compare the architectural approaches of LangGraph, CrewAI, and AutoGPT"
```

Enjoy researching with Fathom! 🔍
