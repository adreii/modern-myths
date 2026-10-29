# Everyday Myths channel

A Roblox-style short-video channel (Instagram Reels / YouTube Shorts). Each episode follows Barthes's *Mythologies*: it decodes the hidden "myth" in an everyday thing, then asks an ethical question. The episodes form a corpus to derive ethics from.

- Corpus tracker: https://claude.ai/artifact/N1RKyp9u41NHKVKsi7GF19 (db collection `episodes`)
- Shot lists: `ep01-shot-list.md`
- Episode skill (ideas, scripts, shot lists, cinematography): `.claude/skills/everyday-myths-episode/SKILL.md`
- Roblox Studio helpers: `roblox/StoryKit/*.luau`; setup in `roblox/SETUP.md`
- Studio MCP server: `.mcp.json` (needs Roblox Studio installed and open, with **Enable Studio as MCP server** turned on)

## Working rules
- **Easy questions (how-to, "how do I…", quick facts) go to a subagent.** Brief it with the facts it needs, then relay its answer.
- **At the end of every chat, have a Sonnet subagent build a to-do list.** It writes or updates `TODO.md` here from what the chat did, what's blocked and what's unverified. Then relay it to the user.
