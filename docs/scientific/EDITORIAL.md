# Editorial review and navigation checks

**Reviewer E, simulated editorial review.** Inspection used the development tree based on `d2ab724`. The historical milestone dates below belong to repository records. No new participants or runtime observations were involved.

| Finding | Severity and location | Evidence, correction and outcome | Remaining limitation |
| --- | --- | --- | --- |
| E01 | Major, root README introduction and platform installation | All three development clone commands selected the earlier refactor branch. They now select `redscribe-benchmark-timeline`, the inspected branch. The root introduction links the scientific index, illustrated guide and integrated development record. | Dependency and device testing remain separate release gates. |
| E02 | Major, README validation and capabilities, benchmark and architecture indices | The introduction presented a seven-model run as pending and linked a draft PR. The integrated record records the subsequent P1 run and PR integration. Current navigation distinguishes the visible single-recording route, retained batch and pilot code, structured scoring and historical testing. Dated audit records retain their original context. | Historical execution evidence pertains to its stated code, inputs and hardware. |
| E03 | Minor, citation and version metadata | Parsed the root CFF as YAML. It declares CFF 1.2.0, software version 2.0.0, four authors and DOI `10.5281/zenodo.22941754`. The README citation uses the same version and DOI. The development target remains v2.1.0. | YAML parsing does not check the CFF schema or author identity. Confirm preferred name spellings against author records before a new archival deposit. |
| E04 | Minor, illustrated guide and samples | All six linked screenshots decoded completely with Pillow. The eight-page PDF rendered through Poppler at thumbnail resolution. The XLSX opened read-only with openpyxl. Its three sheets were Model summary (15 × 22), Recording results (8 × 34) and Efficiency (8 × 20), including header and layout rows. Both file digests matched the two published values in the sample directory README. | No desktop Excel display check. Hash agreement with the public README does not independently authenticate the closed experiment manifest or establish sharing permission. |
| E05 | Editorial, root and benchmark workflow figure | Headings and captions identify the existing academic v8 figure as a historical design. The current route is linked directly. | Rendering differences between Markdown clients remain possible. |

## Rechecking links

The repository check resolves relative inline Markdown links and image targets from the referring file, percent-decodes path components and checks local Markdown heading fragments. It excludes fenced code examples, URL schemes, remote URLs and HTML attributes. The final QA record should record the outcome after all simultaneous edits have landed. Earlier scientific documents named planned destinations before those files existed.

[Illustrated guide](../user-guide/README.md) · [Sample file checksums](../user-guide/sample-outputs/README.md) · [Consolidated historical record](../validation/CONSOLIDATED_DEVELOPMENT_RECORD_2026-11-28.md)

Final integrated scan covered 80 Markdown files and 341 local link occurrences, with zero missing targets and zero heading warnings under the scan's Markdown-link rules. The source tree and sample checks above describe local observations. External link availability and human accessibility assessment remain separate.
