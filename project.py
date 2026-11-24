"""Compare a first-mention baseline with evidence-aware intake extraction."""

import argparse
import json
import re
from pathlib import Path

FIELDS = {
    "program": r"\b(?:computer science|data science|public health|mechanical engineering|finance|architecture)\b",
    "term": r"\b(?:fall|spring|summer) 20\d\d\b",
    "action": r"\b(?:schedule a call|review my documents|send a checklist)\b",
}
OPTIONAL = re.compile(
    r"\b(maybe|might|not sure|undecided|possibly|considering|don't want|do not want|no longer)\b",
    re.I,
)


def extract(turns, *, evidence_aware):
    found = {}
    for turn_number, turn in enumerate(turns, 1):
        if turn["role"] != "applicant":
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", turn["text"]):
            for field, pattern in FIELDS.items():
                match = re.search(pattern, sentence, re.I)
                if match is None:
                    continue
                value = match.group().lower()
                if evidence_aware and OPTIONAL.search(sentence):
                    if found.get(field, {}).get("value") == value and re.search(
                        r"\b(?:don't|do not|no longer)\b", sentence, re.I
                    ):
                        found.pop(field)
                    continue
                if evidence_aware or field not in found:
                    found[field] = {"value": value, "turn": turn_number, "quote": match.group()}
    return found


def make_fixtures():
    programs = (
        "computer science",
        "data science",
        "public health",
        "mechanical engineering",
        "finance",
        "architecture",
    )
    templates = (
        (
            "direct",
            "I want {p} for {t}. Please {a}.",
            "",
            {"program": "p", "term": "t", "action": "a"},
        ),
        (
            "correction",
            "I want {q} for {s}. Please {a}.",
            "Correction. I want {p} for {t}.",
            {"program": "p", "term": "t", "action": "a"},
        ),
        ("negated", "I don't want {q}. I want {p} for {t}.", "", {"program": "p", "term": "t"}),
        ("uncertain", "Maybe {q}. I want {p}.", "I might apply in {t}.", {"program": "p"}),
        ("withdrawn", "Please {a}. I want {p}.", "I don't want to {a}.", {"program": "p"}),
        ("no answer", "Thanks for the information.", "", {}),
        ("partial", "I want {p}.", "", {"program": "p"}),
        ("quoted example", "I would like information.", "Please {a}.", {"action": "a"}),
        (
            "long thread",
            "I read the handbook and shared it with my family. I want {q}.",
            "Thanks for waiting. I want {p}. I have confirmed {t}. Please {a}.",
            {"program": "p", "term": "t", "action": "a"},
        ),
        (
            "mixed intent",
            "I am considering {q}. Please {a}.",
            "Term is {t}.",
            {"term": "t", "action": "a"},
        ),
    )
    for i, p in enumerate(programs):
        for j, (category, first, last, labels) in enumerate(templates):
            args = {
                "p": p,
                "q": programs[(i + 1) % 6],
                "t": f"fall {2027 + i}",
                "s": f"spring {2027 + i}",
                "a": ("schedule a call", "review my documents", "send a checklist")[(i + j) % 3],
            }
            turns = [
                {"role": "advisor", "text": f"Example: {args['q']} in {args['s']}."},
                {"role": "applicant", "text": first.format(**args)},
            ]
            if last:
                turns.extend(
                    [
                        {"role": "advisor", "text": "Could you confirm your preference?"},
                        {"role": "applicant", "text": last.format(**args)},
                    ]
                )
            yield {
                "id": f"eval-{i * 10 + j + 1:02d}",
                "category": category,
                "turns": turns,
                "expected": {field: args[key] for field, key in labels.items()},
            }


def evaluate(rows, predict):
    fields = {key: dict(tp=0, fp=0, fn=0) for key in FIELDS}
    categories = {}
    failures = []
    exact = unsupported = 0
    for row in rows:
        output = predict(row["turns"])
        actual = {key: item["value"] for key, item in output.items()}
        expected = row["expected"]
        good = actual == expected
        exact += good
        category = categories.setdefault(row["category"], {"rows": 0, "exact": 0})
        category["rows"] += 1
        category["exact"] += good
        unsupported += sum(expected.get(key) != value for key, value in actual.items())
        for key, counts in fields.items():
            if key in actual:
                counts["tp" if actual[key] == expected.get(key) else "fp"] += 1
            if key in expected and expected[key] != actual.get(key):
                counts["fn"] += 1
        if not good:
            failures.append(
                {
                    "id": row["id"],
                    "category": row["category"],
                    "expected": expected,
                    "output": output,
                }
            )
    for counts in fields.values():
        tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn"))
        counts["precision"] = round(tp / (tp + fp), 4) if tp + fp else None
        counts["recall"] = round(tp / (tp + fn), 4) if tp + fn else None
    return dict(
        rows=len(rows),
        exact=exact,
        unsupported_values=unsupported,
        fields=fields,
        categories=categories,
        failures=failures,
    )


def demo():
    rows = list(make_fixtures())
    return {
        "baseline": evaluate(rows, lambda turns: extract(turns, evidence_aware=False)),
        "candidate": evaluate(rows, lambda turns: extract(turns, evidence_aware=True)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()
    if args.fixtures:
        args.fixtures.write_text(
            "\n".join(json.dumps(row) for row in make_fixtures()) + "\n", encoding="utf-8"
        )
    report = demo()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: {
                    "exact": value["exact"],
                    "rows": value["rows"],
                    "unsupported_values": value["unsupported_values"],
                }
                for key, value in report.items()
            },
            indent=2,
        )
    )
