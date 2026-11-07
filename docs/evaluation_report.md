# Evaluation Report — Academic Regulation and Student Petition Triage Service

## 1. Evaluation Overview

This report documents the evaluation framework and observed test results for the Academic Regulation and Student Petition Triage Service.

The evaluation focuses on:

- Petition classification and processing.
- Retrieval evidence and citation correctness.
- Verification of agent-generated claims.
- Routing recommendations.
- Prompt-injection detection.
- Unsupported or fabricated citations.
- Toxicity checks.
- Fail-safe behavior when evidence is unavailable.

The evaluation dataset contains 22 synthetic test cases.

## 2. Evaluation Dataset

**Dataset:** `evaluation/evaluation_set.json`

**Dataset version:** v1

**Total test cases:** 22

The evaluation set includes cases designed to test:

- Ordinary petition-processing scenarios.
- Attendance and condonation scenarios.
- Evidence and citation verification.
- Missing regulatory provisions.
- Prompt-injection attempts.
- Fabricated citations.
- Unsafe or inappropriate language.
- Routing and escalation behavior.

The test cases use synthetic information and do not represent actual student records.

## 3. Evaluation Methodology

The evaluation implementation is provided in:

- `evaluation/evaluator.py`
- `evaluation/evaluate.py`

The evaluator includes the following checks.

### 3.1 Citation Evaluation

The citation evaluator checks whether supplied citations correspond to retrieved evidence.

It examines source references and matching evidence text.

### 3.2 Evidence Evaluation

The evidence evaluator uses lexical overlap as a diagnostic signal for comparing claims and retrieved passages.

This is not a substitute for semantic groundedness evaluation.

### 3.3 Prompt-Injection Evaluation

The evaluation checks whether suspicious prompt-injection patterns are detected by the application's input guardrails.

The current implementation uses heuristic pattern matching and is not an exhaustive security detector.

### 3.4 Toxicity Evaluation

The toxicity evaluator checks for a limited set of inappropriate language patterns.

It is a lexical heuristic and should not be interpreted as a comprehensive semantic toxicity model.

### 3.5 Routing Evaluation

The routing evaluator checks whether the system follows fail-safe behavior when evidence is missing or verification fails.

An unsupported recommendation must not be presented as a verified eligibility decision.

## 4. Observed Evaluation Results

The evaluation command was executed using:

```bash
python -m evaluation.evaluate
```

The observed output was:

| Metric | Observed result |
|---|---:|
| Total test cases | 22 |
| Evaluated cases | 10 |
| Not evaluated | 12 |
| Passed | 10 |
| Failed | 0 |
| Pass rate among evaluated cases | 100% |

The pass rate is calculated only from the 10 evaluated cases. It does not represent overall system accuracy or regulatory correctness.

## 5. Evaluation Status by Case

The observed evaluation results were:

| Case group | Count | Status |
|---|---:|---|
| EV001–EV012 | 12 | Not evaluated |
| EV013–EV022 | 10 | Passed |

The first 12 cases require live retrieval or agent-generated outputs and therefore remain pending evaluation.

The remaining 10 cases passed the implemented static evaluation checks.

## 6. Interpretation of Results

The current results demonstrate that the implemented static evaluation checks execute successfully for the evaluated synthetic cases.

However, the results do not establish that the system can correctly interpret real university regulations.

The regulation corpus has not yet been populated with the selected university's official regulations and examination bye-laws.

Consequently:

- Real regulation retrieval accuracy has not been established.
- Semantic groundedness and faithfulness have not been fully measured.
- Real-world eligibility classification accuracy has not been established.
- The 12 pending cases require further evaluation using actual retrieval and agent outputs.

## 7. Known Evaluation Limitations

1. The current dataset contains synthetic cases.
2. Twelve cases remain unevaluated because live retrieval or agent outputs are required.
3. Evidence relevance currently includes lexical-overlap diagnostics.
4. Semantic groundedness and faithfulness metrics remain pending.
5. Prompt-injection detection uses heuristic patterns.
6. Toxicity detection uses a limited lexical heuristic.
7. No claim of regulatory accuracy can be made without a populated and verified official regulation corpus.

## 8. Recommended Next Evaluation Steps

After selecting and ingesting the official university regulation corpus:

1. Execute the ingestion pipeline.
2. Confirm that regulation documents and clause metadata are available in ChromaDB.
3. Run the 12 pending evaluation cases through the actual agent workflow.
4. Verify retrieved base provisions and modifying or condonation provisions.
5. Measure citation correctness and evidence relevance.
6. Evaluate whether recommendations are supported by retrieved passages.
7. Review committee escalation for cases involving discretionary provisions.
8. Record the results in an updated evaluation report.

## 9. Reproducibility

Run the evaluation from the project root:

```bash
python -m evaluation.evaluate
```

The evaluation report is generated at:

```text
storage/evaluation_report.json
```

The source evaluation cases are maintained in:

```text
evaluation/evaluation_set.json
```

The evaluation implementation is maintained in:

```text
evaluation/evaluator.py
evaluation/evaluate.py
```

## 10. Conclusion

The evaluation framework contains 22 synthetic cases, of which 10 were evaluated and passed the implemented checks. Twelve cases remain pending live retrieval or agent evaluation.

These results demonstrate successful execution of the currently implemented static checks, but they do not establish real-world regulatory accuracy.

The next major evaluation milestone is to populate the system with official university regulations and examination bye-laws, then execute the pending cases against the complete retrieval and multi-agent workflow.