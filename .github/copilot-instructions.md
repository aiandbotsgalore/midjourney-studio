# Copilot / AI Agent Instructions for Midjourney v3 Studio

This file gives focused, actionable guidance for an AI coding agent working in this repository.
Keep instructions concrete and reference code locations so you can be immediately productive.

## Big picture
- Single-file Streamlit app: the UI and API client live in `app.py` (large, ~2000+ lines).
- `MidjourneyAPI` (in `app.py`) is the primary integration point with UseAPI's Midjourney v3 endpoints.
- UI state is stored in `st.session_state`; jobs are submitted via `MidjourneyAPI` then polled (see `poll_job_status`).

## Key components & where to look
- `app.py`:
  - `MidjourneyAPI` class: methods `imagine`, `blend`, `describe`, `button`, `seed`, `get_job`, `list_running_jobs`. Use these methods for all network interactions.
  - `build_prompt(base_prompt, params)`: canonical prompt construction pattern (flags: `--ar`, `--v`, `--s`, `--c`, `--q`, `--seed`, etc.).
  - `poll_job_status(api, job_id)`: blocking poll loop (3s interval by default, `POLL_INTERVAL`). Prefer reusing it for consistent behavior.
  - File upload handling: `blend` expects `imageBlob_1..N`; `describe` expects `imageBlob`. Both accept tuples `(filename, bytes, content_type)`.

## Important patterns and conventions
- Multipart file uploads: always use `files` encoded as `(filename, bytes, content_type)` and name blobs as `imageBlob` or `imageBlob_1/2/...`. See `MidjourneyAPI.blend` and `describe`.
- Prompt params: `params` is a dict with keys like `ar`, `version`, `stylize`, `chaos`, `quality`, `weird`, `seed`, `sref`, `cref`, `iw`, `sw`, `cw`. Use `build_prompt` to format them.
- Job lifecycle: submit → add to `st.session_state.active_jobs` → poll with `poll_job_status` → move to `job_history` on terminal states (`completed`, `failed`, `moderated`). Keep UI updates consistent with these keys.
- Secrets: credentials are read from `.streamlit/secrets.toml` if present (`load_secrets` / `save_secrets`). There are hardcoded defaults in `init_session_state` — treat them as placeholders and remove before sharing.

## Running, debugging, and developer workflow
- Python version: 3.12+ (see `README.md`). Use a venv on Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
- To debug API calls, search `MidjourneyAPI._request` and add logging around `requests.request`. Use temporary `st.write()` lines in Streamlit pages for quick inspection.
- To reproduce upload behavior in unit tests or scripts, construct files like:
```python
files = [(name, bytes_data, content_type)]
# Then call MidjourneyAPI.blend(files, dimensions="Square")
```

## Examples (copyable snippets)
- Submit an imagine job (follow `app.py` usage):
```python
api = MidjourneyAPI(api_token)
code, result = api.imagine(final_prompt, stream=False)
if code in (200,201):
    job_id = result.get('jobid')
    poll_job_status(api, job_id)
```
- Blend 3 images (client-side):
```python
files = [(f.name, f.getvalue(), f.type or 'image/png') for f in uploaded_files[:3]]
code, res = api.blend(files, dimensions='Square')
```
- Describe (reverse prompt) one image:
```python
code, res = api.describe(file_bytes, filename, content_type)
```

## Safety & repo-specific cautions
- Secrets in `init_session_state` are present in the codebase as defaults. Replace them with `.streamlit/secrets.toml` values and do NOT commit real tokens.
- The app blocks on `poll_job_status` — long-running operations may freeze the UI; prefer existing flow (Streamlit `st.status` and intermittent reruns) when making changes.
- Rate limits and capacity: code checks `list_running_jobs()` and uses simple waits. If modifying batch logic, keep the existing capacity checks to avoid unexpected 429s.

## Where to add tests or refactors (recommended, not required)
- Consider extracting `MidjourneyAPI` to its own module (e.g., `midjourney/api.py`) to allow unit testing of request construction and error handling.
- Add small tests for `build_prompt` with representative `params` dicts to ensure prompt flags are formatted correctly.

## Files worth scanning for more context
- `app.py` (primary) — start here for behavior and examples
- `requirements.txt` — confirm runtime deps (`streamlit`, `requests`, `toml`)
- `.streamlit/config.toml` and `.streamlit/secrets.toml.example` (see README) — runtime theme and secrets locations

If anything here is unclear or you want this guidance expanded (more examples, CI steps, or a proposed refactor), tell me which sections to expand and I will iterate.
