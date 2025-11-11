# Code Generation Process

## Overview

This document describes the end-to-end workflow from user prompt to generated code implementation in the opencode system.

## Prompt Construction

The LLM prompt is constructed in the session management component through the SessionPrompt namespace. It includes:

- Current session context and conversation history from Session.messages()
- Available tools catalogue from the ToolRegistry system
- Agent-specific system prompts from Agent system
- Project context and configuration from Instance and Config
- Any relevant file contents or LSP diagnostics from relevant tools
- System prompts from SystemPrompt provider and configuration

## LLM Interaction

The prompt is sent to the LLM through the Provider system, which abstracts AI provider differences and handles model selection and API interactions via the ai library's streamText function. The interaction uses:

- ProviderTransform for model-specific parameter handling
- SessionPrompt.createProcessor for managing stream processing
- Tool registry through activeTools parameter to specify available tools

## Response Processing

LLM responses are parsed and validated through:

- Zod schemas for parameter validation
- Tool registry to verify tool availability
- Permission system to ensure appropriate access via Permission.RejectedError
- Session management to store results via Session.updatePart

## Tool Selection

Tool decisions are made by agents based on:

- Agent configuration and capabilities from Agent.Info
- User permissions and consent via Agent.permission
- Tool availability in the tools registry (ToolRegistry.tools)
- LSP diagnostics for code context through LSP tools integration
- MCP (Model Control Protocol) integration where applicable using MCP.tools()

## Tool Execution

Tools execute through the tool system with:

- Permission checks before execution via Permission system
- File system integration via ReadTool, WriteTool, EditTool etc.
- LSP integration for code analysis and diagnostics
- Safe execution patterns to prevent destructive operations
- MCP (Model Control Protocol) integration via MCP.tools()
- Task-based execution flow through TaskTool for subagents

## Result Processing

Values returned from tools are processed through:

- Session parts storage for history using Session.updatePart
- Diff generation for changes using PatchTool and Snapshot system
- LSP updates for code context through LSP integration
- Global state updates for system consistency via Bus events

## Next Step Determination

Next steps are determined by:

- Agent decision-making based on current context and agent mode
- Tool results and their implications through ToolRegistry.enabled()
- User feedback loop through CLI interface via SessionPrompt.prompt()
- System state and project requirements via Session management and Config

## Core Components Involved

- Session Management: Stores conversation state and history (Session, MessageV2)
- Agent System: Makes decisions about tool usage (Agent, SystemPrompt)
- Tool System: Executes actions against files and systems (ToolRegistry, individual tools)
- CLI Interface: Provides user interaction points (cli/cmd/run.ts)
- Project Management: Establishes project context (Instance, Project)
- Configuration: Drives behavior and permissions (Config)
- Storage: Persists session and project data (Storage)
- Provider System: Handles LLM interactions (Provider)
- Permission System: Controls tool access (Permission)
- LSP Integration: Provides code context (LSP, LSP diagnostics tools)


# Key prompt sections
• Session Context: Includes conversation history from Session.messages()
• Agent Configuration: Agent-specific system prompts and tool availability from the Agent system
• Project Context: Configuration and instance details from Instance and Config
• Tool Catalogue: Available tools from ToolRegistry
• System Prompts: From SystemPrompt provider and configuration
• LSP Diagnostics: Code analysis from LSP tools
• MCP Tools: Tools integrated through Model Control Protocol
These components are structured to provide comprehensive context for the LLM to make informed decisions about tool usage and code generation.

## Base System Prompt

The base system prompt is constructed via SessionPrompt.resolveSystemPrompt which:

• Starts with a header from SystemPrompt.header
• Adds provider-specific prompts from SystemPrompt.provider
• Includes environment variables from SystemPrompt.environment
• Adds custom prompts from SystemPrompt.custom
• Combines into a maximum of two system message entries for caching

## AGENTS.md Integration

When AGENTS.md is included in the prompt, its contents are accessed through:

