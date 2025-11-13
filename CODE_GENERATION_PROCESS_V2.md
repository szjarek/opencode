# Code Generation Process

## Overview

This document describes the end-to-end workflow from user prompt to generated code implementation in the opencode system. The process is orchestrated through the `SessionPrompt` namespace, which coordinates session management, agent selection, tool resolution, LLM interaction, and response processing.

## High-Level Flow

1. **User Input**: User provides a message via CLI (`cli/cmd/run.ts`) or programmatic API
2. **Session Creation/Retrieval**: Session is created or retrieved via `Session.create()` or `Session.get()`
3. **Message Creation**: User message is created via `SessionPrompt.createUserMessage()` which processes file URLs, agent references, and text parts
4. **Agent & Model Resolution**: Agent and model are selected based on input, configuration, or defaults
5. **System Prompt Construction**: System prompt is built via `SessionPrompt.resolveSystemPrompt()`
6. **Tool Resolution**: Available tools are resolved via `SessionPrompt.resolveTools()` from ToolRegistry and MCP
7. **LLM Interaction**: Prompt is sent to LLM via `streamText()` from the `ai` library
8. **Response Processing**: Stream is processed via `SessionPrompt.createProcessor()` which handles tool calls, text, and reasoning
9. **Iterative Execution**: Process continues in a loop until `finishReason` is not "tool-calls"
10. **Result Storage**: All parts (text, tool calls, reasoning) are stored via `Session.updatePart()`

## Detailed Component Flow

### 1. Prompt Construction

The LLM prompt is constructed in `SessionPrompt.prompt()` (packages/opencode/src/session/prompt.ts) through several steps:

#### 1.1 User Message Creation (`createUserMessage`)

When a user message is created, the system processes different part types:

- **Text Parts**: Directly included in the message
- **File Parts**: 
  - For `file://` URLs with `text/plain` mime type:
    - If URL has `?start=X&end=Y` query parameters, LSP is used to resolve symbol ranges via `LSP.documentSymbol()`
    - File content is read via `ReadTool.execute()` and included as synthetic text parts
  - For `file://` URLs with `application/x-directory` mime type:
    - Directory is listed via `ListTool.execute()` and included as synthetic text parts
  - For `data:` URLs: Base64-decoded content is included
- **Agent Parts**: When an agent reference is included, a synthetic text part is added instructing the LLM to use the `task` tool with the specified subagent

All parts are stored via `Session.updateMessage()` and `Session.updatePart()`.

#### 1.2 Message History Retrieval (`getMessages`)

Conversation history is retrieved via `Session.messages()` and filtered through `MessageV2.filterSummarized()`. 

**Session Compaction**: If the last assistant message's token count exceeds the model's context limit (checked via `SessionCompaction.isOverflow()`), the system:
1. Calls `SessionCompaction.run()` to generate a summary of previous messages
2. Creates a synthetic user message instructing the LLM to resume from the summary
3. Replaces the message history with just the summary and resume message

This ensures the conversation stays within context limits while preserving important information.

#### 1.3 System Prompt Resolution (`resolveSystemPrompt`)

The system prompt is constructed by combining multiple sources in this order:

1. **Header** (`SystemPrompt.header()`): Provider-specific headers (e.g., Anthropic spoof prompt)
2. **Provider/Agent Prompt**:
   - If `input.system` is provided, it's used directly
   - Otherwise, if `agent.prompt` exists, it's used
   - Otherwise, provider-specific prompts are selected via `SystemPrompt.provider(modelID)`:
     - `gpt-5`: PROMPT_CODEX
     - `gpt-*`, `o1`, `o3`: PROMPT_BEAST
     - `gemini-*`: PROMPT_GEMINI
     - `claude`: PROMPT_ANTHROPIC
     - Default: PROMPT_ANTHROPIC_WITHOUT_TODO
3. **Environment** (`SystemPrompt.environment()`): Includes working directory, git status, platform, date, and project tree structure
4. **Custom** (`SystemPrompt.custom()`): Searches for and includes:
   - Local files: `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md` (deprecated) via `Filesystem.findUp()`
   - Global files: `~/.opencode/AGENTS.md`, `~/.claude/CLAUDE.md`
   - Config-specified files from `config.instructions` array

