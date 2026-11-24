# Native segment preservation

Benchmark-only change. Preserve adapter-emitted segment text and available start/end fields in a separate JSON file with SHA-256. Existing strip/join scoring assembly is unchanged. This is adapter output, not necessarily raw model tokens. Partial segments on failure/cancellation are not yet persisted. CI pending. Target branch: redscribe-benchmark-timeline, not main.
