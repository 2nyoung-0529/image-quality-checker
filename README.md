# Image Quality Checker

A small, transparent pre-QC tool for image datasets. It scans a folder, records
basic metadata, finds byte-identical duplicates and routes obvious issues into
`PASS`, `REVIEW`, `DROP` or `ERROR` queues.

This project is a refactoring of an earlier QC script. The goal is not to replace a
human reviewer or claim model-based image understanding; it is to make repetitive,
deterministic checks reproducible before manual inspection.

## Checks

| Check | Result | Meaning |
|---|---|---|
| Minimum width/height | `DROP` | Image is below a configured dimension |
| SHA-256 exact duplicate | `DROP` | File bytes match an earlier file |
| Mean brightness threshold | `REVIEW` | Image may be unusually dark or bright |
| Decode failure | `ERROR` | File cannot be fully decoded as an image |
| No issue found | `PASS` | No configured rule was triggered |

`DROP` is a workflow recommendation based on configured rules, not deletion. The
program never modifies source images.

## Quick start

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
image-quality-check /path/to/images --output output/results.csv
```

Scan subdirectories and use a configuration file:

```bash
image-quality-check /path/to/images \
  --recursive \
  --config config.example.json \
  --output output/results.csv
```

Without installation, set the source path explicitly:

```bash
PYTHONPATH=src python -m image_quality_checker /path/to/images
```

The command returns `0` after a completed scan and `2` for invalid input,
configuration or output errors. Individual unreadable images are recorded as
`ERROR` rows so that one bad file does not stop a batch.

## Configuration

Copy `config.example.json` and adjust it for the dataset. CLI `--recursive`
overrides the corresponding JSON value to `true`. Unknown keys and invalid
threshold ranges fail early instead of being ignored.

Brightness is the grayscale mean on a 0–255 scale. Thresholds are dataset-specific;
the defaults are demonstration values, not universal quality standards.

## Output

The UTF-8 CSV includes the relative path, dimensions, color mode, file size,
brightness, SHA-256 hash, duplicate owner, status and reasons. See
[`samples/sample_results.csv`](samples/sample_results.csv) for a synthetic example.
Hashes in that example are placeholders, not real file digests.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The tests create temporary synthetic images and cover low resolution, brightness,
duplicates and unreadable files.

## Limitations

- Duplicate detection is exact; resized or recompressed near-duplicates are not found.
- Mean brightness cannot distinguish intentional silhouettes, night scenes or local
  exposure problems. Candidates therefore go to `REVIEW`, not `DROP`.
- Blur, occlusion and semantic suitability are outside the current deterministic scope.
- Rule thresholds should be validated against each dataset and QC policy.

## Repository structure

```text
image-quality-checker/
├── src/image_quality_checker/  # reusable package and CLI
├── tests/                      # synthetic unit tests
├── samples/                    # example output only
├── docs/review.md              # comparison with the original versions
├── config.example.json
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Privacy and data handling

The tool runs locally and does not upload images. Real source images and generated
outputs are intentionally excluded from this repository; verify usage rights before
publishing any dataset samples.

## License

No license is included by default. Add one only after choosing terms appropriate for
your portfolio and any third-party assets.
