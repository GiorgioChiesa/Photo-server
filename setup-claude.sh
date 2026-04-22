#!/bin/bash
set -e

echo "🚀 Setup Claude Code Pro..."

# 1. Struttura directory
mkdir -p .claude/{agents,skills,plans,hooks}
mkdir -p ~/.claude/hooks
mkdir -p ~/.config/claude-code/skills

# 2. CLAUDE.md base
cat > CLAUDE.md << 'EOF'
# Progetto — Contesto Claude Code

## Stack
- [descrivi il tuo stack]

## Comandi
```bash
# [i tuoi comandi principali]
```

## Convenzioni
- [le tue regole di coding]

## Architettura
- /src → [descrizione]
- /tests → [descrizione]
EOF

# 3. Settings con hooks essenziali
cat > .claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(python3:*)",
      "Bash(npm:*)",
      "Read(**)",
      "Edit(src/**)",
      "Edit(tests/**)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Read(.env.production)"
    ]
  },
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "osascript -e 'display notification \"Completato!\" with title \"Claude Code\"'"
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "echo \"Branch: $(git branch --show-current)\nStatus: $(git status --short | head -5)\""
      }]
    }]
  }
}
EOF

echo "✅ Setup completato!"
echo "Avvia con: ollama launch claude --model gemma4:26b"
