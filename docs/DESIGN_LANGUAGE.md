# ChainSentinel design language: "Case file"

Research date: 24 Oct 2026. Raw data in this folder:
- `rea/*.inspect.json`, `rea/*.shot.json`: REA (`rea-agents` 6.7.0) `inspect-web-page` + `capture-web-screenshot` over CDP (headless Chrome 156). Decoded viewports: `shots/rea_*.png`.
- `computed_tokens.json` + `shots/<site>.png`, `shots/<site>_scroll.png`: `tokens.py`, a Playwright pass reading computed styles (REA observes structure, scripts and network but does not report computed CSS).
- Arkham (arkm.com) and Breadcrumbs served a Cloudflare "Just a moment..." challenge to both tools, so no tokens were taken from them.

## What each reference contributed
| Site | Observed | Taken |
|---|---|---|
| Elliptic | Ink `#131b1f` on `#f5f5f5`, Poppins, radii 5–10px, single lime signal `#d2fb7a`, easing `cubic-bezier(.65,0,.35,1)` 0.4s | A near-black ink with one bright signal colour; a compliance product can be calm and confident |
| Chainalysis | Institutional navy `#293972` text and fills, `#f4f6fa` washes, 1px `#d1d3e0` borders, 12px cards | Navy as the "authority" ink for interactive and selected states, not a neon accent |
| Nansen | Dark `#06080b`, Inter + a mono (IBM Plex Mono, Fragment Mono) for data, big negative tracking on headings | Mono reserved for addresses, amounts and hashes; tight tracking on large numerals |
| Linear | 12–14px UI text, Inter + Berkeley Mono, 1px `rgba(255,255,255,.08)` hairlines, 4–8px radii, 100–160ms `cubic-bezier(.25,.46,.45,.94)` | Density (13px UI, 28px rows), hairlines instead of shadows, fast UI transitions |
| Stripe Radar | `sohne` light 300 headings, slate `#50617a` secondary text, `#e5edf5` 1px borders, 2–6px radii, reveals 0.3s `cubic-bezier(.25,1,.5,1)` | Thin borders, small radii, slate secondary text, the soft reveal curve for result cards |
| PostHog | Warm paper `#eeefe9` / `#fdfdf8`, IBM Plex Sans + Source Code Pro, `#bfc1b7` borders, 4px radii, no shadows | IBM Plex family, borders over shadows, a product with personality instead of a template (we kept the paper idea but neutral, not cream) |

## Direction
A light **forensic case file**: neutral report paper (deliberately not the warm cream that has become its own AI cliché), black ink, hairline rules, a serif for headings and the verdict stamp, mono for the evidence. It reads like a compliance report an analyst would print and sign, which is what the tool produces. It avoids the AI-template look (dark graphite, glass, a blue glow, Geist/Inter, rounded cards everywhere).

## Tokens
**Type** (all SIL OFL 1.1, bundled in `static/vendor/fonts/`)
- Headings and the verdict stamp: **Source Serif 4** (variable, optical size), 600, tracking -0.01em. Page title 30px, section 19px, verdict 34px.
- UI and body: **IBM Plex Sans** 400/500/600. Body 13.5px/1.5, UI 13px, small 12px, table headers 11px uppercase with +0.05em tracking.
- Data: **IBM Plex Mono** 400/500 for addresses, amounts, hashes, rule codes, probabilities. Tabular figures everywhere.

**Colour roles**
| Role | Token | Value |
|---|---|---|
| Paper (app ground) | `--bg` | `#f2f3f3` |
| Sheet (panels) | `--s1` | `#ffffff` |
| Sunk (wells, bars) | `--s2` | `#e9eaea` |
| Hairline | `--line` | `#dadbdb` |
| Strong rule | `--line2` | `#c4c6c7` |
| Ink | `--fg` | `#16181c` |
| Ink 2 | `--fg2` | `#3f444b` |
| Muted (≥4.5:1 on paper) | `--mut` | `#646973` |
| Authority (interactive, selected, flow) | `--acc` | `#1f3d8a` |
| Flag | `--flag` | `#b42318` on `#fbe8e5` |
| Review | `--rev` | `#965a00` on `#fbf0d9` |
| Clear | `--clr` | `#11744a` on `#e2f2e8` |
| Synthetic (hatched) | `--syn` | `#5a3fc0` |
| Sapling (model output) | `--sap` | `#0e5e63` |

**Shape and space**: 4px base grid (4, 8, 12, 16, 24, 32). Radii 3px controls, 4px panels, 2px chips. 1px borders; shadows only on floating layers (`0 4px 12px -2px #0002`). Table rows 30px, panel padding 14–16px.

**Graph**: plain near-white ground `#fbfbfb` (no decorative grid), ink nodes, hollow grey unlabelled wallets, slate edges `#9a9587`, authority-navy highlight and particles, serif-free mono labels on paper chips.

**Motion**: UI state 120ms `cubic-bezier(.25,.46,.45,.94)`; result reveals 320ms `cubic-bezier(.25,1,.5,1)`; probability bars 800ms `cubic-bezier(.165,.84,.44,1)`; graph entry staggered ≤22ms per node. All off under `prefers-reduced-motion`.

## Rules for the UI
- Plain English first, technical term second: every rule, label and score has a plain sentence; jargon (OFAC, mixer, peel chain, Sapling, P(violation)) has a dotted underline with a hover definition.
- Technical detail is one click away behind "Show details", never removed.
- Banyan Sapling is the decision-maker and gets the hero panel; our rules are labelled "evidence".
- REAL / SYNTHETIC / SIMULATED tags stay on every wallet.
- No copied code, logos, illustrations or layouts from the references; only these abstract tokens.

## Detector pass
The impeccable anti-pattern detector flagged a cream page background, a side-tab accent border and a decorative grid background on the first pass. All three were removed (neutral paper, full 1px border, plain graph ground). The remaining advisory, hatched stripes, is kept on purpose: hatching is the code for SYNTHETIC data everywhere in the app.
