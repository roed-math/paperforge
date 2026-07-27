/-!
Minimal fixture "formalization": plain text files the declaration-map miner
scans (no Lean toolchain needed — iter_decls reads source). Exercises both
citation disciplines: a docstring header (**Theorem 1.2.**) and a
name-encoded citation (lem_2_1), plus an axiom and a private declaration.
-/

namespace Minimal

/-- **Theorem 1.2.** Every widget is trivial. -/
theorem main_widget_trivial : True := trivial

/-- The supporting lemma. -/
theorem lem_2_1 : True := trivial

/-- A classical input the paper cites rather than proves. -/
axiom classical_input : True

/-- Support code with no paper-side statement. -/
private def helper : Nat := 0

end Minimal
