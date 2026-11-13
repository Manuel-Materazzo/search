---
name: searxng-fork-sync
description: Updates our SearXNG fork with the latest commits from the upstream repo by creating a new branch from upstream/master and re-applying our custom patches (docker, branding, translations, workflows, core fixes, theme modularity, simple theme, modern theme, engine cascade, sitelinks, url tools, plugins). Use this skill whenever the user asks to merge, sync, update, rebase or pull upstream into the fork, to apply or re-apply the patches in patches/, or to port upstream changes to the modern theme, even if they don't mention patches explicitly.
---

# Syncing the fork with upstream

This repo is our fork of upstream. Our customizations live as patch files in `patches/`. To pull in new upstream commits, we do **not** merge or rebase: we start from a clean `upstream/master` and re-apply our patches on top.

**The safe patches should apply cleanly. The unsafe patches will almost always fail.** This is not an error and not an anomaly: it is the reason this skill exists. Upstream changes often, our patches touch code that changes with it, so the real job is to **carry the intent of each patch over onto the current upstream code**. The descriptions below are the spec of that intent. Do not invent behavior that is not described here.

## Constraints (read before doing anything)

**Windows and colons in filenames.** We work on Windows and upstream contains files with colons in their names. A normal clone or pull fails on them, so this must be set:

```bash
git config core.protectNTFS false
```

Those files are skipped and simply do not exist in the working tree. We never edit them. Consequences:

- They will show up as **deleted** in `git status`. **Never commit those deletions.**
- Before **every** commit, run `git status --porcelain` and look for deleted (`D`) paths containing a colon. If any are staged, unstage them with `git reset HEAD -- "<path>"`.
- Never use a blind `git add .` or `git add -A` without running that check right after.

**Remotes.** There are two:

- `origin`: our fork.
- `upstream`: the original repo.

**Branching.** Every sync happens on a **new branch** created from `upstream/master` (suggested name: `sync/upstream-YYYY-MM-DD`). Never apply patches directly on `master` or on any existing branch: this protects working code from accidents.

**The `patches/` directory is read-only for you.** Never edit, regenerate, overwrite or delete anything under `patches/`, even after you have successfully resolved conflicts, unless explicitly instructed by the user. The user regenerates the patch files after reviewing your result. A broken or half-updated patch in the repo is worse than an outdated one.

**Stop instead of guessing.** If you are not sure what a hunk was meant to do against the new upstream code (function removed, file restructured, logic rewritten), stop and ask the user. A guessed hunk ends up inside a regenerated patch without anyone noticing.

## Workflow

1. `git fetch upstream` and `git fetch origin`.
2. Make sure `core.protectNTFS` is `false` (see above).
3. Create the sync branch from `upstream/master`.
4. Apply the safe patches (one commit).
5. Apply each unsafe patch, **in the order listed below**, **one commit per patch**. The order matters: patches depend on each other (modern builds on theme modularity, and subsequent features build on both). Each commit must contain only the delta of its patch, so the user can regenerate that patch from the commit with `git show` or `git format-patch`.
6. Run the final verification.
7. Write the final report (format below).

## Applying safe patches

These add or remove files and should not generate conflicts. They provide:

- a custom Dockerfile and docker compose (`patches/safe/docker.patch`)
- fork documentation (`patches/safe/docs.patch`)
- branding images (`patches/safe/images.patch`)
- an edit to one translation, across all languages (`patches/safe/translations.patch`)
- a disabled GitHub Action, plus 2 new ones (`patches/safe/workflows.patch`)

1. **Dry-run to check for conflicts:**
   ```bash
   git apply --check patches/safe/docker.patch patches/safe/docs.patch patches/safe/images.patch patches/safe/translations.patch patches/safe/workflows.patch
   ```
   If it exits silently with no output, the patches apply cleanly. If it fails, do not continue blindly: run the check on each patch separately to find which one fails and why, then treat it like an unsafe patch (see "When a patch does not apply") and report it.

2. **Apply:**
   ```bash
   git apply patches/safe/docker.patch patches/safe/docs.patch patches/safe/images.patch patches/safe/translations.patch patches/safe/workflows.patch
   ```
   Run `git status` to verify the modified and added files.

