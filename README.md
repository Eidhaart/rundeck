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

The anon key is meant to be public. Access is enforced by the policies in `schema.sql`: each user reads and writes only their own deck and portrait folder. Profiles (handle, portrait, level) are readable by signed-in users, ready for leaderboards later.

## Deploy

Import the repo at vercel.com/new. Framework preset: Other. No build command, output directory `.`.

## Sound

Short UI effects are synthesized live with the Web Audio API. The clips in `sfx/` were made by the project owner with an AI sound generator:

| File | Plays on |
|---|---|
| `complete_1-3.mp3` | Completing a task, rotated so the same one never plays twice in a row |
| `complete_heavy.mp3` | Completing a HEAVY task, and every 5th hit of a combo |
| `ping.mp3` | Loot drops and achievements |
| `detected.mp3` | Pick for me locking a target |
| `levelup.mp3` | Level up |
| `heat.mp3` | An event starting |
| `ring.mp3` | The incoming call after a focus session (looped) |
| `jackin.mp3` | Starting a focus session |
| `boot.mp3` | The boot screen |
| `error.mp3` | Invalid actions |

Any missing file falls back to the synthesized version.
