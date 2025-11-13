# Prompt Structure

This document describes the structure and content of prompts sent to the LLM in the opencode system. The prompt is composed of multiple sections that provide context, instructions, and capabilities to the language model.

## Overview

The prompt sent to the LLM consists of:

1. **System Messages** (up to 2 messages for caching efficiency)
   - Header and provider-specific instructions
   - Agent-specific or model-specific behavior guidelines
   - Environment information
   - Custom instructions from project files

2. **Conversation History**
   - Previous user messages and assistant responses
   - Tool execution results
   - Reasoning traces (for models that support it)
   - File change patches

3. **Tool Definitions**
   - Built-in tools for file operations, code execution, and task management
   - MCP (Model Context Protocol) tools from external servers
   - LSP (Language Server Protocol) tools for code analysis
   - Custom tools from plugins and project configuration

4. **Contextual Information**
   - File contents (when referenced in user messages)
   - Directory listings (when directories are referenced)
   - LSP diagnostics (when available)
   - Project structure information

## System Prompt Sections

The system prompt is constructed from multiple sources, combined into a maximum of two system messages for efficient caching.

### 1. Header Section

**Purpose**: Provides provider-specific initialization and formatting instructions.

**Content**: 
- For Anthropic models: A spoof prompt that ensures proper formatting and behavior
- For other providers: Typically empty

**Meaning**: Sets up the initial context and ensures the model understands it's operating within the opencode system.

### 2. Provider/Agent Prompt Section

**Purpose**: Defines the core behavior, personality, and operational guidelines for the agent.

**Content**: The content depends on the model or agent configuration:

#### Model-Specific Prompts

- **GPT-5 models**: Codex prompt - Emphasizes precision, safety, and helpfulness. Focuses on concise communication, structured planning, and autonomous task completion.

- **GPT-4, GPT-3.5, O1, O3 models**: Beast prompt - Emphasizes autonomous problem-solving, extensive iteration, and thorough testing. Requires extensive internet research and recursive information gathering.

- **Gemini models**: Gemini-specific prompt with model-appropriate instructions.

- **Claude models**: Anthropic prompt - Emphasizes conciseness, directness, and professional objectivity. Includes detailed guidelines on:
  - Tone and style (concise, direct, minimal output tokens)
  - Proactiveness balance
  - Code style and conventions
  - Task management with TodoWrite tool
  - Tool usage policies
  - Code references with file paths

- **Default (other models)**: Anthropic-style prompt without todo management features.

#### Agent-Specific Prompts

If an agent has a custom `prompt` field configured, it overrides the model-specific prompt. This allows agents to have specialized behaviors and instructions tailored to their specific purpose.

**Key Themes Across Prompts**:

- **Autonomy**: Agents should work independently to solve problems completely before yielding
- **Conciseness**: Minimize output tokens while maintaining helpfulness
- **Planning**: Use todo/task management tools for complex multi-step work
- **Code Quality**: Follow existing conventions, test thoroughly, handle edge cases
- **Tool Usage**: Use tools efficiently, batch operations when possible
- **Communication**: Clear, direct, professional tone with appropriate detail level

### 3. Environment Information Section

**Purpose**: Provides context about the execution environment and project structure.

**Content**:
- Working directory path
- Git repository status (whether the directory is a git repo)
- Platform information (operating system)
- Current date
- Project tree structure (limited to 200 items for brevity)

**Format**:
```
<env>
  Working directory: /path/to/project
  Is directory a git repo: yes/no
  Platform: darwin/linux/windows
  Today's date: Mon Jan 01 2024
</env>
<project>
  [project tree structure]
</project>
```

**Meaning**: Helps the agent understand where it's operating, what tools are available, and the structure of the codebase it's working with.

### 4. Custom Instructions Section

**Purpose**: Includes project-specific and user-specific instructions from configuration files.

**Content Sources** (searched in order):

1. **Local Project Files** (searched from current directory upward):
   - `AGENTS.md`: Describes available agents and their capabilities
   - `CLAUDE.md`: Project-specific coding standards and conventions
   - `CONTEXT.md`: (deprecated) Additional context information

2. **Global Configuration Files**:
   - `~/.opencode/AGENTS.md`: Global agent definitions
   - `~/.claude/CLAUDE.md`: Global coding standards

3. **Config-Specified Files**: Files listed in `config.instructions` array

**Content Format**: Raw markdown/text content from these files is directly inserted into the system prompt.

**Meaning**: 
- **AGENTS.md**: Provides information about available subagents, when to use them, and their capabilities. This helps the primary agent decide when to delegate tasks to specialized agents.
- **CLAUDE.md**: Contains project-specific coding standards, patterns, testing requirements, and conventions that should be followed.
- **CONTEXT.md**: (Deprecated) Previously used for additional project context.

**Integration**: These files are read and their content is appended to the system prompt, allowing projects to customize agent behavior without code changes.

## Conversation History

The conversation history includes all previous messages in the session, converted to the format expected by the LLM provider.

### Message Types

#### User Messages