3. **Stage and commit** (with the colon-deletion check from the Constraints section):
   ```bash
   git add -A
   git status --porcelain
   git commit -m "Apply safe patches"
   ```

## When a patch does not apply

This is the normal case for unsafe patches. Method:

1. `git apply --check <patch>` to see which hunks fail and on which files.
2. Try `git apply --3way <patch>`. It applies what it can and leaves conflict markers where it cannot. If `--3way` is not possible (missing blobs), use `git apply --reject <patch>`: it applies the clean hunks and writes the failed ones to `.rej` files. Delete the `.rej` files before committing.
3. For each hunk that failed, look at what upstream did to that code (`git log` / `git diff` on the file, against the previous upstream base: `git merge-base origin/master upstream/master` gives the last upstream commit the fork was based on) and redo the hunk by hand on the current code, using the patch description below as the spec.
4. If you cannot tell how to carry the intent over, **stop and ask the user**. Say which patch, which file, which hunk, and what changed upstream.
5. Commit with the message `Apply <patch-name>.patch`.

## Applying unsafe patches

These touch code that upstream will keep changing, so take extra care. Run `git apply --check` first, then follow "When a patch does not apply" if it fails.

### 1. Core fixes: `patches/core-fixes.patch`

```bash
git apply --check patches/core-fixes.patch
```

Applies core developer experience and error reporting improvements:
- In `searx/settings_defaults.py`: collects and reports all schema validation errors clearly with full key namespaces, instead of failing on the first error with obscure paths.
- In `searx/version.py`: catches general `Exception` on git version metadata lookup to prevent hard crashes during development or packaging.

### 2. Theme modularity: `patches/theme-modularity.patch`

```bash
git apply --check patches/theme-modularity.patch
```

Provides the architectural foundation that allows custom themes (like modern) to inherit unchanged templates and fall back to `simple` without code duplication:
- In `searx/templates/simple/` (`404.html`, `base.html`, `index.html`, `page_with_header.html`, `results.html`, `search.html`): parameterizes template inheritance (e.g. `{%- extends theme + "/base.html" -%}` instead of hardcoded `simple/base.html`).
- In `searx/webapp.py`:
  - `get_result_template()`: falls back to `simple/result_templates/<template>` if not found in requested theme.
  - `render()`: falls back to rendering `simple/<template>` if the theme does not implement that specific template file.

Rule to carry over: any template reference in simple that hardcodes `simple/` (`extends`, `include`, `import`) must use `theme + "/..."`. This includes **new** templates and references that upstream added since the last sync.

### 3. Simple theme customizations: `patches/simple-theme.patch`

```bash
git apply --check patches/simple-theme.patch
```

Applies custom branding and style rules specific to the simple theme client under `client/simple/` (`src/less/style.less`, `style-rtl.less`, `index.less`), plus its build configuration (`vite.config.ts`, `package-lock.json`).

### 4. Modern theme: `patches/modern-theme.patch`

```bash
git apply --check patches/modern-theme.patch
```

Adds the complete modern theme under `client/modern/` and `searx/templates/modern/`.

⚠️ **Critical.** Even though the theme relies on `theme-modularity.patch` to duplicate only the templates it needs, a template customized in modern (for example `base.html`) can be updated upstream in simple. When that happens, the change **must be reflected in modern too**. Example: if upstream adds a link to `<nav id="links_on_top">` in simple's `base.html`, add the same link to `<nav id="links_on_top">` in modern's `base.html`.

In the same way:
- `package.json` and `tsconfig.json` in modern must reflect the versions and settings of the simple client ones.
- `vite.config.ts` gets special treatment: it is configured to pull as many unchanged files as possible from simple. If simple's version changes, update modern's accordingly **while keeping its current behavior**.

If upstream changes are not carried over every time, the theme stops working, and after a few syncs the backlog is so large that a complete theme rewrite is needed. **Never skip updating modern.**

