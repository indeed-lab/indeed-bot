import Lake
open Lake DSL

package «indeed-core» where
  version := v!"0.1.0"
  leanOptions := #[⟨`warningAsError, true⟩]

lean_lib Indeed

@[default_target]
lean_exe «indeed-core» where
  root := `Main
