"""Offline, read-only coverage audit for canonical Phase-3 checklist.

All 262 module activities, 26 independent module Gates and 105 *non-counting*
operational crosswalks must be present once in the authoritative register.
This is a schema/completeness test, NEVER a promotion to accepted/target PASS.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTER = ROOT / "coordination" / "phase3_checklist.md"
ACT = re.compile(r"^\\| \\*\\*(P3M\\d{2}-A\\d{2})\\*\\*")
OP = re.compile(r"^\\| \\*\\*(P3OP\\d{2}-R\\d{2})\\*\\*")
MOD = re.compile(r"^### (P3M\\d{2}) — ")
GATE = re.compile(r"^- \\[([ x])\\] \\*\\*Independent Module Gate — (NOT PASSED|PASSED):")
ACT_REF = re.compile(r"P3M\\d{2}-A\\d{2}")


def unique(label: str, rows: list[str], pattern: re.Pattern[str], count: int) -> list[str]:
    ids = [pattern.match(line).group(1) for line in rows if pattern.match(line)]
    if len(ids) != count or len(set(ids)) != count:
        raise AssertionError(
            f"{label}: expected exactly {count} distinct register rows; "
            f"found {len(ids)} rows, {len(set(ids))} unique"
        )
    return ids


class Phase3CanonicalRegisterIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lines = REGISTER.read_text(encoding="utf-8").splitlines()
        cls.module_ids = unique("MODULES", cls.lines, MOD, 26)
        cls.activities = unique("ACTIVITIES", cls.lines, ACT, 262)
        cls.operational = unique("OPERATIONAL_NON_COUNTING", cls.lines, OP, 105)

    def test_exact_26_module_sequence_and_independent_gates(self) -> None:
        self.assertEqual(self.module_ids, [f"P3M{n:02d}" for n in range(26)])
        gate_rows = [line for line in self.lines if GATE.match(line)]
        self.assertEqual(len(gate_rows), 26)
        for n, label in enumerate(self.module_ids):
            begin = next(i for i, line in enumerate(self.lines) if line.startswith(f"### {label} — "))
            next_module = next((i for i in range(begin + 1, len(self.lines))
                                if MOD.match(self.lines[i])), len(self.lines))
            within = [line for line in self.lines[begin:next_module] if GATE.match(line)]
            self.assertEqual(len(within), 1, f"{label}: missing/duplicate independent Gate")
            match = GATE.match(within[0])
            self.assertEqual((match.group(1), match.group(2)) in
                             {(" ", "NOT PASSED"), ("x", "PASSED")}, True,
                             f"{label}: contradictory Gate mark")
            # A future Gate PASS must explicitly retain its own approved witness.
            if match.group(2) == "PASSED":
                self.assertNotIn("(future evidence only)", within[0], label)

    def test_all_activity_ids_have_owner_criterion_acceptance_and_evidence(self) -> None:
        source_ids = set(self.activities)
        self.assertEqual(len(source_ids), 262)
        for line in self.lines:
            m = ACT.match(line)
            if not m:
                continue
            self.assertIn("**Output:**", line, m.group(1))
            self.assertIn("**Check:**", line, m.group(1))
            self.assertIn(" | ", line, m.group(1))
            self.assertIn(" — ", line, m.group(1))
            self.assertTrue("NOT_RUN" in line or "PASS" in line
                            or "DOCUMENT_REVIEW_ONLY" in line
                            or "CI" in line or "VERIFIED" in line
                            or "TESTED" in line,
                            f"{m.group(1)}: no explicit test state")
            self.assertIn(" | ", line.split("**Check:**", 1)[1], m.group(1))

    def test_all_105_crosswalk_references_resolve_to_canonical_activities(self) -> None:
        activity_set = set(self.activities)
        for line in self.lines:
            m = OP.match(line)
            if not m:
                continue
            refs = set(ACT_REF.findall(line))
            self.assertTrue(refs, f"{m.group(1)}: mapping missing")
            self.assertFalse(refs - activity_set, f"{m.group(1)}: orphan IDs {refs - activity_set}")
            self.assertIn("Mapped only" if "Mapped only" in line
                          else "GAP/CONFLICT", line, m.group(1))

    def test_crosswalk_does_not_inflate_primary_denominator(self) -> None:
        self.assertEqual(len(self.activities) + len(self.module_ids), 288)
        self.assertEqual(len(self.operational), 105)
        self.assertEqual(len(self.activities) + len(self.module_ids) +
                         len(self.operational), 393)


if __name__ == "__main__":
    unittest.main()
