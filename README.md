# InvariantSmith

An LLM reads a Python function and proposes rules it should never break.
A symbolic solver (Z3 via CrossHair) and a property-based fuzzer (Hypothesis) then try to prove each rule wrong.
Anything that breaks yields a concrete failing input, which we shrink to the smallest version that still fails.
That minimal reproduction is either a real bug or proof the proposed rule was bad.
The AI never decides what a bug is — it only proposes; the verifier decides.
We measure ourselves on BugsInPy: 493 known real bugs across 17 Python projects.
