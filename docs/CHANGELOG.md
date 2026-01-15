# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-15

### Added
- **Streaming Output**: Real-time streaming for compression and report generation phases
  - Users can now see progress as content is being generated
  - Implemented using `astream()` for better UX with long contexts
- **Researcher IDs**: Unique identifiers for parallel researchers
  - Format: `[R-xxxxxx]` where xxxxxx is a 6-character hash
  - Makes it easy to track individual researchers in logs
  - Topic summary (first 80 chars) displayed to avoid log clutter
- **Auto-save Reports**: Reports are automatically saved to markdown files
  - Smart filename generation from report title (H1 heading)
  - Three-tier fallback: report title → brief → timestamp
  - Example: `report_20260115_004607_US_Population_Growth_Analysis_2006-2026.md`
- **Enhanced Source Citations**: Full URL preservation and display
  - Search results formatted as markdown with clickable links
  - Inline citations throughout the report
  - Comprehensive Sources section with all URLs
  - Format: `[Title](URL)` for easy reference

### Fixed
- **Critical**: Tavily search tool not being called
  - Added missing `@tool` decorator to `tavily_search` function
  - Fixed docstring parameter mismatch (removed 'config', added 'max_char_to_include')
  - Search functionality now works as intended
- **Type Annotations**: Updated from `Callable` to `BaseTool`
  - Fixed type errors in `tools/utils.py`
  - Proper type checking for tool registry
- **Type Safety**: Fixed type issues in report generation
  - Handle `research_brief` potentially being `None`
  - Handle `final_report.content` being `str | list` type

### Changed
- **Prompts**: Strengthened requirements for source preservation
  - Compression prompt now explicitly requires preserving all URLs
  - Report generation prompt emphasizes inline citations and Sources section
  - Added warnings against generic source descriptions
- **Search Results**: Enhanced formatting for better citation
  - Added `formatted_output` field with markdown links
  - Each result includes title, URL, query, and summary
  - Results separated by horizontal rules for clarity

### Improved
- **Log Readability**: Parallel researchers now easily distinguishable
  - Each researcher has unique ID in all log messages
  - Topic summaries prevent overly long log lines
  - Clear visual separation between different researchers
- **Filename Generation**: More meaningful report filenames
  - Extracts actual report title instead of truncating brief
  - Reduced fallback length from 50 to 30 characters
  - Better handling of special characters

## [0.1.0] - 2026-01-14

### Added
- Initial release
- Multi-agent research system with LangGraph
- Clarification agent for ambiguous queries
- Supervisor agent for research planning
- Parallel researcher agents
- Report generation with markdown output
- Tavily search integration
- DeepSeek LLM integration
- Configuration system with TOML
- Logging system

### Features
- Parallel research execution
- Configurable research depth and concurrency
- Multiple LLM provider support (DeepSeek, OpenAI, Anthropic)
- Customizable prompts and system messages
- Tool-based architecture for extensibility

---

## Version History

- **0.2.0** (2026-01-15): Major improvements to search, logging, and report generation
- **0.1.0** (2026-01-14): Initial release with core functionality

## Upgrade Guide

### From 0.1.0 to 0.2.0

No breaking changes. All improvements are backward compatible.

**New Features to Try:**
1. Check logs for researcher IDs: `grep "\[R-" logs/fathom.log`
2. Find auto-saved reports in `./reports/` directory
3. Look for clickable source links in generated reports
4. Watch streaming output during compression and report generation

**Configuration Changes:**
No configuration changes required. All new features work with existing config.

**API Changes:**
None. All changes are internal improvements.

## Contributors

- Claude Sonnet 4.5 (AI Assistant)
- [Your name/team]

## Links

- Repository: [Add your repo URL]
- Issues: [Add your issues URL]
- Documentation: See README.md
