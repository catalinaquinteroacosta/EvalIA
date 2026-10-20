# PA semantic family — initial isolated package

**Status: foundation only, NOT live-validated or ready for clinical/research scoring.**

The official evaluator protocol AD-05 defines PA1–PA8. This package contains literal-evidence validation, immutable contracts, fail-closed deterministic ordinal mapping and an adapter-based orchestration skeleton. It does **not** implement a working OpenAI extractor, independent semantic verifier, automated assessor, reconciliation, cache or the rubric-complete indicator-specific scoring rules. Those must be developed and validated before use. Do not treat the tests as evidence of scoring accuracy.

No shared files were changed. Copy only the `backend/evaluators/pa/` subtree into your project, after checking that directory does not already contain concurrent work. No terminal closing commands are included.

The N/A exception for a bare greeting must be established using the protocol's objective non-evaluable-content condition; general PA4 is not automatically N/A when resources are unmentioned. Missing user/response is missing data, not N/A.

## Pending
- Full PA1–PA8 component matrix grounded in the official rubric and decision boundaries
- Provider-backed semantic extraction and independent verification, with independent absence audits
- Per-indicator applicability, including general vs conditional, and history relevance
- BLOCKED-only reconciliation, private versioned cache, audit reports
- Adversarial local tests and genuine OpenAI live tests
- 72-case validation after new independent cases
