# Project Instructions

You are Kilo working on a rental listing automation project.

## Mandatory startup
Always read these files first:
- `.kilo/agents/rental-agent.md`
- `must_have.md`
- `nice_to_have.md`

## Default workflow for listing URLs
When the user sends a rental listing URL without extra instructions:
1. Treat it as a `rental-agent` task.
2. Follow `rental-agent.md` exactly.
3. Do not improvise a different format.
4. Do not output descriptions in English unless explicitly asked.
5. Use the result format from `rental-agent.md`.

## Allowed outputs
- Save results to `{YYYY-MM-DD}.md` in the workspace root.
- For Telegram/WhatsApp sending, use existing scripts and agents only.
- Do not invent new formats.

## Allowed MCPs for this project
- For rental tasks, use only the MCPs required for Telegram/WhatsApp sending and local execution.
- Do not explore, enable, or use unrelated MCPs such as Google Sheets, spreadsheets, docs, or any workspace MCPs unless the user explicitly asks for them in the current task.
- If an unrelated MCP is present in the environment, ignore it.

## Hard rules
- Do not skip the review step.
- Do not send messages without user confirmation.
- Do not expose secrets.
- If a step is unclear, follow `rental-agent.md` instead of improvising.
- Use a single-pass workflow. Do NOT spawn multiple subagents for translation and review. Do everything in one `rental-agent` pass.