How to do it: take the upstream diff of `client/simple/` and `templates/simple/` between the previous base and the new `upstream/master`, and for every changed file that modern overrides or mirrors, decide whether modern needs the same change. The per-file result goes into the report (see below).

### 5. Engine cascade: `patches/engine-cascade.patch`

```bash
git apply --check patches/engine-cascade.patch
```

By default SearXNG fires parallel queries to all engines and combines them (its metasearch behavior). This feature makes it behave like a fallback chain instead:
- Queries engines sequentially one by one until an engine returns valid results.
- Respects custom engine ordering configured by the user.

Files touched:
- `searx/settings_defaults.py` & `searx/preferences.py`: defines `engine_cascade` and `engine_order` settings and defaults.
- `searx/search/models.py`: adds `engine_cascade` flag to `SearchQuery`.
- `searx/webadapter.py`: parses `engine_cascade` and sorts engine refs according to `engine_order`.
- `searx/search/__init__.py`: implements `search_sequential_requests()`.
- `searx/templates/simple/preferences.html` & `preferences/engine_cascade.html`, `preferences/engine_order.html`: frontend UI controls.

### 6. Sitelinks: `patches/sitelinks.patch`

```bash
git apply --check patches/sitelinks.patch
```

Adds sitelinks: sub-queries fired when an eligible website appears in search results (e.g., when Stack Overflow is in the results, a list of related Stack Overflow links appears under the main result).

Files touched:
- `searx/result_types/_base.py`: adds `sitelinks` field to `Result` and `LegacyResult`, and URL normalization.
- `searx/search/processors/online.py`: implements `_add_forced_sitelinks()`, `_get_sitelinks()`, and `_get_property()`.
- `searx/webapp.py`: highlights query terms inside sitelink titles in `search()`.
- `searx/plugins/tracker_url_remover.py`: cleans tracking parameters from sitelink URLs.

### 7. URL tools & proxify: `patches/url-tools.patch`

```bash
git apply --check patches/url-tools.patch
```

Adds URL utilities and privacy proxying in `searx/webapp.py`:
- `url_proxify()`: prepends a configured proxy service to URLs for anonymous browsing, exposing proxy context variables to templates (`proxify`, `proxify_results`, `proxy_method`, `proxy_url`, `proxy_post_params`).
- `get_pretty_url()`: cleans up trailing slashes, truncates long paths with ellipsis, and styles separators (` › `).
- `get_pretty_host()`: helper extracting clean hostname (stripping `www.`).

### 8. Plugins: `patches/plugins.patch`

```bash
git apply --check patches/plugins.patch
```

Extends tracker pattern database in `searx/data/tracker_patterns.py` (e.g. appends `tl` tracking parameter cleanup for `reddit.com`).

## Final verification

Do not declare the work finished without running these:

1. `git status --porcelain`: no staged deletions of colon-named files, no leftover `.rej` files or conflict markers (`grep -rn '^<<<<<<<\|^>>>>>>>' client templates searx` or equivalent).
2. No hardcoded `simple/` references left in `extends`, `include` or `import` in `templates/simple/` and `templates/modern/` (the `theme + "/..."` rule from theme-modularity). New upstream templates are the usual offenders.
3. Build the clients (simple and modern) with the commands defined in their `package.json`. If you are not sure which command to run, ask.
4. Run the project's test suite if one is available, and report failures that look related to our patches.
5. Confirm that all patches apply cleanly with `git apply --check`.

## Final report

For each patch, in this fixed format, so the user can review before regenerating:

- **Patch:** name, and the commit that contains it.
- **Applied cleanly:** hunks/files that went through unchanged.
- **Redone by hand:** for each hunk, one line on what changed upstream and one line on how it was adapted.
- **Doubts / stopped:** anything you were unsure about, or where you stopped and asked.

For `modern-theme.patch`, additionally:

- The list of files in `client/simple/` and `templates/simple/` that upstream changed since the previous base.
- For **each** of them: whether modern mirrors it, and if so whether it was updated (yes / no / not needed, with the reason). An empty or partial list here means the work is not finished.

Also report the previous upstream base commit you used for the diffs, so the user can check it.
