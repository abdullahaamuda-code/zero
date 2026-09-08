# Contributing to Zero

Thank you for your interest in improving Zero! We welcome contributions to help make Zero faster, more capable, and accessible to developers and operators everywhere.

---

## Architecture Overview

Zero is organized into modular components:

- **`backtalk/`**: The voice I/O engine (PTT microphone capture, Whisper STT, Kokoro TTS, signal bus).
- **`ai-visualizer/`**: The reactive audio/state HUD server and modular visual faces.
- **`vault/`**: Persistent markdown memory architecture (daily notes, active priorities, resources).
- **`AGENTS.md`**: Core identity prompt and operating mandates for the agent.

---

## How to Contribute

### 1. Reporting Issues
- Check existing GitHub issues before creating a new one.
- Provide clear reproduction steps, your OS, Python version, and relevant log outputs.

### 2. Developing Features & Fixes
1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/abdullahaamuda-code/zero.git
   cd zero
   ```
2. **Create a topic branch**:
   ```bash
   git checkout -b feature/my-new-feature
   # or
   git checkout -b fix/issue-description
   ```
3. **Keep it lightweight**:
   - Do NOT commit large binary assets, virtual environment folders (`.venv`), model weights, or personal cache files.
   - Zero is built to be fast, portable, and minimal.
4. **Test your changes**:
   - Verify `backtalk` modules and syntax:
     ```bash
     cd backtalk
     python -c "import backtalk.config, backtalk.vault_logger; print('OK')"
     ```
   - Verify `ai-visualizer`:
     ```bash
     cd ../ai-visualizer
     python server.py --mock speaking --no-open
     ```
5. **Never commit secrets**:
   - Ensure `.env`, API keys, passwords, and personal directory paths are never committed. Use `.env.example` or config templates for placeholders.

### 3. Pull Request Guidelines
- Write clear, concise commit messages.
- Describe what the PR accomplishes and reference any related issues.
- Ensure all tests pass before submitting.
