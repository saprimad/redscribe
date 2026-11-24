# Prediction integrity audit

Finding: the pilot scored joined segment text in memory but appended a newline when exporting TXT. On Windows text-mode newline conversion could further change bytes. Fix: save exact UTF-8 scoring input before scoring, refuse overwrite, read back and verify bytes, record file name, SHA-256 and byte length in model result. Empty predictions remain valid. Regression tests cover whitespace, CRLF, Unicode, empty text and overwrite refusal.

Scope: this freezes the assembled scoring prediction, not native ASR segment output. Existing segment stripping/joining remains unchanged pending explicit protocol review. Crash-safe persistence, batch resume verification, offline re-scoring and native segment preservation remain pending. No participant data used. CI result pending at commit time.
