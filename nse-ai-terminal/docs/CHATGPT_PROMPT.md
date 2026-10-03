# Prompt to give ChatGPT / Codex / Copilot

You are helping me extend the repo "NSE-AI-TERMINAL" (FastAPI backend in `backend/`, mobile app in
`app/www/` built to an APK by GitHub Actions). Read `README.md` and `docs/API.md` first.

Hard rules:
1. PAPER ONLY. Never add real order placement unless I explicitly ask in a separate task, and then
   behind an env flag that defaults to off, with position/loss limits enforced by `RiskGuard`.
2. Never put broker credentials, PINs or TOTP in the app or in git. Secrets live in backend env vars.
3. Keep the JSON shapes in `docs/API.md` stable; if you change one, update `app/www/app.js` and the docs.
4. Add or update a test in `backend/tests/` for every backend change. Run `python -m pytest -q`.
5. Be honest in the UI: label simulated data as simulated.

Tasks:
- A) Angel One SmartAPI market-data adapter (read-only quotes + option chain) behind `FEED_MODE=angel`.
- B) Order-flow screen and SQLite memory of signals + outcomes.
- C) Real option-chain source replacing `options.build_chain()`.
- D) Optional LLM validator layers.
- E) Signed release APK in GitHub workflow using repository secrets.

For each task: explain the plan, give complete changed files, then the test.