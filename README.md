# RunDeck

A gamified task deck in a cyberpunk terminal style. XP, combos, loot drops, a focus timer and a reward shop, with switchable palettes, typefaces and panel ornaments. English, Polish and Swedish.

It is a static site with no build step: `index.html`, `config.js`, and the SQL in `supabase/`.

## Run locally

```
npx serve .
```

Without Supabase keys in `config.js`, everything saves to the browser's local storage.

## Accounts with Supabase

1. Create a project at supabase.com.
2. In the SQL editor, run `supabase/schema.sql`. It creates `profiles`, `decks`, the `avatars` storage bucket and the row-level security policies.
3. In Authentication → URL Configuration, set the Site URL to your Vercel domain and add it to the redirect URLs, so confirmation and login-link emails land back on the app.
4. Copy the project URL and the anon public key from Project Settings → API into `config.js`:

```js
window.RUNDECK_CONFIG = {
  supabaseUrl: "https://xxxx.supabase.co",
  supabaseAnonKey: "eyJ..."
};
```

The anon key is meant to be public; the secret (service role) key must never go in the app or the repo.

### Security and privacy

- Passwords are handled and hashed by Supabase Auth. RunDeck's tables never contain emails or passwords.
- Row-level security is forced on every table: each user can read and change only their own profile and deck. Anonymous visitors have no access.
- Portraits are stored inside the private deck, not in public storage.
- Signed-in users can delete their account from Config → Account. That removes the auth user, profile and deck (`delete_my_account()`).
- Signing out removes the local copy of the deck from the device.
- `vercel.json` sends a strict Content-Security-Policy, HSTS, no framing, nosniff and a locked-down Permissions-Policy.

### Offline and multiple devices

The app works offline and keeps a local copy. When a device reconnects (or is reopened, or every 45 s while open) it does a three-way merge against the last version it synced: XP and credits from each device add up, tasks are matched by id so completions, edits, new tasks and deletions from every device are kept, and only a direct clash on the same field of the same task goes to the device syncing last. Writes use optimistic locking (`data->>sid`), so two devices saving at once never overwrite each other. A `//WARNING` line shows while a signed-in device has no connection.

Bot protection uses Cloudflare Turnstile in interaction-only mode, so most people never see a challenge. To turn it on: create a Turnstile widget at dash.cloudflare.com (mode: Invisible or Managed), put its **site key** in `config.js` as `turnstileSiteKey`, and put its **secret key** in Supabase under Authentication → Attack Protection → CAPTCHA (provider: Turnstile). Leave `turnstileSiteKey` empty to run without it.

Recommended dashboard settings: keep email confirmation on, set the minimum password length to 8, turn on leaked-password protection if your plan has it, and use a custom SMTP sender before inviting many users.

The privacy policy is `privacy.html` (English, Polish, Swedish). Set the contact address in its script before going public.

## Deploy

Import the repo at vercel.com/new. Framework preset: Other. No build command, output directory `.`.

## Sound

Short UI effects are synthesized live with the Web Audio API. The clips in `sfx/` were made by the project owner with an AI sound generator:

| File | Plays on |
|---|---|
| `complete_1-3.mp3` | Completing a task, rotated so the same one never plays twice in a row |
| `complete_heavy.mp3` | Completing a HEAVY task, and every 5th hit of a combo |
| `hack_complete.mp3` | Completing a care-hack task (a glitched remix of `complete_1`) |
| `ping.mp3` | Loot drops and achievements |
| `detected.mp3` | Pick for me locking a target |
| `levelup.mp3` | Level up |
| `heat.mp3` | An event starting |
| `ring.mp3` | The incoming call after a focus session (looped) |
| `jackin.mp3` | Starting a focus session |
| `boot.mp3` | The boot screen |
| `error.mp3` | Invalid actions |

Any missing file falls back to the synthesized version.
