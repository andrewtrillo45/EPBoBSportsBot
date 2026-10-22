# EPBoBSportsBot — Setup Guide

EPBoBSportsBot posts the newest gaming and sports news into your Discord. It runs free on GitHub's servers every 5 minutes, so nothing runs on your computer.

**What it covers**
- 🎮 **Gaming Info:** Call of Duty, Warzone, WARDOGS, Fortnite, FC 27, College Football 27, Madden
- 🏆 **Sports News:** NFL, CFB, NBA, MLB, NHL, WNBA, Tennis, NASCAR
- 🎮 **Gaming sources:** Call of Duty blog, CharlieIntel, Steam News, WARDOGS News, Fortnite.com, EA (FC, College Football, Madden), Operation Sports, CFB.FAN, Madden School, Google News
- 📰 **Sports sources:** ESPN, RotoWire, FantasyPros, The Athletic, AP Sports, RotoBaller, Underdog Network, CBS Sports, Fox Sports, MLB.com, Google News
- 📈 **Trending on Sleeper:** most added and dropped players, posted to #nfl and #nba every 8 hours

✅ Parts 1 and 2 (Discord) are already done on the EPBoB server. They're kept here for reference. Part 3 is what's left.

A computer is easier than a phone for Part 3.

---

## Part 1 — Discord: role and channels

### 1. Create the role
Server Settings → **Roles** → Create Role
- Name: `Sports and Gaming News`
- Leave every permission off. This role only unlocks channels.

### 2. Create the two categories
Make a category called **Gaming Info** with these text channels:
`call-of-duty` · `warzone` · `wardogs` · `fortnite` · `fc27` · `college-football-27` · `madden`

Make a category called **Sports News** with these text channels:
`nfl` · `cfb` · `nba` · `mlb` · `nhl` · `wnba` · `tennis` · `nascar`

### 3. Lock each category to the role
On each category, open Edit Category → **Permissions**:
- **@everyone:** View Channel ❌
- **Sports and Gaming News:** View Channel ✅, Send Messages ❌, Read Message History ✅
- Click **Sync** on the channels so they all copy the category's permissions.

People without the role never see these categories at all.

### 4. Let members turn it on or off themselves
Server Settings → **Onboarding**. This needs Community turned on: Server Settings → Enable Community.
- Add a question such as **"Want sports & gaming news?"**
- Add an answer **"Yes, show me the news"** that gives the `Sports and Gaming News` role.

New members get asked when they join. Anyone can change their choice later from **Channels & Roles** at the top of the channel list, which hides the news again whenever they want. You don't need an extra bot for this part.

---

## Part 2 — Discord: one webhook per channel

A webhook is how EPBoBSportsBot posts into a channel. Repeat these steps for all 15 channels:

1. Hover the channel → ⚙️ **Edit Channel** → **Integrations** → **Webhooks** → **New Webhook**
2. Name it `EPBoBSportsBot` and upload your logo as its picture
3. Click **Copy Webhook URL** and paste it somewhere private, labeled with the channel name

⚠️ Treat webhook links like passwords. Anyone who has one can post in that channel.

---

## Part 3 — GitHub: the free cloud that runs the bot

### 1. Make the repository
- Sign up at github.com (free).
- Click **New repository**, name it `EPBoBSportsBot`, and set it to **Public**.
  - Public repositories get unlimited free run time. Your webhook links stay hidden in step 3, so public is safe.

### 2. Upload the files
On the repo page, click **Add file → Upload files** and drag in:
`epbobsportsbot.py`, `feeds.yaml`, `requirements.txt`, `seen.json`, `README.md`

The workflow file lives in a folder that starts with a dot, which some uploads skip. To add it:
- Click **Add file → Create new file**
- Type the name exactly: `.github/workflows/news.yml`
- Paste in the contents of `news.yml` and click **Commit**

### 3. Add your webhook links as a secret
Go to repo **Settings → Secrets and variables → Actions → New repository secret**.
- Name: `WEBHOOKS`
- Value: the block below, with each link pasted in (keep the quotes and commas):

```json
{
  "call-of-duty": "PASTE_WEBHOOK_URL",
  "warzone": "PASTE_WEBHOOK_URL",
  "wardogs": "PASTE_WEBHOOK_URL",
  "fortnite": "PASTE_WEBHOOK_URL",
  "fc27": "PASTE_WEBHOOK_URL",
  "college-football-27": "PASTE_WEBHOOK_URL",
  "madden": "PASTE_WEBHOOK_URL",
  "nfl": "PASTE_WEBHOOK_URL",
  "cfb": "PASTE_WEBHOOK_URL",
  "nba": "PASTE_WEBHOOK_URL",
  "mlb": "PASTE_WEBHOOK_URL",
  "nhl": "PASTE_WEBHOOK_URL",
  "wnba": "PASTE_WEBHOOK_URL",
  "tennis": "PASTE_WEBHOOK_URL",
  "nascar": "PASTE_WEBHOOK_URL"
}
```

### 4. Turn it on and test it
- Open the **Actions** tab and allow workflows if GitHub asks.
- Click **EPBoBSportsBot → Run workflow**.
- On the first run, each channel gets just **one** story, so your server isn't flooded with old news. After that, new stories post every 5 minutes, with at most 4 per channel each run.

---

## Changing things later
- **Add or remove a news source:** edit `feeds.yaml` right on GitHub (click the ✏️ pencil icon).
- **Add a new game or sport:** add a channel block to `feeds.yaml`, make the Discord channel and webhook, then add that name and link to the `WEBHOOKS` secret.
- **Post more or fewer stories:** change `max_posts_per_channel_per_run` in `feeds.yaml`.
- **Pause the bot:** Actions tab → EPBoBSportsBot → ⋯ → **Disable workflow**.

## Good to know
- GitHub sometimes runs scheduled jobs a few minutes late. That's normal.
- If one news site is down or blocks the bot, the others keep posting. Problems show up in the run log on the Actions tab.
- Sleeper's player news stories stay inside its app, so the bot posts Sleeper's trending players instead (change how often with `every_hours` in `feeds.yaml`). Sleeper keeps its player news inside its app, and X (Underdog, ESPN on X) charges for API access, so the bot can't read those. Fox Sports, AP, RotoBaller, and Underdog Network come in through Google News. Underdog's site posts rarely, so don't expect much from it.
- RotoWire posts a lot of player news. If the NFL or NBA channels get too busy, delete the RotoWire lines in `feeds.yaml`.
- `sleeper_players.json` appears after the first run. It's a saved list of Sleeper player names so the bot doesn't re-download it every time.
- `seen.json` is the bot's memory of what it already posted. Don't delete it unless you want a fresh start.
