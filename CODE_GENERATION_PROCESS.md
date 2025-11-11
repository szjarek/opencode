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
