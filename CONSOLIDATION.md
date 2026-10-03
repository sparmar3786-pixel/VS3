# VS3 Consolidated Source

VS3 is a single consolidated project assembled from the accessible Vandana/VS repositories and selected branches.

## Rules used
- One canonical path per active implementation; repeated source files were not copied again.
- Native Android Kotlin is the APK path; Flutter/Dart build pipelines are not used for the APK.
- The 32-stage option-analysis pipeline and six-layer AI source are retained.
- Angel One, NSE/MCP, strategy, quant, frontend, tests, deployment and design-reference files are retained where they add distinct functionality.
- Reference-only files are isolated under `reference/` or `legacy_reference/` so they cannot silently replace active code.
- Secrets and broker credentials are not embedded.

## Source families
Vandana1, Vandana2, Vandana3, Vandana4, VSP1 and VandanaS1 were inspected. VS1 and VS2 are currently empty repositories, so there were no source files to import from them.
