# Troubleshooting Guide

Common issues and solutions for the Fathom Deep Research Agent.

## API Retries and Rate Limiting

### Symptom
You see repeated retry messages in the logs:
```
openai._base_client - INFO - Retrying request to /chat/completions in 0.447108 seconds
```

### Cause
This is **normal behavior** when your LLM API provider is rate limiting requests or experiencing temporary issues. The OpenAI client (which DeepSeek/Kimi clients are based on) has built-in retry logic with exponential backoff.

### Common Reasons:
1. **Rate Limiting**: You're hitting your API provider's rate limits
   - Too many requests per minute
   - Too many concurrent requests
   - Token usage limits

2. **API Server Load**: The provider's servers are temporarily overloaded

3. **Network Issues**: Temporary network connectivity problems

### Solutions:

#### 1. Reduce Concurrency
Edit `src/fathom/config/config.toml`:
```toml
[research]
concurrency = 2  # Reduce from 4 to 2 (fewer parallel researchers)
```

#### 2. Increase Timeout
```toml
[llm]
timeout = 120  # Increase from 60 to 120 seconds
max_retries = 5  # Increase retry attempts
```

#### 3. Check Your API Limits
- **DeepSeek**: Visit https://platform.deepseek.com/usage
- **Kimi**: Check your account dashboard
- Upgrade to a higher tier if needed

#### 4. Add Delays Between Requests
If you're consistently hitting rate limits, consider:
- Reducing `max_depth` (fewer research iterations)
- Reducing `max_sub_questions` (fewer parallel searches)

### When to Worry:
- ✅ **Normal**: 2-3 retries that eventually succeed
- ⚠️ **Concerning**: 5+ retries in a row
- ❌ **Problem**: Requests failing after all retries

---

## Langfuse Warnings

### Symptom 1: "No Langfuse client has been initialized"
```
langfuse - WARNING - No Langfuse client with public key ... has been initialized
```

### Solution:
This warning should no longer appear with the latest code. If you still see it:
1. Make sure you're using the latest version of the code
2. Check that environment variables are set correctly:
   ```bash
   echo $LANGFUSE_PUBLIC_KEY
   echo $LANGFUSE_SECRET_KEY
   ```

### Symptom 2: "Failed to flush Langfuse traces"
```
cli - WARNING - Failed to flush Langfuse traces: 'LangchainCallbackHandler' object has no attribute 'flush'
```

### Solution:
This has been fixed in the latest code. The flush now uses the Langfuse client's `flush()` method instead of the callback handler's.

---

## Slow Report Generation

### Symptom
Report generation takes 5-10 minutes:
```
11:01:39 - FINAL REPORT: starting generation
11:11:16 - Final report generation succeeded
```

### Cause
The report generation model (kimi-k2-thinking) is a reasoning model that:
- Thinks through the response before generating
- Generates very long, detailed reports
- May be rate-limited or queued

### Solutions:

#### 1. Use a Faster Model for Reports
Edit `config.toml`:
```toml
[llm]
report_model_name = "deepseek-chat"  # Faster, less detailed
# or
report_model_name = "gpt-4o"  # If using OpenAI
```

#### 2. Reduce Research Depth
```toml
[research]
max_depth = 4  # Reduce from 8 (less research = faster reports)
```

#### 3. Accept the Wait
Reasoning models like kimi-k2-thinking are designed to be thorough. The wait time is normal for high-quality, detailed reports.

---

## Memory Issues

### Symptom
```
MemoryError: Unable to allocate array
```

### Solutions:

#### 1. Reduce Context Size
```toml
[scraping]
summary_max_chars = 2000  # Reduce from 4000
```

#### 2. Limit Research Scope
```toml
[research]
max_depth = 4
max_sub_questions = 2
```

#### 3. Clear Old Reports
```bash
# Archive old reports
mkdir -p reports/archive
mv reports/report_*.md reports/archive/
```

---

## Network Errors

### Symptom
```
httpx.ConnectError: Connection refused
httpx.TimeoutException: Request timed out
```

### Solutions:

#### 1. Check API Endpoint
Verify your `BASE_URL` in `.env`:
```bash
# For DeepSeek
BASE_URL=https://api.deepseek.com

# For custom proxy
BASE_URL=http://your-proxy-url.com/v1
```

#### 2. Test Connectivity
```bash
curl -I $BASE_URL
```

#### 3. Check Firewall/Proxy
- Ensure your firewall allows outbound HTTPS
- Configure proxy if needed

---

## Tavily Search Errors

### Symptom
```
TavilyError: API key invalid
TavilyError: Rate limit exceeded
```

### Solutions:

#### 1. Verify API Key
```bash
cat .env | grep TAVILY_API_KEY
```

#### 2. Check Usage Limits
Visit: https://app.tavily.com/usage

Free tier: 1000 searches/month

#### 3. Reduce Search Frequency
```toml
[search]
max_results = 3  # Reduce from 5
```

---

## Debug Mode

### Enable Detailed Logging

Edit `config.toml`:
```toml
[logging]
level = "DEBUG"  # Change from INFO
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
fathom "your query"
```

### View Logs in Real-Time
```bash
tail -f logs/fathom.log
```

### Filter Specific Components
```bash
# Only show researcher logs
tail -f logs/fathom.log | grep researcher

# Only show API errors
tail -f logs/fathom.log | grep -i error

# Only show Langfuse
tail -f logs/fathom.log | grep -i langfuse
```

---

## Performance Optimization

### For Faster Research:

```toml
[llm]
report_model_name = "deepseek-chat"  # Faster model
summary_model_name = "deepseek-chat"
research_model_name = "deepseek-chat"

[research]
max_depth = 4  # Fewer iterations
max_sub_questions = 2  # Fewer parallel searches
concurrency = 2  # Less parallelism

[search]
max_results = 3  # Fewer search results
```

### For Better Quality (Slower):

```toml
[llm]
report_model_name = "kimi-k2-thinking"  # Reasoning model
research_model_name = "kimi-k2-thinking"

[research]
max_depth = 8  # More iterations
max_sub_questions = 3  # More parallel searches
concurrency = 4  # More parallelism

[search]
max_results = 5  # More search results
```

---

## Getting Help

If you're still experiencing issues:

1. **Check the logs**: `cat logs/fathom.log | tail -100`
2. **Verify configuration**: `cat src/fathom/config/config.toml`
3. **Test environment variables**: `env | grep -E "(API_KEY|TAVILY|LANGFUSE)"`
4. **Check API status**: Visit your provider's status page
5. **Open an issue**: Include logs and configuration (redact API keys!)

---

## Quick Diagnostics

Run this diagnostic script:

```bash
#!/bin/bash
echo "=== Fathom Diagnostics ==="
echo ""
echo "Environment Variables:"
echo "API_KEY: ${API_KEY:0:10}..."
echo "BASE_URL: $BASE_URL"
echo "TAVILY_API_KEY: ${TAVILY_API_KEY:0:10}..."
echo "LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY:0:15}..."
echo ""
echo "Config File:"
grep -E "(model_name|max_depth|concurrency|timeout)" src/fathom/config/config.toml
echo ""
echo "Recent Errors:"
tail -20 logs/fathom.log | grep -i error
echo ""
echo "API Connectivity:"
curl -I $BASE_URL 2>&1 | head -5
```

Save as `diagnose.sh`, make executable (`chmod +x diagnose.sh`), and run (`./diagnose.sh`).
