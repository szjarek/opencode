# ARCHITECTURE.md

## Overview

This document describes the internal structure of the core opencode package (`@packages/opencode/src/`). The architecture follows a modular pattern designed to separate concerns while enabling seamless interaction between components.

## Core Components

### 1. Session Management (`/session/`)

**Files**: `index.ts`, `message-v2.ts`, `prompt.ts`
**Responsibility**: Manages conversation sessions, messages, and parts (content chunks)
**Dependencies**: `Storage`, `Project`, `MessageV2`, `Config`
**Place in Repository**: Central to core functionality for tracking user interactions

The session system handles all conversation state. It provides APIs for creating, updating, and managing sessions. Each session contains multiple messages, and each message contains multiple parts. Sessions are persisted to storage and can be shared.

### 2. Agent System (`/agent/`)

**Files**: `agent.ts`, `generate.txt`
**Responsibility**: Manages AI agents with different capabilities, permissions, and prompts
**Dependencies**: `Provider`, `Config`, `SystemPrompt`, `Permission`
**Place in Repository**: Core AI decision-making system that directs tool usage

Agents are configured with specific capabilities, permissions, and behavior patterns. The system supports both built-in agents (general, build, plan) and user-defined agents. Each agent defines what tools it can use and what permissions it requires.

### 3. Tool System (`/tool/`)

**Files**: `tool.ts`, `edit.ts`, `read.ts`, etc.
**Responsibility**: Defines and implements tools that agents can execute (file editing, reading, searching, etc.)
**Dependencies**: `Permission`, `File`, `LSP`, `Instance`
**Place in Repository**: Provides the capability layer for agents to interact with files and systems

Tool implementations are designed to be safe and permission-controlled. Each tool defines its parameters and execution logic. Tools can request permission from users when necessary.

### 4. CLI Interface (`/cli/`)

**Files**: `cmd/` subdirectory with command files, `bootstrap.ts`, `ui.ts`
**Responsibility**: Command-line interface for executing opencode commands
**Dependencies**: `RunCommand`, `Session`, `Provider`, `Agent`
**Place in Repository**: Entry point for user interaction

The CLI handles command parsing, argument validation, and execution. Each command is defined in its own file within the cmd/ directory and integrates with core systems.

### 5. Project Management (`/project/`)

**Files**: `project.ts`, `instance.ts`, `bootstrap.ts`
**Responsibility**: Manages project-level state and initialization
**Dependencies**: `Instance`, `Storage`, `Config`
**Place in Repository**: Establishes project context for all operations

Handles project initialization, provides project context to all components, and manages project-related state like workspace directories.

## Supporting Components

### Configuration (`/config/`)

Manages user settings and application configuration.

### Storage (`/storage/`)

Handles persistence of session data and project state using a key-value storage system.

### Provider System (`/provider/`)

Manages AI providers (OpenAI, Anthropic) and model selection.

### Business Logic (`/bus/`)

Event-driven communication system between components.

### Permission System (`/permission/`)

Controls tool access permissions and user consent for potentially destructive operations.

### ID Generation (`/id/`)

Provides unique identifier generation for sessions, messages, and parts.

### Global State (`/global/`)

Manages global application state.

### Installation (`/installation/`)

Handles version checking and installation-related utilities.

## Data Flow Architecture

1. CLI commands create sessions
2. Agents analyze and decide on tools to use based on their configuration and permissions
3. Tools execute actions against files or system resources
4. Results are stored in session parts
5. All data persists through the storage layer
6. Sessions can be shared or exported

## Key Dependencies and Interactions

- **Core Dependencies**:
  - `ai` (for LLM interactions)
  - `zod` (for parameter validation)
  - `decimal.js` (for cost calculation)
  - `diff` (for file diffing)
  - `remeda` (for functional utilities)

- **Data Flow Pattern**:
  - CLI → Session Creation → Agent Decision → Tool Execution → Storage Update → Return Results

- **Component Relationships**:
  - Agents define what tools can be used and with what permissions
  - Tools interact with the file system and LSP
  - Sessions are the container for all conversation history
  - Project management provides context and initialization
  - Configuration drives behavior and permissions

The architecture follows a modular pattern where each component has specific responsibilities and communicates through clearly defined APIs, enabling easy extension of tool capabilities and agent behaviors while maintaining separation of concerns.
