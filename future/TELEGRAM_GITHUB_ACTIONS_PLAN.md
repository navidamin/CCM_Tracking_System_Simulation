# Telegram → GitHub Actions → Claude Code Pipeline

## Goal

Allow team members to trigger Claude Code tasks (simulation runs, analysis updates,
code changes) via Telegram messages, with results posted back to Telegram.

---

## Architecture

```
┌──────────┐     webhook      ┌────────────────────┐    gh workflow    ┌─────────────────┐
│ Telegram │ ───────────────► │ Cloudflare Worker  │ ──────────────► │ GitHub Actions  │
│   Bot    │                  │ (relay + auth)     │                  │ (Claude Code)   │
└──────────┘                  └────────────────────┘                  └────────┬────────┘
     ▲                               ▲                                        │
     │           result callback     │          commit/push/comment           │
     └───────────────────────────────┘◄───────────────────────────────────────┘
```

### Components

| # | Component            | Role                                              | Cost     |
|---|----------------------|----------------------------------------------------|----------|
| 1 | Telegram Bot         | User interface — send prompts, receive results     | Free     |
| 2 | Cloudflare Worker    | Webhook receiver, auth gate, GH API caller         | Free     |
| 3 | GitHub Actions       | Runner — checks out repo, runs Claude Code CLI     | Free*    |
| 4 | Anthropic API        | Claude does the actual work                        | ~$0.05–0.50/task |

\* Free for public repos; 2000 min/month for private repos.

---

## Step-by-Step Implementation Plan

### Phase 1: Telegram Bot Registration

1. Message `@BotFather` on Telegram → `/newbot`
2. Name: `CCM Simulation Bot` (or similar)
3. Save the **bot token** — will be stored as GitHub secret
4. Set bot commands via BotFather:
   ```
   /run - Run simulation at a velocity (e.g. /run 2.5)
   /sweep - Run velocity sweep with 20 seeds
   /analyze - Run crane parametric analysis
   /ask - Ask Claude a question about the codebase
   /status - Check last workflow run status
   ```
5. Note the **chat ID** of the authorized group/user (for auth filtering)

### Phase 2: GitHub Actions Workflow

Create `.github/workflows/claude-telegram.yml`:

```yaml
name: Claude Code (Telegram-triggered)

on:
  workflow_dispatch:
    inputs:
      prompt:
        description: 'Task for Claude'
        required: true
        type: string
      telegram_chat_id:
        description: 'Chat ID to reply to'
        required: true
        type: string
      telegram_message_id:
        description: 'Message ID to reply to'
        required: false
        type: string

permissions:
  contents: write
  pull-requests: write

jobs:
  claude:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Claude Code
        id: claude
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: ${{ github.event.inputs.prompt }}

      - name: Notify Telegram
        if: always()
        run: |
          STATUS="${{ job.status }}"
          CHAT_ID="${{ github.event.inputs.telegram_chat_id }}"
          MSG="*Claude Code finished* ($STATUS)\n\nPrompt: ${{ github.event.inputs.prompt }}\n\nRun: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          curl -s -X POST \
            "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
            -d chat_id="$CHAT_ID" \
            -d parse_mode="Markdown" \
            -d text="$MSG"
```

### Phase 3: Cloudflare Worker (Webhook Relay)

The worker receives Telegram webhook updates and dispatches GitHub workflows.

```
future/cloudflare-worker/
├── wrangler.toml
├── src/
│   └── index.ts
```

