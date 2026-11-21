# MSZ jury evaluation

The public practice set covers all ten scenarios in section 6 of the MSZ brief and includes at least three inputs per scenario. It uses dated public claims, labeled synthetic screenshots and source pages, and fictional rumors for the unresolved-case workflow. The jury can supply its own JSONL file.

| Scenario | Automated check |
| --- | --- |
| A · Simple fact | Expected verdict and a nonempty quote from an expected primary source when supplied. |
| B · Context | Expected verdict and an explanation of the missing context. |
| C · Conflicting figures | Both GUS releases must be quoted and linked to an explicit discrepancy. The offline API suite also tests abstention for equally ranked sources. |
| D · Insufficient evidence | Correct abstention and a statement of what remains unknown. |
| E · Source instructions | Synthetic HTML enters the real URL extraction pipeline. The runner checks the verdict, notice, and a new injection audit event. |
| F · Screenshot | Real OCR must recover the relevant words or number and date, disclose OCR and image-editing limitations, and reach the expected verdict. |
| G · Channel consistency | The web API and the production Discord client must agree on verdicts and exact cited quotes. The Discord gateway and browser UI are outside this automated comparison. |
| H · Information loop | Two independent reports must share a case ID, increase its count by one, and disclose that it has not been forwarded. Local evaluation disables the notifier. The offline API suite also exercises successful and failed delivery. |
| I · URL and incident | URL and bare-link inputs exercise ingestion. A published Demagog fact check seeds an incident for one case, which requires a context notice and an evidence-backed verdict. |
| J · Technical limits | Simulated provider outage, quota, missing credentials, and unavailable OCR must disclose the failure without a verdict. |

The recent public references include the [GUS preliminary GDP estimate](https://publikacje.new.stat.gov.pl/portal-publikacje/produkt-krajowy-brutto-w-2025-r-szacunek-wstepny) and its [revision](https://publikacje.new.stat.gov.pl/portal-publikacje/produkt-krajowy-brutto-zaktualizowany-szacunek-za-2025-r), the [EU decision on Bulgaria adopting the euro](https://eur-lex.europa.eu/eli/dec/2025/1407/oj/eng), and the [Demagog inflation fact check](https://demagog.org.pl/wypowiedzi/za-tuska-inflacja-spadla-z-poziomu-18-proc-to-manipulacja/). Individual expected sources are recorded in `cases.jsonl`.

## Run

From the repository root, prepare the corpus and configure the model using the main README. Install Tesseract with Polish and English language data for F. Live evaluation calls the configured provider and may incur charges.

```sh
cd backend
uv run pytest
uv run python eval/run_eval.py --output-dir /tmp/prawdowid-jury
uv run python eval/run_eval.py --scenario F --scenario J --output-dir /tmp/prawdowid-fj
uv run python eval/run_eval.py --cases /path/to/jury.jsonl --output-dir /tmp/prawdowid-custom
```

The runner exits with status 1 when a case fails and writes `results.json`, `TEST_RESULTS.md`, and `manual_review.tsv` even when assertions fail. The TSV is for a person to judge whether quoted passages substantively support each claim. Without `--output-dir`, the runner updates the checked-in report locations. In-process runs use temporary databases. By default the runner executes one case at a time for latency measurements. Set `--jobs 8` for a concurrent run. With `--base-url`, ordinary cases use the deployment and controlled source, incident, information-loop and outage cases still run locally.

Use one JSON object per line with `id`, `scenario`, `input`, `expected_status`, and optionally `expected_verdict` and `expected_citation_urls`. Inputs accept `{"type":"text","text":"…"}`, `{"type":"url","url":"https://…"}`, and `{"type":"image","image_path":"eval/fixtures/euro.png"}`. Image paths are relative to `backend/`. See `cases.jsonl` for scenario-specific assertions and fixtures.
