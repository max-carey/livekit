# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LiveKit AI agent project that implements a language learning system called "Vocab Voice". The application provides two types of interactive language learning sessions:

1. **Native Explanation** - Users explain L2 vocabulary meanings in their native language
2. **Listening Practice** - Interactive dialogue practice sessions

The agent system uses voice interaction with speech-to-text, large language models, and text-to-speech to create immersive learning experiences.

## Architecture

### Core Components

- **`agent.py`** - Main entry point with `HostAgent` class that manages session routing
- **Agent Classes** - Specialized agents for different learning types in `agents/` directory:
  - `NativeExplainAgent` (`agents/native_explain_agent.py`) - Handles native language explanations of L2 vocabulary
  - `ListenAgent` (`agents/listening_agent.py`) - Manages dialogue practice sessions
- **Prompt System** - YAML-based prompt management in `prompts/` directory
  - `loader.py` - Utility to load prompts from YAML files
  - Prompt files: `host.yaml`, `native_explain.yaml`, `dialogue_comprehension.yaml`
- **`dialogue_generator.py`** - Standalone script to generate practice dialogues with audio using OpenAI and ElevenLabs

### Technology Stack

- **LiveKit Agents Framework** - Core agent orchestration
- **Speech Processing**:
  - STT: Deepgram Nova-3 (multilingual)
  - TTS: Cartesia Sonic-2 (low-latency, high-quality)
  - VAD: Silero
  - Turn Detection: MultilingualModel
- **LLM**: OpenAI GPT-4o-mini
- **Audio Processing**: Background audio player support
- **Noise Cancellation**: BVC (Background Voice Cancellation)

## Development Commands

### Running the Agent
```bash
python agent.py
```

### Generate Practice Dialogues
```bash
python dialogue_generator.py <target_word>
```
This creates audio dialogues in the `audios/` directory using the target word.

### Package Management
Uses `uv` for dependency management:
```bash
uv sync  # Install dependencies
uv add <package>  # Add new dependency
```

## Environment Variables Required

- `OPENAI_API_KEY` - For LLM and dialogue generation
- `CARTESIA_API_KEY` - For text-to-speech services
- LiveKit credentials (set via LiveKit's standard environment variables)

## Prompt Management

Prompts are stored as YAML files in `prompts/` directory with the structure:
```yaml
system_prompt: |
  Your prompt content here
```

Use `load_prompt(name)` function to load prompts in agent code.

## Agent Architecture Pattern

Each agent follows this pattern:
1. Inherits from LiveKit's `Agent` class
2. Configures STT, LLM, TTS, VAD, and turn detection in `__init__`
3. Uses `@function_tool()` decorators for callable functions
4. Implements `on_enter()` hook for initialization when agent becomes active
5. Can return other agents from function tools to chain sessions

The `HostAgent` acts as a router, allowing users to choose between different quiz types and managing transitions between specialized agents.