**Core logic (`src/index.ts`):**

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const update = await request.json();
    const msg = update.message;

    // Auth: only allow specific chat IDs
    if (!env.ALLOWED_CHAT_IDS.split(',').includes(String(msg.chat.id))) {
      return new Response('Unauthorized', { status: 403 });
    }

    // Parse command
    const text = msg.text || '';
    let prompt = '';

    if (text.startsWith('/run ')) {
      const vel = text.replace('/run ', '').trim();
      prompt = `Run simulation at velocity ${vel} m/min and report results`;
    } else if (text.startsWith('/sweep')) {
      prompt = 'Run velocity sweep with 20 seeds and report max safe velocity';
    } else if (text.startsWith('/analyze')) {
      prompt = 'Run crane parametric analysis and summarize findings';
    } else if (text.startsWith('/ask ')) {
      prompt = text.replace('/ask ', '').trim();
    } else if (text.startsWith('/status')) {
      // Query last GH Actions run status via gh API
      return await checkLastRun(env, msg.chat.id);
    } else {
      // Free-form prompt
      prompt = text;
    }

    // Dispatch GitHub Actions workflow
    const ghResponse = await fetch(
      `https://api.github.com/repos/${env.GH_REPO}/actions/workflows/claude-telegram.yml/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `token ${env.GH_TOKEN}`,
          'Content-Type': 'application/json',
          'User-Agent': 'ccm-telegram-bot',
        },
        body: JSON.stringify({
          ref: 'main',
          inputs: {
            prompt,
            telegram_chat_id: String(msg.chat.id),
            telegram_message_id: String(msg.message_id),
          },
        }),
      }
    );

    // Acknowledge to user
    await sendTelegram(env, msg.chat.id,
      `⏳ Task dispatched to Claude Code.\n\nPrompt: ${prompt}`
    );

    return new Response('OK');
  },
};
```

**Worker secrets (via `wrangler secret put`):**
- `TELEGRAM_BOT_TOKEN`
- `GH_TOKEN` (GitHub PAT with `repo` + `actions` scope)
- `ALLOWED_CHAT_IDS` (comma-separated)

**Webhook registration:**
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://ccm-bot.<account>.workers.dev"
```

### Phase 4: GitHub Repository Secrets

Add these in Settings → Secrets and variables → Actions:

| Secret                 | Value                                  |
|------------------------|----------------------------------------|
| `ANTHROPIC_API_KEY`    | Anthropic API key                      |
| `TELEGRAM_BOT_TOKEN`  | From BotFather                         |
| `GH_TOKEN`            | GitHub PAT (for worker → GH dispatch)  |

### Phase 5: Testing & Hardening

1. **Smoke test**: Send `/ask What is the max safe velocity?` via Telegram
2. **Simulation test**: Send `/run 2.0` and verify plots are generated
3. **Error handling**: Verify timeout/failure notifications reach Telegram
4. **Rate limiting**: Add per-user cooldown in the Cloudflare Worker (e.g., 1 task/min)
5. **Queue visibility**: Add `/status` command to check running/queued workflows

---

## Security Considerations

- **Auth filtering**: Only whitelisted `chat_id`s can trigger workflows
- **No secrets in prompts**: Prompts are visible in GitHub Actions logs
- **API key rotation**: Rotate `ANTHROPIC_API_KEY` quarterly
- **Workflow timeout**: 30-minute cap prevents runaway costs
- **Branch protection**: Claude pushes to feature branches, not `main`

---

## Cost Estimate (Monthly)

| Usage Level         | GitHub Actions | Anthropic API | Total     |
|---------------------|----------------|---------------|-----------|
| Light (5 tasks/day) | Free           | ~$5           | ~$5       |
| Moderate (20/day)   | Free           | ~$20          | ~$20      |
| Heavy (50/day)      | Free*          | ~$50          | ~$50      |

\* May approach 2000 min/month limit on private repos at heavy usage.

---

## Future Extensions

- [ ] Inline result previews (send plots as Telegram photos)
- [ ] PR creation flow: Claude creates PR, bot sends link, user approves via button
- [ ] Scheduled runs: cron-triggered sweeps with automatic Telegram reports
- [ ] Multi-repo support: route commands to different repositories
- [ ] Cost dashboard: track API spend per user/command

---

## File Checklist

When implementing, create these files:

```
.github/workflows/claude-telegram.yml    ← GitHub Actions workflow
cloudflare-worker/wrangler.toml          ← Worker config
cloudflare-worker/src/index.ts           ← Webhook relay logic
cloudflare-worker/package.json           ← Dependencies
```

Store all secrets in GitHub Actions secrets and Cloudflare Worker secrets — never in code.
