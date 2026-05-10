# Potential Impact in Financial Markets

A pointed assessment of what ChainRight's framework could change for
banks, asset managers, regulators, fintechs, and AI vendors operating in
financial services. Not a marketing document. Where the technical claims
become brittle when applied, this report flags it.

## Why finance is the right test case

Three properties of financial regulation make it the cleanest target for
a chained-provenance audit framework, and a much harder target than
general AI safety or content moderation:

1. **Material non-public information (MNPI)** has an established legal
   definition and a thirty-year case-law history. There is a clear
   yes/no test for whether a piece of information should be private.
2. **Adjudicable AI** — the regulator's question is not "is this AI
   safe?" but "did this specific output cause harm in this specific
   trade or recommendation?" That is a per-call question, which maps
   directly onto the per-call ledger primitive.
3. **Chinese walls** between business units (research vs. trading,
   M&A advisory vs. broker-dealer, etc.) are already enforced by
   process and policy. AI deployment threatens these walls in a way
   that no current regulation specifically addresses.

The audit gap created by frontier LLMs lands directly on top of all
three of these properties. If ChainRight's framework holds, the
financial industry is the first place its impact becomes legally
material.

## The three audit primitives, mapped to financial use cases

### Per-call provenance for adjudicable AI

The `chain_equilibrium_run` primitive records, for every prompt-
response pair, the verifier's per-clause verdict, the typing-cost of
running the verifier, the attribution graph hash, and the model
identifier. The chain is content-addressed, append-only, and
cryptographically valid under save/load.

**Where this bites in finance:**

- **Loan origination.** A small-business loan denied by an AI-assisted
  underwriting tool. Plaintiff alleges discrimination. Today the bank
  cannot reproduce the denial reasoning bit-exactly because the
  upstream LLM's responses are not deterministic and not logged at
  the input-output level. With per-call provenance, the chain
  produces the prompt, response, equilibrium verdict, and circuit-
  level attribution that the loan officer saw.
- **Investment recommendation.** A recommendation surfaces in
  research that turns out to be material non-public information
  about a covered company. SEC inquiry. Today the firm cannot
  trace whether the recommendation came from a leak, a memorized
  training-data fragment, or generalization from public filings.
  With chained attribution, the answer is on chain.
- **AML / sanctions screening.** A false negative lets through a
  transaction that should have been blocked. Regulator asks why.
  Today: opaque LLM output, model card. With chain: per-call
  reasoning trace, including which clauses passed and which failed.

The unit cost on this is currently ~52 seconds of human-typing-
equivalent verifier work per call (corpus-mode measurement). If a
bank does 10⁴ AI-assisted decisions per day, the audit budget is
**~140 hours of analyst-equivalent time per day** to verify. That is
the conversation regulators and banks should be having and aren't.

### Absence attestation for non-public material

The `chain_corpus_check` primitive verifies that a piece of text does
*not* appear in a configured corpus set, recording the result with a
hash of the text (never the text itself), the corpus list, the
timestamp, and the verdict.

**Where this bites in finance:**

- **MNPI handling.** Before a piece of information is treated as
  public (released, traded on, redistributed), an analyst can run
  it against EDGAR filings, news archives, public datasets, and
  the firm's published research. A clean negative scan, chained,
  is a defensible attestation that as of date D the information was
  not yet public. That converts an internal compliance claim into
  a third-party-verifiable artifact.
- **Pre-publication research.** An analyst writing a research note
  can confirm the note's substantive findings are not leaked into
  public corpora before circulation. Chained attestation makes the
  pre-publication state legally discoverable.
- **Insider-trading defense.** A trader accused of acting on MNPI
  can demonstrate that the information they had was either
  contemporaneously public (chain shows it in a public corpus) or
  contemporaneously non-public (chain shows clean negative scan).

The honest limitation: the corpus set must be broad enough for the
negative claim to bite. webtext alone is ~250K records — too small
to be meaningful. EDGAR + major news archives + Common Crawl
excerpts together would be defensible. Building the broader corpus
is the hard work; the chain is the easy part.

### Cross-firm model isolation for Chinese-wall compliance

This is the §1.4 concern from the underlying paper: if two business
units within a firm (or two firms in the same financial group) share
weights of the same internally-fine-tuned model, that model has
implicitly learned features from both business units' data. A
research-side query against the model risks pulling in trading-side
training signal. The Chinese wall has a hole.

ChainRight does not directly enforce wall isolation, but it makes
the violation observable. With per-prompt circuit-level attribution
chained alongside the response, you can detect features in the
attribution that originated in training data the querying business
unit was not supposed to see.

**Where this bites in finance:**

- **Sell-side research / proprietary trading.** A research analyst
  queries an internal model. The attribution graph implicates
  features whose chained training-data origin is the trading desk's
  log. Wall violation, observable in the chain.
- **M&A advisory / capital markets.** Same shape, between advisory
  and underwriting groups.
- **Multi-strategy fund.** Same shape, between systematic and
  fundamental teams.

The technical gap here is real: full feature-to-data attribution
during training is at the frontier of mechanistic interpretability
research. ChainRight provides the chain that *would* enable the
detection if the attribution method matures. We claim the audit
shape, not the detection method.