The final system prompt is combined into a maximum of two system message entries for caching efficiency.

#### 1.4 Tool Resolution (`resolveTools`)

Tools are resolved from multiple sources:

1. **Built-in Tools** (`ToolRegistry.tools()`):
   - Loads all tools from `packages/opencode/src/tool/*.ts`
   - Includes: `edit`, `read`, `write`, `bash`, `glob`, `grep`, `list`, `patch`, `task`, `todo`, `webfetch`
   - Custom tools from project `tool/*.{js,ts}` files
   - Plugin tools from registered plugins

2. **MCP Tools** (`MCP.tools()`):
   - Connects to MCP servers defined in config
   - Exposes tools with sanitized names: `{clientName}_{toolName}` (spaces/hyphens replaced with underscores)
   - Tools are wrapped to integrate with plugin hooks and output formatting

3. **Tool Filtering**:
   - Tools are filtered based on `agent.tools` configuration (default: all enabled)
   - `ToolRegistry.enabled()` applies agent-specific tool permissions
   - Input `tools` parameter can override tool availability
   - Wildcard matching via `Wildcard.all()` is used for pattern-based enabling/disabling

4. **Tool Schema Transformation**:
   - Tool parameter schemas are transformed via `ProviderTransform.schema()` for provider-specific compatibility
   - Tools are wrapped with `tool()` from the `ai` library
   - Each tool's `execute` method is wrapped to:
     - Trigger `Plugin.trigger("tool.execute.before")` hook
     - Execute the tool with proper context (sessionID, messageID, callID, agent, abort signal)
     - Trigger `Plugin.trigger("tool.execute.after")` hook
     - Format output for the LLM

### 2. LLM Interaction

The prompt is sent to the LLM through the `Provider` system using `streamText()` from the `ai` library.

#### 2.1 Model Resolution (`resolveModel`)

Model selection follows this priority:
1. Explicit `input.model` parameter
2. `agent.model` from agent configuration
3. `Provider.defaultModel()` from config

The model is retrieved via `Provider.getModel(providerID, modelID)` which:
- Loads provider SDK (e.g., `@ai-sdk/anthropic`, `@ai-sdk/openai`)
- Gets model info from `ModelsDev` registry
- Creates language model instance
- Applies provider-specific transformations

#### 2.2 Parameter Resolution

LLM parameters are resolved via `Plugin.trigger("chat.params")` hook with defaults:
- `temperature`: From `agent.temperature` or `ProviderTransform.temperature()`
- `topP`: From `agent.topP` or `ProviderTransform.topP()`
- `options`: Merged from `ProviderTransform.options()`, `model.info.options`, and `agent.options`
- `maxOutputTokens`: Calculated via `ProviderTransform.maxOutputTokens()` with `OUTPUT_TOKEN_MAX` (32,000) limit

#### 2.3 Stream Configuration

The `streamText()` call is configured with:
- `messages`: System messages + conversation history converted via `MessageV2.toModelMessage()`
- `tools`: All enabled tools (or `undefined` if `model.info.tool_call === false`)
- `activeTools`: List of tool IDs (excluding "invalid")
- `maxRetries`: 10
- `stopWhen`: `stepCountIs(1)` - stops after one reasoning step
- `experimental_repairToolCall`: Repairs tool calls with incorrect casing or invalid tools
- `abortSignal`: From session lock for cancellation
- `providerOptions`: Provider-specific options merged into the request

### 3. Response Processing

LLM responses are processed via `SessionPrompt.createProcessor().process()` which handles the stream.

#### 3.1 Stream Processing

The processor handles these stream events:

- **`start`**: Initialization
- **`reasoning-start/delta/end`**: Reasoning tokens (for models that support it)
- **`tool-input-start/delta/end`**: Tool call input being generated
- **`tool-call`**: Complete tool call with parameters
- **`tool-result`**: Tool execution result
- **`tool-error`**: Tool execution error (may be `Permission.RejectedError`)
- **`text-start/delta/end`**: Text response chunks
- **`start-step`**: Beginning of a reasoning step (triggers snapshot tracking)
- **`finish-step`**: End of reasoning step (calculates usage, generates patch if files changed)
- **`finish`**: Stream completion
- **`error`**: Stream error

