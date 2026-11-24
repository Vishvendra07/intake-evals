# Intake Evals

A 60-case harness for intake extraction compares first mention with an evidence-aware policy for corrections, uncertainty, and withdrawn requests.

[Source](project.py) · [Demo evidence](evidence/comparative-report.json) · [Verification](evidence/checks.json)

## Run locally

Requires Python 3.11+.

```sh
python project.py --output comparison.json
python -m unittest discover -v
```

## Engineering decision

Score values separately from evidence and expose missed, wrong, and unsupported values. Inspect an individual failure by reading the model output, expected fields, and cited turn.

The two extractors are deterministic comparators and the cases are authored templates. The report measures fixture regressions, with no estimate of general LLM accuracy.



[Technology or project reference](https://docs.python.org/3/library/re.html)
