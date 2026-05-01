from pathlib import Path
import random

MIN_LEN = 7
MAX_LEN = 10

MIN_SCORE = 0.7
DISPLAY = 20

VOWELS = "AEIOU"

CONSONANT_PENALTY = 1.75
VOWEL_PENALTY = 1.5

MAX_PENALTY = 4

def parseWordList(fname):
    wordScores: dict[str, float] = {}
    with open(fname, "r") as f:
        for line in f:
            parts = line.strip().split(";")  # common delimiter
            if len(parts) == 2:
                word, score = parts[0].strip().upper(), float(parts[1].strip())
                wordScores[word] = score
    print(f"Loaded {len(wordScores)} words")   
    return wordScores

def scoreFilter(scores: dict[str, float], minScore: float):
    filtered = {word: scores[word] for word in scores if scores[word] >= minScore}
    print(f"Found {len(filtered)} words with score at least {minScore}")
    return filtered

def lengthFilter(scores: dict[str, float], minLen: int, maxLen: int):
    candidates: dict[int, dict[str, float]] = {}
    for word, score in scores.items():
        if len(word) >= minLen and len(word) <= maxLen:
            if len(word) not in candidates:
                candidates[len(word)] = {}
            candidates[len(word)][word] = score
    return candidates

def alternatingScore(word: str):
    state = word[0] in VOWELS
    score = 0
    penalty = 0
    for ind in range(1, len(word)):
        isVowel = word[ind] in VOWELS
        multiplyer = VOWEL_PENALTY if isVowel else CONSONANT_PENALTY
        if state == isVowel:
            if penalty == 0:
                penalty = multiplyer
            else:
                penalty *= multiplyer
        else:
            score += penalty
            penalty = 0
        state = isVowel
    score += penalty
    return score

def rescore(scores: dict[str, float], maxPenalty: float):
    results: dict[str, float] = {}
    for word in scores:
        penalty = alternatingScore(word)
        if penalty <= maxPenalty:
            results[word] = penalty
    return results

wordScores = parseWordList(Path.cwd().parent / "words.txt")
candidates = lengthFilter(scoreFilter(wordScores, MIN_SCORE), MIN_LEN, MAX_LEN)
remainder = 0
penalized: dict[int, dict[str, float]] = {}
for length in candidates:
    penalties = rescore(candidates[length], MAX_PENALTY)
    penalized[length] = penalties
    remainder += len(penalties)
print(f"Found {remainder} words with penalty at most {MAX_PENALTY}")

with open("possibilities.txt", "w") as f:
    for length in range(MIN_LEN, MAX_LEN + 1):
        if len(penalized[length]) > 0:
            f.write(f"Length {length} ({len(penalized[length])}):\n")
            for word in random.sample(list(penalized[length].keys()), min(DISPLAY, len(penalized[length]))):
                f.write(f"\t{word}: {penalized[length][word]:.2f} {candidates[length][word]}\n")