#### 3.2 Tool Execution Flow

When a `tool-call` event is received:

1. **Tool Part Creation**: A `MessageV2.ToolPart` is created with status "pending"
2. **Tool Execution**: The tool's `execute` method is called with:
   - Tool arguments (validated via Zod schema)
   - Context: `{ sessionID, messageID, callID, agent, abort, extra, metadata }`
3. **Permission Check**: Before execution, `Permission.ask()` is called (if required by tool):
   - Checks if permission is already approved for the session
   - If not, triggers `Plugin.trigger("permission.ask")` hook
   - If denied, throws `Permission.RejectedError`
4. **Execution**: Tool executes and returns `{ title, metadata, output, attachments? }`
5. **Result Storage**: Tool part is updated with status "completed" and result
6. **Error Handling**: If execution fails:
   - Tool part is updated with status "error"
   - If `Permission.RejectedError`, `blocked` flag is set
   - Error is stored in tool part

#### 3.3 Snapshot & Patch Generation

When `start-step` is received:
- `Snapshot.track()` is called to capture current file system state

When `finish-step` is received:
- `Snapshot.patch(snapshot)` is called to generate a diff
- If files changed, a `MessageV2.PatchPart` is created with the file list and hash

#### 3.4 Usage Tracking

Token usage is calculated via `Session.getUsage()` which:
- Extracts usage from LLM response metadata
- Calculates cost based on model pricing
- Tracks input, output, reasoning, and cache tokens
- Updates message with cumulative usage

### 4. Iterative Execution Loop

The main execution loop in `SessionPrompt.prompt()` continues until:

