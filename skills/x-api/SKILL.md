---
name: x-api
description: Use when composing X (Twitter) posts, writing post copy, building or adapting diagrams/images for X, or troubleshooting X API issues. Provides X API v2 conventions, attractive/readable post-writing rules (hook, length, formatting), X-native diagram guidance (strip carousel artifacts, aspect ratios, center-crop), and content guidelines.
---

# X API Knowledge

## Post Creation

X API v2 endpoint for creating posts:
```
POST https://api.x.com/2/tweets
Authorization: Bearer {access_token}
Content-Type: application/json

{"text": "Hello world"}
```

### With media:
```json
{
  "text": "Check this out",
  "media": {
    "media_ids": ["1234567890"]
  }
}
```

## Authentication

X uses **OAuth 2.0 with PKCE** (Proof Key for Code Exchange):
- Authorization URL: `https://x.com/i/oauth2/authorize`
- Token URL: `https://api.x.com/2/oauth2/token`
- Access tokens expire in **2 hours**
- Refresh tokens valid for **6 months** (requires `offline.access` scope)
- The plugin auto-refreshes tokens before each API call

Required scopes: `tweet.read tweet.write users.read media.write offline.access`

## Media Upload

Single-shot upload to `POST https://api.x.com/2/media/upload`:
- Format: `multipart/form-data`
- Fields: `media_data` (base64), `media_category` ("tweet_image")
- Returns `data.id` (media ID string)

### Constraints
- Max 4 images per post
- Images: max 5 MB (JPG, PNG, GIF, WEBP)
- GIFs: max 15 MB, resolution max 1280x1080
- Videos: max 512 MB, 0.5-140 seconds (requires chunked upload)

## Post Content Guidelines

- Free tier: **280 characters** per post
- Premium/X Blue: **25,000 characters**
- Hashtags: use sparingly, 2-3 max
- @mentions count toward character limit
- URLs are shortened to 23 characters by t.co
- Line breaks are preserved

## Writing an attractive, readable post (ALWAYS craft, never dump raw text)

Every time you compose for X, deliberately write the post for the platform. Do NOT paste
an article abstract or a LinkedIn body verbatim. Source material (a WeChat article, a
LinkedIn post) is INPUT to be re-cut for X, not the post itself. Re-cut it every time.

**Hook the first line.** The opening line is the post: it is what shows in-feed and decides
the scroll-stop. Lead with one of: a surprising/specific stat, a bold claim, a provocative
question, or a concrete value proposition. Put the most counterintuitive fact first. Never
open with throat-clearing ("In this post I want to talk about...").

**Length.** The engagement sweet spot is short: ~71-100 chars wins on pure engagement, and
keeping the whole post scannable (well under the 280 free-tier cap) reads better on mobile,
where most of the audience is. Premium can post long-form, but the 2026 algorithm now favors
a single self-contained post over a multi-tweet thread for distribution, so prefer ONE tight,
complete post + images over a thread unless the user explicitly wants a thread. Earn the read
with the hook, let the diagrams carry the depth.

**Format for mobile.** Use line breaks liberally: one idea per line, a blank line between
ideas. A wall of text is a scroll-past. One claim per line beats a dense paragraph.

**Hashtags.** 3 or fewer, relevant, at the end. More reads as spam and dilutes reach.

**Native media beats links.** Images uploaded directly to X get materially more engagement
than the same content behind a link, and the algorithm rewards time-on-post (dwell). A strong
diagram set is the single biggest readability lever an X post has. Always prefer attaching
rendered images over linking out.

