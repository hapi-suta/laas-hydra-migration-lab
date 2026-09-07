# Practice incidents with a known recovery boundary

A useful incident exercise changes one identifiable condition, preserves its previous state, and defines an independent validation. Random breakage makes it difficult to distinguish a lesson from an unrecoverable environment.

The executable local incident controller supports two reversible service failures: source Hydra stopped and gateway stopped. The cloud exercises additionally cover DMS connectivity, task interruption, LOB configuration, missing table selection, and pre-write cutover aborts.

Use a small dataset for diagnosis practice, then select a subset of failures to repeat at full scale. Always identify whether a repair requires task resume, table reload, or full restart; these operations have different effects on a prepared target.

A passing health endpoint proves reachability only. Validation should also exercise the failed capability: token refresh for an authentication incident, an observed replicated update for CDC recovery, and an all-row comparison for data-integrity recovery.

Record the first signal, the hypothesis, evidence that rules alternatives out, the exact fix, and prevention. Avoid changes that accidentally repair several things at once, such as deleting all data and reinstalling the stack.

Cloud incident injection is confined to resources tagged for this practice project. Capture the original resource configuration and restore it after each exercise. Never run Terraform destroy or a broad security-group change as a diagnostic step.
