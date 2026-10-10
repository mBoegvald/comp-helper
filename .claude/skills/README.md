# Skills for Claude Code

`svelte-code-writer` and `svelte-core-bestpractices` come from
[sveltejs/ai-tools](https://github.com/sveltejs/ai-tools/tree/main/tools/skills) at commit 6b5d0da (2026-10-05),
MIT licensed (LICENSE-svelte-ai-tools). One local change: svelte-code-writer says to run `npx @sveltejs/mcp` from
`frontend/`, where the CLI is a pinned dev dependency.

To update: copy `tools/skills/*` from a newer commit over these folders, keep the local change, and bump
`@sveltejs/mcp` in frontend/package.json (two weeks old at least, like every dependency).
