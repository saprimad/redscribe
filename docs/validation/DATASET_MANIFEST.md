# Dataset manifest and pairing validation

Local API: inspect_pairs, approve_dataset, verify_dataset. Explicit participant IDs and manually paired audio plus approved reference manifest. Reject duplicate IDs, identical audio or source DOCX hashes, missing files and unexpected count when supplied. Recheck hashes before use. Exclusive manifest creation. Hashes cannot establish semantic pairing; researcher must listen/review. No automatic filename matching. GUI and batch-runner integration pending; no private files in GitHub. CI pending.
