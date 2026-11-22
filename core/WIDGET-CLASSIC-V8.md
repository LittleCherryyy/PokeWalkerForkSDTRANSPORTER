# Widget Classic V8 - orphaned sync recovery

Fixes a V7 regression where a failed return could persist `returnPending=true` while the process-local `syncing` flag was lost. That state blocked all Classic buttons and stopped the 400 ms Pokemon animation.

V8 automatically repairs an active walker when `returnPending=true` but there is no active sync: it clears the pending return, restores walking mode, clears stale widget status, resets Classic UI state to HOME, and resumes animation. The transfer service also always unlocks a failed local return before saving.