1. **Tool Calls Complete**: `finishReason !== "tool-calls"` (i.e., LLM finished with text or stop)
2. **No Blocking Errors**: `!result.blocked` (permission errors don't block, but are logged)
3. **No Errors**: `!result.info.error`
4. **No Queued Messages**: All queued messages for the session have been processed

If `finishReason === "tool-calls"`, the loop continues with:
- Updated message history (including tool results)
- Same system prompt
- Same tools
- New LLM request

This allows the agent to make multiple tool calls in sequence to complete a task.

### 5. Session Management

#### 5.1 Session Locking

Sessions are locked via `SessionLock.acquire()` during prompt processing to prevent concurrent modifications. The lock:
- Creates an `AbortController` for cancellation
- Prevents multiple simultaneous prompts for the same session
- Queues additional prompts until the current one completes
- Releases lock and publishes `SessionPrompt.Event.Idle` when done

#### 5.2 Message Storage

All messages and parts are stored via:
- `Session.updateMessage()`: Stores message metadata (role, model, tokens, cost, time)
- `Session.updatePart()`: Stores message parts (text, tool, reasoning, patch)
- Parts are stored incrementally as the stream processes (for real-time updates)

#### 5.3 Session Compaction

When context overflows (checked before each LLM request):
1. `SessionCompaction.run()` is called with current session and model
2. A summary prompt is constructed via `SystemPrompt.summarize()`
3. Previous messages are sent to a small model for summarization
4. Summary is stored as a new message
5. Message history is replaced with summary + resume instruction

### 6. Agent Selection and Subagent Execution

#### 6.1 Agent Resolution

Agent selection follows this priority:
1. Explicit `input.agent` parameter
2. Command's `command.agent` configuration
3. Default "build" agent
4. First available agent from `Agent.list()`

#### 6.2 Agent Configuration

Agents are configured via `Agent.Info` schema:
- `name`: Agent identifier
- `mode`: "primary" (default), "subagent" (only via task tool), or "all" (both)
- `model`: Optional model override
- `prompt`: Optional system prompt override
- `tools`: Tool enable/disable configuration
- `permission`: Permission settings for edit, bash, webfetch
- `temperature`, `topP`: Model parameter overrides
- `options`: Additional provider options

#### 6.3 Command-Based Subagent Execution

When `SessionPrompt.command()` is called (for CLI commands):

1. **Command Resolution**: Command is retrieved via `Command.get(name)`
2. **Template Processing**: 
   - `$ARGUMENTS` is replaced with user arguments
   - Shell commands in backticks (`!`...``) are executed and results inserted
   - File references (`@filename`) are resolved:
     - If file exists: Added as file part
     - If directory: Added as directory part
     - If agent name matches: Added as agent part
3. **Subtask Check**: If `command.subtask === true` OR (`agent.mode === "subagent"` AND `command.subtask !== false`):
   - Creates user and assistant messages
   - Creates a `task` tool part
   - Calls `TaskTool.execute()` directly (bypassing LLM)
   - Returns the tool result
4. **Otherwise**: Normal prompt flow with command template as user message

#### 6.4 Task Tool Execution

When the `task` tool is called (by LLM or command):

1. **Agent Validation**: Verifies `subagent_type` is a valid agent with `mode !== "primary"`
2. **Session Creation**: Creates a child session via `Session.create({ parentID })`
3. **Message Creation**: Creates a user message in the child session with the task prompt
4. **Tool Configuration**: Disables `todowrite`, `todoread`, and `task` tools for subagent (prevents recursion)
5. **Prompt Execution**: Calls `SessionPrompt.prompt()` with subagent configuration
6. **Result Aggregation**: Subscribes to `MessageV2.Event.PartUpdated` to track subagent progress
7. **Result Return**: Returns aggregated results from subagent session

Subagents operate in isolated sessions with their own context, tool permissions, and model configuration.

### 7. LSP Integration

LSP (Language Server Protocol) integration provides code analysis and context.

#### 7.1 LSP Client Management

LSP clients are managed via `LSP` namespace:
- Servers are configured in `LSPServer` with file extensions, root detection, and spawn commands
- Clients are created on-demand via `LSP.getClients(file)` when a file is accessed
- Multiple LSP servers can be active simultaneously (e.g., TypeScript, Rust, Go)

#### 7.2 File URL Processing

When a `file://` URL is included in a user message:

1. **Symbol Resolution**: If URL has `?start=X&end=Y` query parameters:
   - `LSP.documentSymbol(filePathURI)` is called to get document symbols
   - Symbol ranges are matched to resolve full function/class boundaries
   - File is read with `offset` and `limit` parameters

2. **File Reading**: File content is read via `ReadTool.execute()` and included as synthetic text parts

3. **Directory Listing**: If URL points to a directory, `ListTool.execute()` is called

#### 7.3 LSP Tools

LSP diagnostics and hover information are available as tools:
- `LSPDiagnosticsTool`: Provides code diagnostics for files
- `LSPHoverTool`: Provides hover information for symbols

These tools are registered in `ToolRegistry` and can be called by agents during code generation.

#### 7.4 LSP Usage Context

LSP is primarily used for:
- **Pre-generation context**: Symbol resolution when files are referenced in prompts
- **Code analysis**: Diagnostics and hover information available as tools
- **Not post-generation**: LSP is not automatically used to validate generated code (agents can call LSP tools if needed)

### 8. Permission System

The permission system controls tool access via `Permission.ask()`.

#### 8.1 Permission Flow

When a tool requires permission:

1. **Permission Check**: `Permission.ask()` is called with:
   - `type`: Permission type (e.g., "edit", "bash", "webfetch")
   - `pattern`: File path pattern or command pattern
   - `sessionID`, `messageID`, `callID`: Context identifiers
   - `title`, `metadata`: Human-readable information

2. **Approval Check**: System checks if permission is already approved for the session (via pattern matching)

3. **Plugin Hook**: If not approved, `Plugin.trigger("permission.ask")` is called:
   - Plugin can return "allow", "deny", or "ask"
   - If "ask", permission is queued for user approval
   - If "deny", `Permission.RejectedError` is thrown

4. **User Approval**: If queued, permission request is published via `Permission.Event.Ask` bus event
   - UI components can subscribe to show approval dialogs
   - User response is published via `Permission.Event.Response`

5. **Error Handling**: If permission is denied:
   - `Permission.RejectedError` is thrown
   - Tool execution is blocked
   - Error is stored in tool part
   - `blocked` flag is set (but doesn't stop the loop)

#### 8.2 Permission Configuration

Permissions are configured via `Agent.Info.permission`:
- `edit`: File edit permissions
- `bash`: Command execution permissions (per-command patterns)
- `webfetch`: Web fetch permissions

Patterns support wildcard matching via `Wildcard.match()`.

### 9. Plugin System

The plugin system provides hooks for extending functionality.

#### 9.1 Plugin Hooks

- `"chat.params"`: Modify LLM parameters before request
- `"chat.message"`: Process user message before storage
- `"tool.execute.before"`: Pre-execution hook for tools
- `"tool.execute.after"`: Post-execution hook for tools
- `"permission.ask"`: Permission request handling

#### 9.2 Plugin Registration

Plugins are loaded from:
- Project `plugin/*.{js,ts}` files
- Config-specified plugin paths
- Global plugin directory

Plugins can provide:
- Custom tools
- System prompt modifications
- Permission handlers
- Tool execution hooks

### 10. Core Components

- **Session Management** (`Session`): Stores conversation state, messages, and parts
- **Agent System** (`Agent`): Manages agent configuration, selection, and capabilities
- **Tool System** (`ToolRegistry`, individual tools): Executes actions against files and systems
- **Provider System** (`Provider`): Handles LLM interactions, model selection, and API abstraction
- **Permission System** (`Permission`): Controls tool access and user consent
- **LSP Integration** (`LSP`): Provides code analysis and symbol resolution
- **MCP Integration** (`MCP`): Connects to Model Context Protocol servers
- **Storage** (`Storage`): Persists session and project data
- **Bus** (`Bus`): Event system for component communication
- **CLI Interface** (`cli/cmd/run.ts`): User interaction entry point

## Key Implementation Details

### Message Format

Messages use `MessageV2` schema with:
- **Info**: Metadata (id, role, sessionID, model, tokens, cost, time, error)
- **Parts**: Content (text, tool, reasoning, patch, step-start, step-finish)

Parts are stored incrementally as the stream processes, allowing real-time updates.

### Tool Execution Context

Tools receive a context object with:
- `sessionID`: Current session identifier
- `messageID`: Current message identifier
- `callID`: Tool call identifier
- `agent`: Agent name
- `abort`: AbortSignal for cancellation
- `extra`: Additional context (modelID, providerID, etc.)
- `metadata`: Function to update tool part metadata during execution

### Error Handling

Errors are handled at multiple levels:
- **Tool Errors**: Stored in tool part with status "error"
- **Permission Errors**: `Permission.RejectedError` blocks tool but not session
- **Stream Errors**: Stored in message `error` field
- **Abort Errors**: `DOMException` with name "AbortError" stored as `MessageV2.AbortedError`
- **Output Length Errors**: `MessageV2.OutputLengthError` for token limit exceeded
- **Auth Errors**: `MessageV2.AuthError` for API key issues

### Session Compaction Details

Compaction is triggered when:
- `SessionCompaction.isOverflow()` returns true
- Token count (input + cache.read + output) > (context_limit - output_limit)

Compaction uses a small model (or same model with reduced reasoning) to summarize previous messages while preserving:
- Tool call results
- File changes
- Important context

### File Time Tracking

`FileTime` tracks when files are read to detect external modifications and trigger LSP updates.

### Command Processing

Commands support:
- Template substitution: `$ARGUMENTS` replaced with user input
- Shell execution: `` `command` `` syntax executes and inserts results
- File references: `@filename` resolves to file parts or agent parts
- Agent references: `@agent-name` resolves to agent parts

## AGENTS.md Inclusion Mechanism

AGENTS.md content is included via `SystemPrompt.custom()` which:

1. **File Discovery**: Searches for `AGENTS.md` in:
   - Local project directory (via `Filesystem.findUp()`)
   - Global config directory (`~/.opencode/AGENTS.md`)
   - Config-specified paths from `config.instructions`

2. **Content Inclusion**: Found files are read and their content is directly inserted into the system prompt

3. **Prompt Construction**: Called during `SessionPrompt.resolveSystemPrompt()` at line 454 in `packages/opencode/src/session/prompt.ts`

The AGENTS.md file content becomes part of the system prompt sent to the language model, providing agents with contextual information about available agents and their capabilities.
