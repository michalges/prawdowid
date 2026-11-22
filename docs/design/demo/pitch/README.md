# Pitch video

`../pitch.mp4`: a ~47 s horizontal (1920x1080) pitch in TikTok style that shows the four channels in order, each with
its own case: web UI (misleading), Discord bot (confirmed), Chrome extension (not enough evidence) and the Android app
(false via the text-selection menu, confirmed via the Share menu). It has no audio track.

Every result comes from the real API. The Android footage is the Expo web build of `mobile/` inside a phone frame. The
Android Share sheet and text-selection menu, the Discord chat, the browser window and the article/feed pages around the
apps are animated HTML mock-ups (`*_stage.html`). The Discord embeds come from the bot's own `render.py`.

```bash
# web dev server on :5173 + API on :8000; extension built (pnpm build in channels/chrome_extension)
cd mobile && EXPO_PUBLIC_API_URL=http://localhost:5173 pnpm exec expo start --web --port 8081   # separate shell
cd backend
uv run --with playwright python ../docs/design/demo/pitch/record_desktop.py <clips_dir>
uv run --with playwright python ../docs/design/demo/pitch/record_android.py <clips_dir>
uv run --with playwright python ../docs/design/demo/pitch/make_pitch.py <clips_dir> ../docs/design/demo/pitch.mp4
```
