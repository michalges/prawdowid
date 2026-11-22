# Prawdowid: Android app

Expo (SDK 58) / React Native app. A thin client of `POST /v1/checks` (channel `mobile`) with no verification logic,
LLM keys or source collection on the device (CONCEPT §7.6).

Entry points, all ending on the same confirmation screen (nothing is sent until the user taps "Sprawdź"):

- **In-app:** paste text or a link, or pick a screenshot from the gallery.
- **Share menu ("Udostępnij → Prawdowid"):** `ACTION_SEND` for `text/plain` and `image/*`. Browser shares of
  "title + link" are reduced to the link.
- **Text-selection menu ("Sprawdź w Prawdowidzie"):** `ACTION_PROCESS_TEXT`, from any app that supports it.

Shared images are copied into the app cache natively, then resized/compressed on-device to fit the 5 MB API limit.

## Layout

- `src/app/`: Expo Router screens: `index` (input + confirmation), `wynik/[checkId]`, `historia`, `ustawienia`.
- `modules/share-intent/`: local Expo module (Kotlin) that turns share / process-text intents into JS payloads
  (`getInitialShare()` for cold start, `onShare` event for warm start).
- `plugins/withAndroidShareIntents.js`: config plugin that adds the intent filters to `MainActivity`.

`android/` is generated (`pnpm prebuild`) and not committed.

## Run

Needs an Android SDK (`ANDROID_HOME`) and an emulator or device.

```bash
pnpm install
pnpm android                       # expo run:android: builds a dev client, starts Metro
EXPO_PUBLIC_API_URL=https://prawdowid.example pnpm android   # another server
```

The default server is `http://10.0.2.2:5173` (the web dev server on the host, seen from the Android emulator).
It can be changed in "Ustawienia". Cleartext HTTP is only enabled when the build-time URL is `http://`.

Test the share entry points from a shell:

```bash
adb shell am start -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT "Od 2026 roku Polacy potrzebują ETIAS" pl.prawdowid.app
adb shell am start -a android.intent.action.PROCESS_TEXT -t text/plain --es android.intent.extra.PROCESS_TEXT "Od 2026 roku Polacy potrzebują ETIAS" pl.prawdowid.app
```

Checks: `pnpm types:check`, `pnpm lint`, `pnpm format:check`, `pnpm doctor`.
