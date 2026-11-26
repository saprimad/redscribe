# Live resume restoration
After dataset and checkpoint identity verification, the runner verifies completed prediction hashes and recomputed metrics and emits completed or pending progress events. Scheduler rechecks verified cells before skipping. Cancellation remains cooperative. No claim of hard-kill recovery or concurrent writer safety. GUI runtime and event tests pending.