• Agent configuration from Agent.Info schema and Agent.list()
• Agent capabilities specified in the agent's tool permissions
• Agent mode settings like 'primary', 'subagent', or 'all'
• Agent-specific system prompts defined in Agent.prompt

## Available Tools Description

Tool descriptions are built through:

1. ToolRegistry.ts which:
 • Loads all built-in tools like EditTool, ReadTool, WebFetchTool, etc.
 • Registers custom tools from plugins
 • Provides tools via ToolRegistry.tools() method
2. MCP integration via MCP.tools() which:
 • Connects to MCP servers defined in config
 • Exposes MCP tool definitions with sanitized names
 • Applies wildcard matching for tool enabling/disabling


The tool descriptions include:

• Tool identifier (id)
• Tool description from tool definition
• Parameters schema for tool inputs
• Execute method for tool implementation

## Additional Prompt Components

Other prompt parts include:

• Conversation history from Session.messages()
• LSP diagnostics when available
• File contents when requested through the LSP integration
• Project context from Instance and Config
• Model-specific parameters from ProviderTransform
• User permission constraints from Permission system
• Agent-specific configuration from Agent.Info

Each component is filtered or transformed to meet the requirements of the specific LLM provider and model configuration, ensuring secure and effective tool usage within the context of
the session.


# LSP
## 1. Tool Integration

• LSP namespace provides LSP client functionality
• LSP diagnostics are used in LSPDiagnosticsTool to provide code context
• LSP hover information via LSPHoverTool
• LSP.documentSymbol for symbol search and range resolution

## 2. Prompt Construction

• When files are included in prompts via file URLs, LSP is used to:
 • Get document symbols for accurate code context
 • Resolve symbol ranges for partial file content
 • Provide better contextual information in prompts


## 3. File Operations

• File references in prompts trigger LSP operations:
 • Symbol resolution when a file URL has a range
 • Directory listings through ListTool combined with LSP for file structure


## 4. Code Analysis

• LSP diagnostics are passed to the LLM through tools
• Symbol information helps with better semantic understanding during code analysis

## 5. How LSP is Integrated

1. Tool System: LSP tools are registered in the tool system (ToolRegistry.tools)
2. Session Handling: File URL parsing in createUserMessage triggers LSP operations
3. Command Processing: Commands like ! (shell commands) use LSP for context
4. Prompt Creation: LSP diagnostics are injected into prompts for better context

## 6. The LSP integration provides semantic code understanding that enhances the LLM's ability to generate accurate and contextually appropriate code solutions.
LSP is mainly used in these contexts:

1. During Prompt Construction: When file paths are included in user messages, LSP is used to:
 • Get document symbols for better code context
 • Resolve symbol ranges for partial file content
 • Provide diagnostic information about code
2. Tool Execution: LSP diagnostics and hover information are available as tools that agents can call during code generation, but these aren't typically used afterward.
3. Pre-Generation Context: LSP integration provides context for the LLM before it even generates code, which helps in understanding the current project's state.

The system does not appear to have any mechanisms for automatically analyzing the generated code with LSP after it is created. The LSP integration is designed as a tool that agents can
call when needed, rather than a passive monitoring system for generated code evaluation. The architecture emphasizes using LSP for context during code generation rather than for
post-generation analysis.



# AGENTS.md inclusion mechanism
AGENTS.md content is added to the LLM prompt through the SystemPrompt.custom() function in packages/opencode/src/session/system.ts.

## Where it happens

The inclusion occurs in the resolveSystemPrompt function in packages/opencode/src/session/prompt.ts at line 412, where await SystemPrompt.custom() is called.

## How it works

1. File discovery: SystemPrompt.custom() searches for AGENTS.md in:
 • Local project directory using Filesystem.findUp()
 • Global configuration directories
2. Content inclusion: Found AGENTS.md files are read and their content is directly inserted into the system prompt
3. Prompt construction: The function is called during system prompt generation in the SessionPrompt namespace, integrating the AGENTS.md content as part of the LLM context

The AGENTS.md file content becomes part of the system prompt sent to the language model, providing agents with contextual information about available agents and their capabilities.