# Reproduce the P001 fixture-result audit

The report approves the two source files by their recorded SHA-256 values. It does not approve any different implementation, the historical archive, or a whole-phase result.

1. Create a new task-owned temporary directory outside the checkout. Copy `review_fixture_outcomes.py` into that directory.
2. Clone the published implementation into `source/` under that directory, check out the exact tested revision and confirm the two source hashes in `review.json`. This clone is only the fixture-review source; it is not a substitute for the anonymous two-host dependency campaign.
3. From the temporary directory, run `python3 -B review_fixture_outcomes.py`. It generates real unittest processes, exercises the actual campaign verdict path with unrelated stages neutralized, and reproduces the historical expected-failure false pass as a mutation.
4. Run `python3 -B -m unittest discover -s source/tests/compat/logic-pro/baseline -v` for all 120 integrated fixtures. Keep the new transcripts outside the checkout.

The original ten subprocess transcripts, focused suite and full fixture log are retained here unchanged. Intentional failures in those ten transcript files are negative-case inputs, not failures of the complete regression suite. `files.json` hashes every retained review asset.
