# Failure recovery audit

Cross-platform integration CI at 876a99b succeeded. Batch runner currently checkpoints but explicitly does not support resume. Do not claim crash recovery or automatic resume. Added cancellation and secondary report failure regression; batch checks approved reference hash again before each recording. Secondary reporting failures no longer abort checkpointing. Hard process termination, per-model resume, long-recording performance and GUI remain open. Tests use mocked inference.
