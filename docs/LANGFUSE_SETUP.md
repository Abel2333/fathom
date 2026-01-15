# Langfuse Integration Guide

This guide explains how to set up and use Langfuse tracing in your Fathom Deep Research Agent.

## What is Langfuse?

Langfuse is an open-source LLM observability and analytics platform that helps you:
- **Trace LLM calls**: See every LLM request, response, and token usage
- **Monitor performance**: Track latency, costs, and quality metrics
- **Debug issues**: Inspect the full execution flow of your agent
- **Analyze usage**: Understand how your models are being used

## Setup Instructions

### 1. Install Langfuse

The langfuse package is already included in the project dependencies. Install it with:

```bash
uv sync
# or
pip install langfuse
```

### 2. Get Langfuse Credentials

You have two options:

#### Option A: Use Langfuse Cloud (Recommended for getting started)

1. Sign up at [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a new project
3. Go to Settings → API Keys
4. Copy your **Public Key** and **Secret Key**

#### Option B: Self-host Langfuse

Follow the [self-hosting guide](https://langfuse.com/docs/deployment/self-host) to deploy your own Langfuse instance.

### 3. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Langfuse credentials
nano .env  # or use your preferred editor
```

Add your Langfuse credentials to `.env`:

```bash
# Langfuse Configuration
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com"  # Optional, defaults to cloud.langfuse.com
```

**Important**: Never commit your `.env` file to version control! It's already in `.gitignore`.

### 4. Enable Langfuse in Config

The Langfuse integration is already enabled in `src/fathom/config/config.toml`:

```toml
[langfuse]
enabled = true  # Set to false to disable tracing
```

To disable tracing, simply set `enabled = false` in the config file.

## What Gets Traced?

With Langfuse enabled, the following will be automatically traced:

### 1. **All LLM Calls**
- Clarification phase (analyzing user requests)
- Research brief generation
- Supervisor planning and decision-making
- Researcher searches and thinking
- Content summarization
- Final report generation

### 2. **Token Usage & Costs**
- Input and output tokens for each call
- Estimated costs (if pricing data is available)

### 3. **Execution Flow**
- Complete workflow from start to finish
- Nested subgraph executions (supervisor → researchers)
- Tool calls and their results

### 4. **Performance Metrics**
- Latency for each LLM call
- Total execution time
- Parallel vs sequential execution

## Using the Langfuse Dashboard

After running your research agent, visit your Langfuse dashboard to:

### View Traces

1. Go to **Traces** in the sidebar
2. Click on a trace to see the full execution flow
3. Expand nodes to see:
   - Input prompts
   - Model responses
   - Token counts
   - Latency

### Analyze Performance

1. Go to **Analytics** to see:
   - Total requests over time
   - Average latency trends
   - Token usage and costs
   - Error rates

### Debug Issues

1. Filter traces by status (success/error)
2. Search for specific queries or errors
3. Inspect the full conversation history
4. See exactly where failures occurred

## Example: Running with Langfuse

```bash
# Set environment variables
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."

# Run your research agent
fathom "What is LangGraph?"

# Check the Langfuse dashboard to see the trace
```

## Trace Structure

Here's what a typical Fathom trace looks like in Langfuse:

```
📊 Fathom Research Session
├── 🤔 Clarification Phase
│   └── LLM Call: deepseek-chat (analyze request)
├── 📋 Research Brief Generation
│   └── LLM Call: deepseek-chat (create brief)
├── 🔬 Research Supervisor
│   ├── LLM Call: kimi-k2-thinking (plan research)
│   ├── 👤 Researcher #1
│   │   ├── LLM Call: kimi-k2-thinking (research)
│   │   ├── Tool: tavily_search
│   │   └── LLM Call: deepseek-chat (summarize)
│   └── 👤 Researcher #2
│       ├── LLM Call: kimi-k2-thinking (research)
│       ├── Tool: tavily_search
│       └── LLM Call: deepseek-chat (summarize)
└── 📝 Final Report Generation
    └── LLM Call: kimi-k2-thinking (write report)
```

## Troubleshooting

### Traces Not Appearing

1. **Check environment variables**: Ensure `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set
2. **Check config**: Verify `enabled = true` in `config.toml`
3. **Check logs**: Look for "Langfuse tracing initialized successfully" in the logs
4. **Network issues**: Ensure you can reach the Langfuse host

### Common Warnings

**"Langfuse is enabled but environment variables are not set"**
- Solution: Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` environment variables

**"Langfuse package is not installed"**
- Solution: Run `uv sync` or `pip install langfuse`

**"Failed to initialize Langfuse"**
- Check your API keys are correct
- Verify network connectivity to Langfuse host
- Check logs for detailed error messages

## Disabling Langfuse

To disable Langfuse tracing:

1. Set `enabled = false` in `src/fathom/config/config.toml`, or
2. Unset the environment variables:
   ```bash
   unset LANGFUSE_PUBLIC_KEY
   unset LANGFUSE_SECRET_KEY
   ```

The agent will continue to work normally without tracing.

## Best Practices

1. **Use descriptive session names**: The trace will use your research query as the session name
2. **Tag traces**: Consider adding custom tags for different research types
3. **Monitor costs**: Regularly check the analytics dashboard to track token usage
4. **Review errors**: Set up alerts for failed traces
5. **Privacy**: Be mindful of sensitive data in prompts - Langfuse stores all inputs/outputs

## Advanced: Custom Tracing

If you want to add custom spans or metadata to your traces, you can access the Langfuse handler:

```python
from fathom.tools.search import get_langfuse_handler

handler = get_langfuse_handler()
if handler:
    # Add custom metadata
    handler.trace(
        name="custom_operation",
        metadata={"custom_key": "custom_value"}
    )
```

## Resources

- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Integration](https://langfuse.com/docs/integrations/langchain)
- [Langfuse GitHub](https://github.com/langfuse/langfuse)
- [Community Discord](https://discord.gg/7NXusRtqYU)

## Support

If you encounter issues with Langfuse integration:
1. Check the [Langfuse documentation](https://langfuse.com/docs)
2. Review the logs in `logs/fathom.log`
3. Open an issue on the Fathom GitHub repository
