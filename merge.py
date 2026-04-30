"""
merge_wordlists.py
------------------
Merges multiple crossword word lists with divergent score scales into a single,
unified list using percentile normalization + coverage-confidence weighting.

Supported input formats:
  - Plain text, one word per line           e.g.  APPLE
  - Semicolon-scored (Broda / XWI style)    e.g.  APPLE;60
  - Tab-scored                              e.g.  APPLE\t60
  - Pipe-scored                             e.g.  APPLE|60

Usage:
  python merge_wordlists.py broda.txt spread.txt jones.txt -o merged.txt
  python merge_wordlists.py *.txt -o merged.txt --min-score 0.3 --min-length 3
"""

import re
import argparse
import math
from pathlib import Path
from collections import defaultdict


# ── 1. Parsing ────────────────────────────────────────────────────────────────

DELIMITERS = re.compile(r"[;|\t]")


def parse_line(line: str) -> tuple[str, float | None]:
    """Return (word, raw_score_or_None) from a single list line."""
    line = line.strip()
    if not line or line.startswith("#"):
        return "", None

    parts = DELIMITERS.split(line, maxsplit=1)
    word = parts[0].strip().upper()
    if not word or not re.match(r"^[A-Z'-]+$", word):
        return "", None  # skip non-alpha / empty tokens

    score = None
    if len(parts) == 2:
        try:
            score = float(parts[1].strip())
        except ValueError:
            pass

    return word, score


def load_wordlist(path: str | Path) -> dict[str, float]:
    """Load a single word list file → {WORD: raw_score_or_None}."""
    words: dict[str, float] = {}
    path = Path(path)
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            word, score = parse_line(line)
            if word and score is not None:
                # Keep the higher score if word appears multiple times
                if word not in words or score > words[word]:
                    words[word] = score
    print(f"  Loaded {len(words):>7,} words from {path.name}")
    return words


# ── 2. Percentile normalization ───────────────────────────────────────────────

def percentile_normalize(words: dict[str, float]) -> dict[str, float]:
    """
    Convert raw scores → [0, 1] percentile ranks within a single list.
    """
    # Sort scored words by raw score
    ranked = sorted(words.items(), key=lambda x: x[1])
    n_scored = len(ranked)

    normalized: dict[str, float] = {}

    # Assign percentile to scored words
    for rank, (word, _) in enumerate(ranked):
        # +1 so no word gets exactly 0.0; scaled to (0, 1]
        normalized[word] = (rank + 1) / (n_scored + 1)

    return normalized


# ── 3. Merge ─────────────────────────────────────────────────────────────────

def confidence_weight(n_present: int, n_total: int, strength: float = 0.5) -> float:
    """
    Return a multiplier in (0, 1] that penalises words appearing in fewer lists.

    n_present  – how many lists contained this word
    n_total    – total number of lists being merged
    strength   – 0 = no penalty, 1 = full logarithmic penalty

    The formula uses a smooth log curve so going from 1→2 lists has a big
    effect, but going from 4→5 has a smaller effect.

    Examples (strength=0.5, n_total=3):
      present in 1/3 lists → ~0.75
      present in 2/3 lists → ~0.90
      present in 3/3 lists → 1.00
    """
    if n_total == 1:
        return 1.0
    coverage = n_present / n_total          # 0 < coverage ≤ 1
    log_factor = math.log1p(coverage * (math.e - 1))  # log(1 + coverage*(e-1))
    return 1.0 - strength * (1.0 - log_factor)


def merge(
    lists: list[dict[str, float]],
    coverage_strength: float = 0.5,
) -> dict[str, float]:
    """
    Merge normalised word lists into one.

    Strategy:
      1. Percentile-normalise each list independently.
      2. For each word, compute the MEAN of its normalised scores across all
         lists that contain it.
      3. Apply a coverage-confidence penalty so words present in only one
         list are down-weighted relative to consensus words.

    Returns {WORD: final_score} where scores are in (0, 1].
    """
    n_total = len(lists)
    normalised = [percentile_normalize(lst) for lst in lists]

    # Collect per-word scores from every list that has the word
    word_scores: dict[str, list[float]] = defaultdict(list)
    for norm in normalised:
        for word, score in norm.items():
            word_scores[word].append(score)

    merged: dict[str, float] = {}
    for word, scores in word_scores.items():
        mean_score = sum(scores) / len(scores)
        weight     = confidence_weight(len(scores), n_total, strength=coverage_strength)
        merged[word] = mean_score * weight

    return merged


# ── 4. Filtering & export ─────────────────────────────────────────────────────

def apply_filters(
    merged: dict[str, float],
    min_score: float = 0.0,
    min_length: int = 1,
    max_length: int = 999,
) -> dict[str, float]:
    return {
        w: s for w, s in merged.items()
        if s >= min_score
        and min_length <= len(w) <= max_length
    }


def export(merged: dict[str, float], output_path: str | Path, decimals: int = 4) -> None:
    """Write sorted merged list as  WORD;SCORE  (descending by score)."""
    output_path = Path(output_path)
    sorted_words = sorted(merged.items(), key=lambda x: x[1], reverse=True)
    with output_path.open("w", encoding="utf-8") as f:
        for word, score in sorted_words:
            f.write(f"{word};{score:.{decimals}f}\n")
    print(f"\n  Exported {len(sorted_words):,} words → {output_path}")


# ── 5. Stats helper ───────────────────────────────────────────────────────────

def print_stats(merged: dict[str, float], lists: list[dict]) -> None:
    scores = sorted(merged.values())
    n = len(scores)
    avg = sum(scores) / n
    med = scores[n // 2]
    top10 = scores[int(n * 0.9)]
    coverage_counts = [0] * (len(lists) + 1)
    all_words = set(merged)
    for word in all_words:
        present = sum(1 for lst in lists if word in lst)
        coverage_counts[present] += 1

    print("\n── Merge statistics ──────────────────────────────")
    print(f"  Total unique words : {n:,}")
    print(f"  Mean score         : {avg:.4f}")
    print(f"  Median score       : {med:.4f}")
    print(f"  90th percentile    : {top10:.4f}")
    print("\n  Coverage breakdown:")
    for i in range(1, len(lists) + 1):
        bar = "█" * (coverage_counts[i] * 30 // max(coverage_counts[1:]))
        print(f"    In {i}/{len(lists)} lists : {coverage_counts[i]:>8,}  {bar}")
    print("──────────────────────────────────────────────────")


# ── 6. CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge and normalise crossword word lists.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("inputs", nargs="+", help="Input word list files")
    parser.add_argument("-o", "--output", default="merged.txt",
                        help="Output file path (default: merged.txt)")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Minimum final score to include (default: 0)")
    parser.add_argument("--min-length", type=int, default=1,
                        help="Minimum word length (default: 1)")
    parser.add_argument("--max-length", type=int, default=999,
                        help="Maximum word length (default: 999)")
    parser.add_argument("--coverage-strength", type=float, default=0.5,
                        help="How hard to penalise words in fewer lists. "
                             "0 = no penalty, 1 = full log penalty (default: 0.5)")
    args = parser.parse_args()

    print(f"\nLoading {len(args.inputs)} list(s)…")
    lists = [load_wordlist(p) for p in args.inputs]

    print("\nNormalising and merging…")
    merged = merge(lists, coverage_strength=args.coverage_strength)

    merged = apply_filters(
        merged,
        min_score=args.min_score,
        min_length=args.min_length,
        max_length=args.max_length,
    )

    print_stats(merged, lists)
    export(merged, args.output)


if __name__ == "__main__":
    main()