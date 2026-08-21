# Original code review

## Version comparison

`image_quality_check01.py` is the more complete of the two originals. It keeps the
resolution, corruption and exact-duplicate checks from `image_quality_check.py`,
then adds deterministic file ordering, average-brightness candidates, a `REVIEW`
state and a filename heuristic that prefers a file without `_copy`.

## Issues addressed

- Input/output paths and thresholds were module-level constants with no CLI.
- Functions lacked complete type hints and reusable result/config models.
- The first version depended on directory iteration order for duplicate ownership.
- The `_copy` filename rule was brittle and required repeatedly scanning results.
- MD5 was adequate for accidental duplicates but SHA-256 is clearer for public use.
- Image opening did not explicitly force a complete decode with `load()`.
- Brightness calculation reopened every image and silently swallowed all exceptions.
- Errors were printed or hidden rather than logged with a reliable exit code.
- Pandas was used only to write CSV, adding an unnecessary dependency.
- There were no tests, package metadata, usage guide or documented limitations.

## Deliberate scope

The revised project does not claim that brightness equals semantic quality. Uniform
thresholds can flag candidates for review, while blur, occlusion, subject visibility
and task-specific suitability still require domain-aware review or a validated model.
