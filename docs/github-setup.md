# GitHub repository setup

Everything the repo needs before its first push, and why. The `hacs` CI job validates
repository *metadata*, not just files, so a correct codebase in a bare repo still fails.

Source for the check list: <https://www.hacs.xyz/docs/publish/action/>

## 1. Repository description

Settings → General → Description. Paste verbatim:

```
Apple-inspired glass and frosted glass themes for Home Assistant. Twelve variants with real native backdrop blur, WCAG AA verified contrast, and no-blur Lite editions for older tablets. HACS-installable.
```

201 characters (GitHub's limit is 350). Satisfies the HACS **description** check.

## 2. Topics

Settings → General → Topics, or the ⚙ next to "About" on the repo home page. Add all of
these (GitHub allows 20; these are 14):

```
home-assistant
homeassistant
hacs
theme
themes
home-assistant-theme
lovelace
frontend
glassmorphism
frosted-glass
apple
ios
dark-mode
accessibility
```

Satisfies the HACS **topics** check. The first four matter most for discoverability inside
HACS and GitHub search; the rest are for humans browsing.

## 3. Repository settings

| Setting | Value | Why |
|---|---|---|
| Issues | **Enabled** | HACS **issues** check requires it |
| Archived | **No** | HACS **archived** check fails on archived repos |
| Default branch | `main` | CI triggers on pushes to `main` |
| Visibility | Public | HACS cannot install from a private repo |

## 4. What is already satisfied by the code

| Check | Satisfied by |
|---|---|
| **hacsjson** | `hacs.json` at the repo root |
| **information** | `README.md` at the repo root |

## 5. Known gap: the `images` check

The HACS **images** check requires the information file (`README.md`) to embed images.
The README currently has none, because no screenshots exist — the theme has never been
rendered in a real Home Assistant instance.

`.github/workflows/ci.yml` therefore passes `ignore: "images"` to the HACS action, with a
TODO. **Once you have screenshots:**

1. Add them to the README (a light and a dark shot, ideally one Glass and one Frosted).
2. Delete the `ignore:` line and its TODO comment from the `hacs` job.
3. Confirm CI still passes.

Screenshots are also required if you ever submit this to the HACS default store.

## 6. The `brands` check

The HACS action also runs a **brands** check ("checks if there are brand assets
available"). Brand assets live in `home-assistant/brands` and are keyed by integration
domain; a theme has no domain, so this check is expected either to be skipped for
`category: theme` or to pass trivially.

This is **not confirmed** — the published docs do not say which checks apply to which
category. If the first CI run fails on `brands`, the one-line fix is to extend the
existing ignore:

```yaml
          ignore: "images brands"
```

## 7. Remotes and mirroring

`origin` is the self-hosted GitLab at `server.lan`, which **push-mirrors to**
<https://github.com/OozoraHaruto/hass-glass-theme>. So the normal flow is:

```bash
git push origin main      # GitLab -> mirrored to GitHub -> Actions run there
```

No second GitHub remote is needed. GitHub Actions fire on mirrored pushes because a mirror
is an ordinary git push.

Do steps 1–3 **before** the first push, or the `hacs` job fails on its first run.

### Two things to verify in the mirror configuration

1. **Tags must be mirrored.** `.github/workflows/release.yml` triggers on `v*` tags. GitLab's
   *"Mirror only protected branches"* option excludes tags, which would silently mean
   releases never build. Either leave that option off, or push tags to GitHub directly.
2. **The mirror is one-way and force-updates.** Anything committed on GitHub — a merged PR,
   a README edit through the web UI — is overwritten on the next mirror run. Treat GitLab as
   the source of truth and never commit on the GitHub side.

If you ever need to push straight to GitHub as well:

```bash
git remote add github git@github.com:OozoraHaruto/hass-glass-theme.git
git push github main
```

## 8. Cutting a release

Releases are optional for HACS (it falls back to the default branch), but they give users
a versioned update path and a pinnable rollback:

```bash
git tag v0.1.0
git push origin v0.1.0
```

`.github/workflows/release.yml` then re-runs the drift check and the test suite against the
tagged tree, zips `themes/glass.yaml`, and publishes a GitHub Release with generated notes.
It will not publish if either check fails.

## 9. Installing it in Home Assistant

HACS → three-dot menu → Custom repositories → add

```
https://github.com/OozoraHaruto/hass-glass-theme
```

with category **Theme**. (HACS reads from GitHub, not GitLab — which is what the mirror is
for.) Then in `configuration.yaml`:

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

Restart Home Assistant, then pick a theme in your user profile.
