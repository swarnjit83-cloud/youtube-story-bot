# YouTube Hindi studio

Our own cartoon studio plus an upload robot for **three separate YouTube channels** (see `channels.json`):

| Channel | What it makes | Days (UTC) | Made for Kids |
|---|---|---|---|
| `kids` | Hindi learning lessons for ages 2-5 (letters, numbers, colours, animals...) | Mon, Wed, Fri | yes |
| `stories` | Fictional cartoon stories with a recurring cast | Tue, Sat | yes |
| `explainers` | Money / rights / how-things-work videos (fact-checked) | Thu | no |

Every episode also gets 3 Shorts. Everything is uploaded **private**; you review it in YouTube Studio and press Publish.

## How it is built
- `toon.py` is our own 2D cartoon engine (consistent vector characters, blinking, lip-sync, backgrounds, lesson cards).
- `studio.py` writes the script (Claude), checks it, makes the voices (Hindi text-to-speech), renders the scenes and uploads.
- `cast.json` holds the characters and their voices; `channels.json` holds the channels and schedule.
- `.github/workflows/weekly-video.yml` runs it every day; a channel only runs on its own days.

## Secrets (GitHub: Settings, Secrets and variables, Actions)
`ANTHROPIC_API_KEY`, and one login token per channel: `YT_TOKEN_KIDS`, `YT_TOKEN_STORIES`, `YT_TOKEN_EXPLAINERS`.
(The older `YT_TOKEN` is used for `stories` until `YT_TOKEN_STORIES` exists.) A channel without a token is skipped.

## Add a channel's login (once per channel)
1. Create the channel on YouTube (use a Brand Account channel, so each channel has its own login).
2. On your computer, in this folder with `client_secret.json`: `python pipeline.py login --token token_kids.json`
3. In the browser, pick the Google account and **the channel** the videos should go to.
4. Copy the contents of the new token file into the matching GitHub secret.

Renaming a channel later does not affect the login.

## Useful commands
    python studio.py run kids          # make and upload one channel now (private)
    python story.py preview            # old picture preview (kept for reference)

YouTube keeps API uploads private until the Google Cloud project passes its audit, so each video needs your tap on Publish.
Fictional and children's content only uses our own drawn characters; never use real people's footage, voices or likenesses.