**Content**:
- Text parts: Direct user input
- File parts: References to files or directories
- Agent parts: References to subagents that should be invoked

**Processing**:
- File references are expanded to include file contents or directory listings
- Agent references trigger instructions to use the `task` tool
- All parts are stored and included in the conversation history

#### Assistant Messages

**Content**:
- Text parts: Agent's responses to the user
- Tool parts: Tool calls made by the agent, including:
  - Tool name and parameters
  - Execution status (pending, running, completed, error)
  - Tool output or error messages
  - Execution metadata
- Reasoning parts: Internal reasoning traces (for models that support it)
- Patch parts: File changes made during a reasoning step
- Step markers: Indicators of reasoning step boundaries

**Structure**: Each assistant message includes:
- Model information (provider, model ID)
- Token usage (input, output, reasoning, cache)
- Cost information
- Timestamps
- Error information (if any)

### Message Filtering

Messages are filtered before being sent to the LLM:
- Summarized messages are excluded (replaced by summaries)
- Aborted messages with no content are excluded
- Messages are converted to provider-specific format via `MessageV2.toModelMessage()`

### Session Compaction

When the conversation history exceeds the model's context limit:
- Previous messages are summarized using a smaller model
- The summary is stored as a new message
- A resume instruction is added
- The history is replaced with just the summary and resume message

This ensures the conversation can continue indefinitely while staying within context limits.

## Tool Definitions

Tools are functions the agent can call to interact with the system. Each tool definition includes:
- **ID**: Unique identifier for the tool
- **Description**: Human-readable description of what the tool does
- **Parameters Schema**: JSON schema defining the tool's input parameters
- **Execute Method**: The function that runs when the tool is called

### Built-in Tools

These are core tools provided by the opencode system:

#### File Operations

- **`read`**: Reads file contents from the filesystem
  - Can read any file on the machine
  - Supports line offset and limit for partial reads
  - Returns content in `cat -n` format with line numbers
  - Truncates lines longer than 2000 characters
  - Can read image files

- **`write`**: Creates a new file with specified content
  - Requires absolute file path
  - Overwrites existing files
  - Creates parent directories if needed

- **`edit`**: Performs exact string replacements in files
  - Requires reading the file first
  - Preserves exact indentation
  - Supports `replaceAll` for multiple replacements
  - Fails if match is ambiguous

- **`patch`**: Applies structured patches to files
  - More sophisticated than `edit` for complex changes
  - Supports multiple file edits in one operation

- **`list`** (or `ls`): Lists directory contents
  - Shows files and subdirectories
  - Includes file metadata (size, permissions, etc.)

#### Code Search and Analysis

- **`grep`**: Searches for text patterns across files
  - Supports regex patterns
  - Can search specific file types or directories
  - Returns matching lines with context

- **`glob`**: Finds files matching patterns
  - Supports glob patterns (e.g., `**/*.ts`)
  - Returns matching file paths

#### Execution Tools

- **`bash`**: Executes shell commands
  - Runs commands in the project directory
  - Supports timeout configuration
  - Requires permission approval for certain commands
  - Parses commands to check for dangerous operations
  - Returns command output and exit status

#### Task Management

- **`todowrite`**: Creates and manages structured task lists
  - Tracks progress through complex multi-step tasks
  - Supports task states: pending, in_progress, completed, cancelled
  - Helps demonstrate thoroughness and organization
  - Should be used for tasks with 3+ steps or non-trivial complexity

- **`todoread`**: Reads the current task list
  - Shows all tasks and their current status
  - Helps the agent understand what work remains

#### Agent Delegation

- **`task`**: Launches a subagent to handle complex tasks
  - Takes a `subagent_type` parameter to select which agent to use
  - Includes list of available subagents and their descriptions
  - Creates isolated session for subagent execution
  - Returns aggregated results from subagent
  - Should be used for tasks matching subagent descriptions
  - Should NOT be used for simple file reads or searches

#### Web Operations

- **`webfetch`**: Fetches content from URLs
  - Converts HTML to markdown
  - Includes 15-minute cache for repeated access
  - Supports HTTP to HTTPS upgrade
  - Can summarize very large content

### MCP Tools

**Purpose**: Tools provided by external Model Context Protocol (MCP) servers.

**Content**: 
- Tools are discovered from MCP servers configured in the project
- Each tool includes its own description and parameter schema
- Tool names are sanitized: `{clientName}_{toolName}` (spaces/hyphens become underscores)

**Meaning**: Allows integration with external services and tools beyond the built-in set. Examples might include:
- Database query tools
- API interaction tools
- Specialized analysis tools
- External service integrations

**Availability**: Only tools from configured and connected MCP servers are available.

### LSP Tools

**Purpose**: Tools that leverage Language Server Protocol for code analysis.

**Content**:

- **`lsp_diagnostics`**: Retrieves code diagnostics (errors, warnings, hints) for a file
  - Requires file path
  - Triggers LSP server to analyze the file
  - Returns formatted diagnostic messages
  - Includes diagnostic metadata (severity, range, message)

