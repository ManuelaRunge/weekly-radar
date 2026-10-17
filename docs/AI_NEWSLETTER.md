# AI-assisted RIDA Radar newsletter

**Current default: free preparation, ChatGPT review on demand.** No API key is needed and GitHub Actions never invokes an AI API.

## Current process
1. Every Monday the existing scheduled workflow runs `src/collect.py` and `src/brief.py`.
2. It also runs `python src/newsletter_ai.py --mode prepare`.
3. This creates `output/chatgpt_input.json`: a bounded list of candidate links with source, dates and verification status, plus `output/HOW_TO_CHATGPT.md`.
4. Open ChatGPT with GitHub connected and request: **"Read `output/chatgpt_input.json` and `config/editorial_instructions.md` from my RIDA Radar repository, verify original sources where accessible, and produce this week's private On the Radar newsletter. Keep RIDA post candidates separate."**
5. Review event dates, registrations, scientific claims and LinkedIn URLs. Do not publish the automated output unchanged.

You can run the workflow manually under GitHub **Actions → RIDA Radar → Run workflow**, after merging these changes.

## Run locally (optional)
```sh
python -m pip install -r requirements.txt
python src/collect.py
python src/brief.py
python src/newsletter_ai.py --mode prepare
```

## Later: optional paid API
The optional API mode has been implemented but is **not run by GitHub Actions**. It is activated ONLY by explicitly running:

```sh
export OPENAI_API_KEY='...' # set in your shell or secret manager, never commit
python src/newsletter_ai.py --mode api --model gpt-5-mini
```

It sends the prepared link-record packet and editorial instructions to the OpenAI Responses API and writes `output/ai_draft.md`. Model availability and prices can change; update `--model` as necessary. API usage incurs separate charges and requires API billing. API mode does not independently fetch or verify original source content, so it must mark title-only records as unverified.

**Do not add an API key to GitHub unless you decide to activate scheduled paid AI later.** A secret by itself does not enable AI: the workflow must also be modified to invoke `--mode api`.

## Scope and safety
- No automated LinkedIn publishing.
- LinkedIn original post URLs may be included as manual leads in `config/manual_links.csv`. Dates and authors still need verification. Avoid authenticated scraping.
- This is a private intelligence system, not a public newsletter service. Keep the repository private.
- Source excerpts are preferable to bare links for reliable AI summaries. Source-specific extraction and tests are future improvements.
- Current packet-generation heuristics may omit relevant links or include noise. They do not verify scientific claims.
