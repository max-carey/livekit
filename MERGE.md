# Merge Instructions for Weather Tool Feature

This feature adds a practice weather lookup tool to the LiveKit agent.

## Changes Made

- Added `function_tool` and `RunContext` imports to `agent.py`
- Added `typing.Any` import for type annotations
- Implemented `lookup_weather` function tool in the `Assistant` class
- Added proper docstring and type hints for the weather tool

## Merge Options

### Option 1: GitHub PR (Recommended)

1. Push the feature branch to GitHub:
   ```bash
   git add .
   git commit -m "Add weather lookup tool to agent"
   git push origin feature/add-weather-tool
   ```

2. Create a Pull Request on GitHub:
   - Go to your repository on GitHub
   - Click "Compare & pull request" for the `feature/add-weather-tool` branch
   - Add description: "Adds a practice weather lookup tool to the LiveKit agent"
   - Review the changes and merge

### Option 2: GitHub CLI

1. Create and push the PR using GitHub CLI:
   ```bash
   git add .
   git commit -m "Add weather lookup tool to agent"
   git push origin feature/add-weather-tool
   gh pr create --title "Add weather lookup tool to agent" --body "Adds a practice weather lookup tool to the LiveKit agent with proper type hints and documentation."
   ```

2. Merge the PR:
   ```bash
   gh pr merge feature/add-weather-tool --merge
   ```

3. Clean up the feature branch:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/add-weather-tool
   git push origin --delete feature/add-weather-tool
   ```

## Testing

After merging, test the weather tool by running the agent and asking questions like:
- "What's the weather like in New York?"
- "Can you check the weather for London?"
- "How's the weather in Tokyo?"

The agent should respond with the mock weather data (sunny, 70°F) for any location. 