**Honesty.** Mirror whatever claim-framing the source settled on (e.g. "clock wins,
throughput ties" stays a tie, not a "win"). Do not inflate a tie into a victory for a punchier
hook.

## Diagrams for X posts (X-NATIVE, never reuse carousel slides as-is)

When a post carries diagrams, draw or adapt them to be X-native. Re-using slides authored for
another channel (a LinkedIn carousel, a WeChat article) without editing is a recognizable
tell and reads as repurposed. ALWAYS produce an X-specific image set.

Build them with the `svg-diagram` skill (edit the SVG source, the source of truth, then
render PNG). Re-cut from the source diagrams every time.

**Strip carousel / sequence artifacts.** These make no sense on X and signal repurposing:
- Page numbers (`3 / 8`, `5 / 8`) - X shows images as a simultaneous gallery, not numbered slides.
- Swipe prompts (`swipe →`, `→ next`) - there is nothing to swipe TO in the same sense.
- "Slide N", deck footers tied to sequence position.
- Audit before render: `grep -lE 'swipe|/ [0-9]|slide' images/*.svg` should be empty.

**Keep key content centered.** X crops multi-image previews from the center outward in the
timeline (the full image shows on tap). Keep headline numbers, titles, and the load-bearing
visual in the middle third; never park a critical label at an edge where the in-feed crop
clips it.

**Use ONE consistent aspect ratio for every image in a post.** Mixing landscape and portrait
in the same post produces unpredictable cropping. Pick one and apply it to all:
- Square `1080 x 1080` (1:1) - safe, dense, reads well in the 2x2 / side-by-side gallery. Good default for technical diagram sets.
- Landscape `1600 x 900` (16:9) - largest single-image preview, no crop on desktop or mobile.
- Vertical `1080 x 1350` (4:5) - maximum mobile feed real estate for a single hero image.

**How X lays out N images (you do not choose the layout):** 1 = full preview; 2 = side by
side (~2:1 each); 3 = one large left + two stacked right; 4 = 2x2 grid. Each tile is
center-cropped. Order the images to read as a sequence anyway (cover -> problem -> mechanism
-> result) since the gallery and the tap-through both present them in upload order.

**Render + verify** (per `svg-diagram`):
```bash
rsvg-convert -z 2 -b white diagram.svg -o diagram.png   # -b white is mandatory
```
Each PNG must be < 5 MB (JPG/PNG/GIF/WEBP). Save the X-native set to its own directory
(e.g. `docs/x/<slug>/images/`) so it is reusable and not confused with the carousel source.

## Free Tier Limits

- 1,500 posts per month
- Primarily write-oriented: cannot read other users' timelines or search broadly
- CAN read engagement metrics for YOUR OWN posts via `GET /2/tweets/:id` (verified working on the free tier with `public_metrics`, and even `non_public_metrics` / `organic_metrics`). Use `get-metrics` (below).
- Media upload available with `media.write` scope
- Rate limit: measured in 24-hour windows

## Reading post metrics / engagement

Use the `get-metrics` command to check how a post is doing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x-api.py get-metrics <tweet_id>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x-api.py get-metrics <tweet_id> --detailed
```

- Public metrics returned: `LIKES`, `REPOSTS`, `QUOTES`, `REPLIES`, `BOOKMARKS`, and `IMPRESSIONS` (impressions appear only for the authenticated user's own posts).
- `--detailed` also requests `non_public_metrics` + `organic_metrics` (profile clicks, engagements). These need the post to be your own and recent; on an insufficient access tier the command logs a NOTE and falls back to public metrics only instead of failing.
- Endpoint: `GET /2/tweets/:id?tweet.fields=public_metrics,created_at[,non_public_metrics,organic_metrics]`.
- A `403` means the app's access tier cannot read metrics (upgrade to Basic with `tweet.read` + `users.read`); the command prints a tier-aware hint. `404` = deleted/protected/wrong ID.
- Engagement needs HOURS to accumulate. Checking immediately after posting will read near-zero; wait before drawing conclusions.

## Common Errors

- **401 Unauthorized**: Token expired. The plugin auto-refreshes, but if refresh fails, re-run `/x:setup`.
- **403 Forbidden**: Missing required scope or app permissions. Check User Authentication Settings in the developer portal.
- **429 Too Many Requests**: Rate limited. Wait and retry.
- **400 Bad Request**: Invalid payload. Check character count and media IDs.

## Reply and Quote Posts

### Reply:
```json
{
  "text": "Great point!",
  "reply": {"in_reply_to_tweet_id": "1234567890"}
}
```

### Quote:
```json
{
  "text": "This is interesting",
  "quote_tweet_id": "1234567890"
}
```

## Scripts Location

The X API scripts are at `${CLAUDE_PLUGIN_ROOT}/scripts/`:
- `oauth-server.py` - OAuth 2.0 PKCE flow with local callback server and auto token refresh
- `x-api.py` - Post creation, media upload, auth check, token refresh, and `get-metrics` (engagement)
