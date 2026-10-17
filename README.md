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

All sounds are synthesized for RunDeck. Short effects are generated live with the Web Audio API; six clips in `sfx/` are rendered by `tools/gen_sfx.py` in a dark neuro-bass style: a growl hit for task complete, a double wub with a drop for heavy tasks, a metallic ping, a growl riser for detection, an alarm over a pulsing reese, and a wobble-bass ringtone:

```
python3 tools/gen_sfx.py sfx
```

It needs numpy, scipy and ffmpeg.
