## IMPORTANT

- Try to keep things in one function unless composable or reusable
- DO NOT do unnecessary destructuring of variables
- DO NOT use `else` statements unless necessary
- DO NOT use `try`/`catch` if it can be avoided
- AVOID `try`/`catch` where possible
- AVOID `else` statements
- AVOID using `any` type
- AVOID `let` statements
- PREFER single word variable names where possible
- Use as many bun apis as possible like Bun.file()
- Use Bun APIs like `Bun.file()` where possible
- Use TypeScript with strict typing
- Follow Prettier formatting (semi: false, printWidth: 120)
- Import ordering: external libraries, internal modules, then relative paths
- Naming: camelCase for variables, PascalCase for components
- Error handling: use explicit error types rather than generic catch blocks

## Build/Lint/Test Commands

- Typecheck: `bun turbo typecheck`
- Test: `bun turbo test`
- Run single test: `bun test --filter="test-name"`
- Format: `bun run format`
- Dev server: `bun dev` in packages/console/app

## Debugging

- To test in development: `bun dev` in packages/console/app
- Use `bun run` for executing scripts
## Tool Calling

- ALWAYS USE PARALLEL TOOLS WHEN APPLICABLE. Here is an example illustrating how to execute 3 parallel file reads in this chat environnement:

json
{
    "recipient_name": "multi_tool_use.parallel",
    "parameters": {
        "tool_uses": [
            {
                "recipient_name": "functions.read",
                "parameters": {
                    "filePath": "path/to/file.tsx"
                }
            },
            {
                "recipient_name": "functions.read",
                "parameters": {
                    "filePath": "path/to/file.ts"
                }
            },
            {
                "recipient_name": "functions.read",
                "parameters": {
                    "filePath": "path/to/file.md"
                }
            }
        ]
    }
}
