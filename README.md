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

## Sound files

The app layers four short clips over its synthesized effects: `notify` (task complete, loot, achievements), `detect` (target lock, level up), `heat` (event start) and `call` (end of a focus session). They are loaded from `sounds/notify.mp3`, `sounds/detect.mp3`, `sounds/heat.mp3` and `sounds/call.mp3`. That folder is git-ignored because the clips are not ours to redistribute; without it the app uses its synthesized sounds.
