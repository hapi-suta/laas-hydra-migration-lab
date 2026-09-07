# Recover an interrupted data generator

The instructor stops the single scale process after several committed batches. The database remains available and contains a partial dataset.

Inspect the last reported ID and current data volume. Explain which work was committed and whether replaying the command would duplicate client IDs. Resume with the same size/profile settings and verify the final exact measurement.

Then inspect a client through Hydra's admin API and authenticate a generated client using the template's demo secret in a private local process. This confirms the scaled rows are still interpretable as clients, rather than merely satisfying SQL constraints.

**Success:** no duplicate IDs, no schema changes, final size goal met, source portal remains functional. Save interruption and recovery times.
