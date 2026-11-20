# Greyquill — Customer Record Pair Scoring

A standard-library Python implementation of the `score_pair` function supplied in the Greyquill Forward Deployed Engineer Intern task.

## Requirements

- Python 3.10 or newer
- No third-party packages required

## Run one comparison

Place the task-provided `customer-records.csv` in this folder, then run:

```bash
python score_pair.py customer-records.csv R0087 R0126
```

Replace the two record IDs with any valid `record_id` values from the CSV. The program prints a JSON result containing the confidence score, methods used, and per-field scores.

## Approach

- **Missing values:** If either side is blank or missing, that field is omitted from both `field_scores` and the weighted average.
- **Name / phonetic:** Split names into tokens, normalize case and accents, support `Surname, Given` ordering, compare tokens independent of order, award partial credit for initials, and use Soundex as an additional phonetic signal. Unmatched extra tokens are penalized.
- **Email / edit distance:** Normalize case and whitespace, then use `difflib.SequenceMatcher` to produce a similarity ratio from 0 to 1.
- **Phone / normalized phone:** Remove the India country prefix (`+91` or `91` where applicable), punctuation, spaces, hyphens, and one leading zero before comparing digits.
- **Date:** Parse the date formats used in the supplied dataset and compare calendar dates.
- **Exact:** Trim whitespace and compare case-insensitively.
- **Confidence:** Calculate the weighted average using only fields that were compared. If no fields can be compared, return 0.0. The result is clamped to the 0–1 range.

## Example pair

I selected **R0087** and **R0126**. Both records use the exact name “Nandini Sharma” and the same city, Gurgaon, so they appear similar at first glance. However, their dates of birth, phone numbers, PIN codes, and email addresses differ, which strongly suggests that they represent different people rather than the same customer entered twice.

## Data handling

The customer CSV is not included in this repository. Keep the file provided by Greyquill locally and do not publish customer records unless Greyquill explicitly authorizes it.

## AI assistance disclosure

ChatGPT was used to help review the task requirements, discuss the matching approach, and test the implementation against the supplied CSV. The implementation and scoring decisions should be reviewed and understood by the submitter before submission.
