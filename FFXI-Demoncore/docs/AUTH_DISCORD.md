# Discord-OAuth Login (PlayOnline Killshot)

PlayOnline is dead in this remake. Authentication, account management, role gating, ban appeals, even patch announcements — all of it routes through Discord. chharbot is the moderator.

## Why kill PlayOnline

- **Friction.** New player onboarding through PlayOnline is the worst part of FFXI. We don't recreate the worst part of FFXI.
- **Security.** PlayOnline auth is 2002-era. Modern OAuth + 2FA via Discord is dramatically safer.
- **Identity coupling.** A character is already a person to its Discord guild. Linking the game account to that Discord identity is a small step that pays back enormously when one player wants to gift gear to another, or when a fomor's owner wants to be notified that their toon was just killed in Beadeaux.
- **Moderation surface.** A misbehaving player gets reported in Discord, banned in Discord, and the same action propagates to the game server. One ledger, one source of truth.

## The flow

```
new player
    │
    ▼
Discord guild invite (server-specific link)
    │
    ▼
join → automatic chharbot DM with verification button
    │
    ▼
click → chharbot OAuth flow (auth code grant)
    │
    ▼
authorized → chharbot reads identify scope, assigns @Verified role
    │
    ▼
chharbot mints LSB account token, stores in DB keyed by Discord ID
    │
    ▼
DMs the user a one-time launcher download link + the token
    │
    ▼
launcher uses token to authenticate against the LSB login server
    │
    ▼
character select → world entry
```

After first verification, every subsequent login is silent — the launcher caches the token and refreshes via Discord's refresh-token flow when it expires (every ~7 days).

## Tooling

- [`discord/discord-oauth2-example`](https://github.com/discord/discord-oauth2-example) — Discord's own reference impl. Shape of the auth code grant flow we follow.
- [`treeben77/discord-oauth2.py`](https://github.com/treeben77/discord-oauth2.py) — Python wrapper for OAuth2 + Linked Roles. We use this in chharbot's verification module.
- [`Rapptz/discord.py`](https://github.com/Rapptz/discord.py) — chharbot's Discord bot foundation (already in the chharbot stack).

We do NOT add a separate web app for the OAuth flow. chharbot handles the redirect URI in its own HTTP server (we already run `lsb_admin_api` for the FFXI sidecar — same Python process can host one more route).

## Token lifecycle

| Token | Lifetime | Stored where | Used for |
|-------|----------|--------------|----------|
| Discord access token | 7 days | chharbot DB, encrypted | Reading user's Discord identity, role checks |
| Discord refresh token | indefinite (until revoked) | chharbot DB, encrypted | Renewing access token |
| **LSB account token** | 30 days, sliding window | LSB account DB, hashed | Game-client login |
| Session token | 12 hours | In-memory, server-side | One game session |

The LSB account token is what the modified launcher sends instead of the PlayOnline ID/POL handshake. It maps to a row in `accounts` (we extend the existing schema with a `discord_id` and `linked_at` column).

## chharbot moderator behavior

chharbot is the only moderator. Humans don't have ban buttons; chharbot does, on the basis of policies it executes.

| Trigger | chharbot action |
|---------|-----------------|
| New member joins guild | DM with verification button |
| Verification timeout (24h, no click) | Auto-kick |
| Reported message (any user can `/report`) | chharbot reads context, decides: dismiss / warn / mute / ban. Logs rationale. |
| Game-side rule violation (RMT, exploits, harassment in tells) | LSB server emits an event → chharbot ingests → applies same Discord-side action |
| Appeal channel message | chharbot reviews ban context, asks clarifying questions, can lift ban or escalate to human ops |
| Patch released | chharbot announces in #patch-notes with summary generated from commit log |
| Server outage detected | chharbot announces + opens triage thread |

Every chharbot moderation action writes a JSONL audit line to `~/.chharbot/discord-mod.log`. A `/why <user>` command in any channel returns the user's full moderation history (including reasons).

The owner can override any chharbot action via a `/override` slash command. chharbot logs the override and learns from it (the override goes into chharbot's reflection memory; over time the agent calibrates its judgment to the owner's tolerance).

## Threat model

- **Discord account compromise.** Mitigation: `/me` re-verification flow can force a re-auth. Banned IP list maintained for known compromised tokens. Loss tolerance: an attacker with a compromised Discord can play your character for up to 12 hours before next session token expiry.
- **Token replay.** Mitigation: LSB account tokens are bound to a hardware fingerprint reported by the launcher. Mismatch → revoke + re-verify.
- **Ban evasion via alt Discords.** Mitigation: chharbot enforces a unique-on-phone-number rule for new verifications (Discord exposes this via the OAuth `phone` scope, opt-in).
- **chharbot itself misbehaving.** Mitigation: every action is reversible by `/override`; full audit log; if chharbot is offline, the gate stays *closed* (no new verifications until owner restores it).

## What to build first

1. **OAuth callback handler in chharbot.** Single Flask/FastAPI route. Smallest viable thing.
2. **DB extension on LSB.** Add `discord_id`, `linked_at`, `lsb_token` to `accounts`.
3. **Verification button + DM flow.** Discord.py-based; the `Verified` role is the carrot.
4. **Modified launcher.** Skip POL entirely; show "Sign in with Discord" → opens browser → returns to launcher with cached token.
5. **Mod actions.** `/report`, `/ban`, `/why`, `/override`, `/appeal`. Build incrementally; v1 is just `/report` with chharbot replying "noted, will review."
6. **Game-side ↔ Discord-side sync.** Bi-directional. v1 is one-direction (Discord ban → game ban). v2 adds the reverse.

This is *the* infrastructure piece — without it, none of the rest of FFXI Hardcore has a front door. Build it after the visual / world / AI prototypes show signal but before any external invite.

## Open questions

- **Region locking.** Do we let international players in unfettered, or gate via Discord region? Default: unfettered. We can revisit if abuse becomes structural.
- **Dual-client.** Do we keep PlayOnline support for legacy players who insist? Strong default: no. The whole point is to cut it. Hardcore players will appreciate the modern flow.
- **Account portability.** Can a player port their existing LSB account to a Discord-linked one? Yes — a one-time link flow during the cutover window. After that, no.
- **Voice integration.** Discord voice → in-game positional audio? Tempting. Out of scope for v1.