- **`lsp_hover`**: Gets hover information for symbols in code
  - Provides type information, documentation, and symbol details
  - Helps understand code context and API usage

**Meaning**: These tools provide semantic understanding of code beyond simple text analysis. They help the agent:
- Understand code structure and relationships
- Identify errors and warnings
- Get type information and documentation
- Navigate codebases more effectively

**Usage**: Agents can call these tools when they need deeper code analysis, but they're not automatically invoked.

### Custom Tools

**Purpose**: Tools defined by plugins or project-specific code.

**Content**: 
- Tools can be defined in project `tool/*.{js,ts}` files
- Plugins can register custom tools
- Each tool follows the same structure as built-in tools (ID, description, parameters, execute)

**Meaning**: Allows projects to extend agent capabilities with domain-specific tools. Examples:
- Project-specific build tools
- Custom analysis tools
- Integration with project-specific services
- Specialized file format handlers

### Tool Filtering

Not all available tools are always enabled:

- **Agent Configuration**: Agents can enable/disable specific tools via `agent.tools` configuration
- **Wildcard Matching**: Tools can be enabled/disabled using patterns (e.g., `lsp_*` to enable all LSP tools)
- **Permission-Based**: Some tools require permissions that may not be granted
- **Input Override**: The `tools` parameter in prompt input can override agent defaults

**Meaning**: This allows fine-grained control over agent capabilities, ensuring agents only have access to tools appropriate for their role and the current context.

## Contextual Information

Additional information is included in prompts when relevant:

### File Contents

**When Included**: When user messages reference files via `file://` URLs or `@filename` syntax.

**Content**:
- For text files: File contents are read and included as synthetic text parts
- For directories: Directory listings are generated and included
- For files with line ranges: Only the specified lines are included (with LSP symbol resolution for accuracy)

**Format**: 
- File contents are prefixed with a synthetic message: "Called the Read tool with the following input: {...}"
- Actual file content follows
- Original file reference is preserved

**Meaning**: Provides immediate context about files the user is asking about, reducing the need for the agent to make separate read calls.

### LSP Diagnostics

**When Included**: When LSP tools are called or when files are analyzed.

**Content**: 
- Diagnostic messages (errors, warnings, hints)
- File paths and line numbers
- Diagnostic severity and messages
- Code ranges affected

**Format**: Formatted diagnostic messages, typically one per line with file path and line number.

**Meaning**: Helps the agent understand code quality issues, type errors, and potential problems before making changes.

### Project Structure

**When Included**: Always included in environment information section.

**Content**: 
- Directory tree structure (limited to 200 items)
- Shows file and directory hierarchy
- Helps understand project organization

**Meaning**: Provides high-level context about project layout, making it easier to navigate and understand the codebase structure.

## Prompt Assembly

The final prompt sent to the LLM is assembled as follows:

1. **System Messages** (up to 2):
   - First message: Header + Provider/Agent prompt
   - Second message: Environment + Custom instructions

2. **Conversation History**:
   - All previous messages converted to provider format
   - Filtered to exclude summarized/aborted messages
   - Includes tool results and reasoning traces

3. **Tool Definitions**:
   - All enabled tools with their descriptions and parameter schemas
   - Transformed to provider-specific format

4. **Current User Message**:
   - Processed file references expanded to content
   - Agent references converted to task tool instructions
   - All parts included in the message

## Provider-Specific Transformations

Different LLM providers require different prompt formats:

- **Message Format**: Converted via `MessageV2.toModelMessage()`
- **Tool Schema**: Transformed via `ProviderTransform.schema()` for compatibility
- **Caching**: System messages optimized for provider-specific caching mechanisms
- **Options**: Provider-specific options merged into requests

**Meaning**: These transformations ensure the prompt works correctly with different LLM providers while maintaining semantic consistency.

## Special Instructions and Reminders

### Synthetic Messages

Some messages are marked as "synthetic" - they're generated by the system rather than the user:

- File read confirmations
- Directory listing confirmations
- Agent invocation instructions
- Resume instructions after compaction

**Meaning**: These help the agent understand what actions were taken automatically and provide context for tool results.

### System Reminders

Tool results and user messages may include `<system-reminder>` tags with useful information and reminders. These are NOT part of the user's input or tool result, but provide additional context.

**Meaning**: Allows the system to provide hints and reminders without cluttering the conversation history.

### Reminder Insertion

Special reminders are inserted into user messages in certain scenarios:

- **Plan Agent**: When using the "plan" agent, a planning reminder is added
- **Build Agent After Plan**: When switching from "plan" to "build" agent, a build switch reminder is added

**Meaning**: These reminders guide the agent's behavior for specific workflows and agent transitions.

## Summary

The prompt structure is designed to provide comprehensive context to the LLM while maintaining efficiency:

- **System prompts** establish behavior and capabilities
- **Conversation history** provides continuity and context
- **Tool definitions** enable interaction with the system
- **Contextual information** fills in details about files and code
- **Provider transformations** ensure compatibility across different LLM providers

This structure allows the agent to understand the task, access necessary information, perform actions, and maintain context throughout extended conversations.

