# Harness change requests from Track A

## Atomic cache writes in AnthropicModel (2026-08-10)

`_write_cache` uses `Path.write_text`, which is not atomic. A reader in a
concurrent process can see a partially written file and crash on JSON parse
(observed 2026-08-10: the Track B ladder startup read a cache entry mid-write
and died; a follow-up scan found zero corrupt files, confirming a transient
read-during-write race, not durable corruption). Two asks:

1. Write to a temp file in the same directory and `os.replace` into place.
2. Treat unparseable cache entries as misses in `_read_cache` (delete and
   refetch) instead of raising.

Workaround until then: never run two spending processes against the same
cache directory concurrently.
