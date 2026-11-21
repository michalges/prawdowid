# DESIGN.md: Prawdowid visual foundations

> For every agent building UI (web, mobile, Discord embeds, demo chat). This file defines **tokens and rules, not screens**: layouts, components and flows are yours to design, as long as they use these tokens and follow the rules below. CONCEPT.md wins on behaviour (what must be shown); this file wins on how it looks.

**Token files (keep them in sync):**
- [`design/tokens.json`](design/tokens.json): source of truth. Import it in the Expo app and anywhere TS needs values (Discord colours included).
- [`design/tokens.css`](design/tokens.css): the same tokens as a Tailwind v4 `@theme` block for `web/`. Classes come out as `bg-brand-600`, `text-ink-muted`, `bg-verdict-true-bg`, `font-serif`, `text-quote`, `rounded-lg`, `shadow-card`.

Never hard-code a hex value, font stack or radius in components. If a value is missing, add a token to both files first.

---

## 1. Direction

White-first and calm, with one confident red (the Polish flag's crimson) for identity and action. The product must look trustworthy and official without looking bureaucratic. Theme: light only for now.

## 2. Rules that matter (from CONCEPT)

1. **Red means "act", never "false".** `brand-600` is for the logo, links, focus rings and the **one primary action per screen** (usually "Sprawdź"). Never colour a verdict, an error or a warning with brand red.
2. **Sources and interpretation never mix (CONCEPT §7.2).** "Co mówią źródła" and "Interpretacja Prawdowida" must be visibly separate. The typographic rule that enforces it everywhere: **verbatim quotes use the `serif` family (`quote` style); everything Prawdowid writes uses `sans`.** Metadata (domains, dates, tiers, corpus version, model) uses `mono` (`meta` style).
3. **Verdicts are label + icon + colour, never colour alone.** Each verdict has a `fg`/`bg` pair and needs a distinct icon shape so it survives greyscale and colour blindness.
4. **Abstaining is a result, not an error.** `brak_wystarczajacych_dowodow` uses calm slate. Never style it as disabled, faded or failed.
5. **Technical statuses are not verdicts (CONCEPT §7.4).** `technical_error`, `rate_limited`, `needs_clarification`, `out_of_scope` use the `system` blue pair, replace the result instead of sitting beside a verdict, and never show a verdict colour.
6. **No "truth score".** Strength (wysoka / średnia / niska) is shown in neutral `ink`, not in verdict colours, with its factors visible.
7. **Handoff states differ visibly (CONCEPT §9.3).** "Zalecamy przekazanie" is neutral (slate); "Przekazano moderatorowi" is green (`verdict.potwierdzone`) and only after confirmed delivery.

## 3. Colour

| Token | Hex | Use |
|---|---|---|
| `brand-600` | `#d4213d` | Primary button fill, links, focus ring, logo. White text on it: 5.1:1 |
| `brand-700` | `#b01a33` | Hover; link text on white (6.9:1) |
| `brand-800` | `#8c1428` | Pressed; brand text on `brand-50` |
| `brand-50` / `brand-100` | `#fdf0f2` / `#fbd9df` | Selected/hover tints, subtle brand outlines |
| `surface` | `#ffffff` | Page and cards |
| `surface-subtle` | `#f6f6f8` | Sources block, input wells, secondary areas |
| `surface-sunken` | `#eceef1` | Skeletons, disabled fills |
| `border` | `#e3e4e8` | Decorative hairlines and dividers |
| `border-control` | `#858b97` | Input/checkbox/secondary button borders (3.4:1) |
| `ink` | `#16181d` | Main text |
| `ink-muted` | `#4d5360` | Secondary text |
| `ink-subtle` | `#6b7180` | Dates, counters. The lightest allowed text colour |
| `system` / `system-bg` | `#1f5fae` / `#eaf2fb` | Technical statuses, neutral context notices (incident match) |
| `warning` / `warning-bg` | `#8a5300` / `#fdf2d8` | Source status, archival material, missing context |

**Verdicts** (`fg` on `bg`, all ≥ 5.5:1):

| API value | Label (PL) | fg | bg | Suggested icon |
|---|---|---|---|---|
| `potwierdzone` | Potwierdzone | `#0b6e4f` | `#e7f4ee` | circle + check |
| `falszywe` | Fałszywe | `#8a1538` | `#fbe9ee` | circle + ✕ |
| `wprowadzajace_w_blad` | Wprowadzające w błąd | `#8a5300` | `#fdf2d8` | triangle + ! |
| `brak_wystarczajacych_dowodow` | Brak wystarczających dowodów | `#475467` | `#eef0f3` | dashed circle + dash |
| `nie_podlega_weryfikacji` | Nie podlega weryfikacji | `#4a4594` | `#eeedf8` | speech bubble |

`falszywe` is a dark wine, deliberately darker and cooler than `brand-600`, so a false verdict never reads as a button.

## 4. Typography

Families (all SIL OFL 1.1, so they're fine for the rights transfer to MSZ, and all cover Polish diacritics):
- `sans`: **IBM Plex Sans**, the interface and all of Prawdowid's own words
- `serif`: **Source Serif 4** italic, verbatim source quotes only, in Polish quotation marks „…”
- `mono`: **IBM Plex Mono**, metadata only

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| `display` | 40 / 44 | 600 | Landing hero only |
| `title` | 28 / 34 | 600 | Page titles |
| `heading` | 20 / 28 | 600 | Section headings, claim text |
| `body` | 16 / 24 | 400 | Explanations. **Never smaller for verdict copy** |
| `body-sm` | 14 / 20 | 400 | Helper text, notices |
| `label` | 13 / 16 | 600 | Badges, tabs, small labels |
| `quote` | 17 / 27 | 400 italic, serif | Citation quotes |
| `meta` | 12 / 16 | 400, mono | Domains, dates, tiers, model info |

**Fonts.** Web: add the Google Fonts `<link>` to `web/index.html` (`IBM Plex Sans` 400/500/600/700, `IBM Plex Mono` 400/500, `Source Serif 4` 400 + 400 italic), or self-host the woff2 files. Mobile: `@expo-google-fonts/ibm-plex-sans`, `@expo-google-fonts/ibm-plex-mono`, `@expo-google-fonts/source-serif-4`. Respect system font scaling on mobile.

## 5. Space, shape, elevation

- Spacing: 4px base (`space` 1, 2, 3, 4, 6, 8, 12 = 4…48px). Tailwind's default scale matches.
- Radius: `sm` 4 (badges, chips) · `md` 8 (buttons, inputs, notices) · `lg` 12 (cards, blocks) · `pill` (tabs, meters).
- Structure comes from `border` hairlines and the `surface-subtle` grey; `shadow-card` is a whisper. No heavy shadows.
- Focus: 2px `brand-600` outline with offset, or `brand-600` border + `shadow-focus` on inputs. Always visible on keyboard focus.

## 6. Accessibility (WCAG AA, brief usability 15%)

- Text ≥ 4.5:1 against its background; large text, icons, control borders and focus rings ≥ 3:1. Every token pair above already passes; don't introduce lighter greys than `ink-subtle`.
- Touch targets ≥ 44px (`size.touchTarget`).
- Verdicts, statuses and strength need text labels (`aria-label` where shown only graphically).
- Asynchronous results/statuses: `role="status"` / `aria-live="polite"`.
- Plain Polish, B1 level, short sentences (CONCEPT §14).

## 7. Voice

Calm, precise, humble. Explain, don't scold ("Źródła urzędowe tego nie potwierdzają", not "To kłamstwo!"). Buttons are verbs: "Sprawdź", "Pokaż źródła", "Usuń moje dane", "Pokaż w przeglądarce". Technical errors end with "To nie jest ocena prawdziwości." Dates in metadata are ISO (`2026-10-02`); in sentences, words ("2 października 2026 r.").

## 8. Per channel

- **Web (`web/`, Tailwind v4):** import `docs/design/tokens.css` (copy it or `@import` it after `@import "tailwindcss";`).
- **Mobile (`mobile/`, Expo):** read values from `docs/design/tokens.json` (copy it into `mobile/src/theme/` if the bundler can't reach `docs/`). Same rules and strings as the web.
- **Discord:** embed colour = `discord.<verdict>` from `tokens.json` (`discord.system` for technical statuses, `discord.brand` for neutral bot messages). Keep the two-block separation as separate embed fields.
- **Demo chat:** same tokens as the web.

## 9. Logo

The mark is **"Oko na krzyżu"**: an eye at the centre of the four directions, a nod to Światowid, who sees in every direction (many sources, one answer). The red ray points up; the pupil is red.

| File | Use |
|---|---|
| [`design/logo/prawdowid-mark.svg`](design/logo/prawdowid-mark.svg) | The mark on white or light surfaces: header, about page, Discord bot avatar on light, docs. Next to the wordmark "Prawdowid" (IBM Plex Sans Bold, `ink`), mark height ≈ 1.4× the cap height, gap `space-2`. |
| [`design/logo/prawdowid-app-icon.svg`](design/logo/prawdowid-app-icon.svg) | The mark reversed on a `brand-600` rounded tile: favicon, Expo app icon/splash, PWA icons, Discord bot avatar. |
| [`design/logo/discord/`](design/logo/discord/) | Discord bot: `avatar-1024.png` / `avatar-512.png` (full-bleed red square, mark sized for Discord's circle crop; source `avatar.svg`) and `banner-1360x480.png` (profile banner, 680×240 @2x). Upload in the Discord Developer Portal. |

Rules:
- Use the files as they are: don't recolour, stretch, rotate, outline or add effects. Colours are `brand-600` `#d4213d`, `ink` `#16181d` and white.
- Clear space around the mark ≥ ¼ of its width. Minimum size 16px (the app icon is the favicon).
- In React, inline the SVG (or import it as a component) so it stays crisp; give it `aria-hidden` when the wordmark text is next to it, otherwise `aria-label="Prawdowid"`.
- For raster formats (Expo `icon.png` 1024px, Android adaptive icon, `apple-touch-icon` 180px), export from the SVG; don't redraw.
- Don't invent other logo artwork.