## The substitution argument

The strongest implication of this framework, if the experimental work
goes through, is a substitution claim:

**A small (~125M–1B param) finance-task-specific model with full
chained provenance can replace a frontier API for regulated activities
where audit defensibility matters more than general capability.**

Specifically:

- The frontier-API path: high task accuracy, opaque internals,
  unbounded inference space, no per-call audit, no training-data
  retrace. Net cost: API fees + audit-impossibility risk premium.
- The chained-provenance path: lower task accuracy on open-ended
  tasks, full per-call audit, full training-data retrace, bounded
  by the inference space the local model has actually seen. Net cost:
  development + training compute (one-time) + audit-defensible.

For tasks where regulatory cost dominates capability cost — which is
most regulated financial activities — the substitution is not
hypothetical. It's a TCO calculation. The training_vs_inference
combinatorics note argues this calculation has not been done, and
that the industry's current default of "use the frontier API" is the
right choice only if you ignore the audit liability.

This is the actual commercial proposition behind ChainRight: not
"audit OpenAI / Anthropic / Google models," because that is
structurally impossible in the closed-API regime. Rather, "build the
small auditable model whose audit defensibility lets it win the
regulated-task contract that the frontier API cannot defensibly take."

## Risks and limitations

A short list of where the framework's claims become weaker on contact
with reality:

1. **Chain integrity ≠ correctness.** The chain proves what was run,
   not that what was run was correct. A bank that chains a thousand
   incorrect AI denials still has chained a thousand incorrect AI
   denials. The audit primitive is necessary but not sufficient.

2. **Negative attestations require broad corpora.** A clean negative
   scan against a small corpus says nothing about a large one. The
   absence-attestation primitive is only as strong as the corpus list.
   Building and maintaining regulator-grade corpus coverage (EDGAR,
   news archives, etc.) is itself a non-trivial engineering effort.

3. **Attribution methods are not fully mature at frontier scale.**
   TracIn, datamodels, and circuit-tracer are well-validated at
   small-model scale. Attribution at frontier scale (10¹²+
   parameters, 10¹³+ training tokens) currently relies on proxies,
   not exact computation. Claims about "we can retrace any output
   to its training data" should be qualified by model and corpus
   scale.

4. **Adversarial prompt construction.** A bad actor could
   deliberately construct prompts that satisfy the equilibrium
   clauses while still producing harmful outputs. The framework
   does not claim adversarial robustness; the eight clauses are
   designed for ordinary deployment, not red-team conditions.

5. **Regulatory adoption lag.** Even if the technical case is sound,
   regulatory frameworks move slowly. The gap between "this primitive
   exists" and "this primitive is required by FINRA / SEC / OCC /
   FCA / ESMA" is years, not quarters.

## What an actor in finance should do with this

**Banks (commercial / investment / private):** Pilot per-call
provenance on one regulated workflow (loan denials, investment
recommendations, AML alerts) with a small open-weights model.
Measure the audit-cost-per-call empirically. The 52-second number
is a starting point, not a final claim. Compare to the implied
cost of audit-impossibility on the frontier-API path.

**Asset managers / hedge funds:** Pilot absence-attestation on a
research workflow where MNPI risk is non-trivial. Build the custom
corpus list (EDGAR + relevant news archives + your firm's published
research). Chain the negative scans. Discuss with compliance counsel
whether the chained attestation has evidentiary weight under your
firm's internal MNPI policy.

**Regulators:** Read the four notes. Engage with the framework on the
question "what would make a per-call audit regime tractable at the
volumes you would need to enforce it?" The 52-second-per-call number
is the conversation. Multiply by your jurisdiction's volume and ask
whether the headcount is plausible.

**Fintechs / AI vendors selling to finance:** This framework is a
moat against frontier-API competitors in regulated workflows.
Vendors who ship chained-provenance small models can defensibly
sell into use cases where frontier-API vendors cannot. The
substitution argument above is the pitch.

**Compliance / legal practitioners:** The absence-attestation primitive
is the most directly useful for current MNPI workflows. The
per-call provenance primitive is most useful for forward-looking
audit defensibility on AI-assisted decisions. Both are in the
state where "deploy in pilot" is the right next step, not "wait
for regulator endorsement."

## Open questions

- What is the cps (characters-per-second) baseline that should be
  used in regulatory cost calculations? Different regulator
  jurisdictions have different analyst-time pricing assumptions.
- How should chained negative attestations be timestamped against
  market hours? Is `now()` UTC sufficient, or does the chain need
  to anchor to an external timestamp authority (e.g., a public
  blockchain)?
- What is the smallest defensible corpus list for MNPI-grade
  absence attestation in U.S. equities? In credit? In FX?
- How does this framework interact with the EU AI Act's
  high-risk-system documentation requirements? With FINRA's
  proposed AI guidance? With the OCC's model-risk-management
  framework (SR 11-7)?

These are the questions that would move ChainRight from "interesting
research framework" to "actually deployed in regulated production."
None of them are technical at this point. All of them are policy-
adjacent and require engagement with practitioners and regulators.
