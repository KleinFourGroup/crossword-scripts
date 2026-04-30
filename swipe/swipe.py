from pathlib import Path
import random

MIN_SCORE = 0.7
DISPLAY = 20

def filter(score, pre, suf):
    return score >= MIN_SCORE

def getInd(pre, suf):
    return (len(pre), len(suf))

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

def candLen(candidateDict: dict):
    num = 0
    for key in candidateDict:
        num += len(candidateDict[key])
    return num

def findCandidates(wordScores: dict[str, float]):
    words = [w for w in wordScores if len(w) >= 5]
    candidates_r = {}
    candidates_l = {}

    for word in words:
        for i in range(2, len(word) - 2):
            pre = word[:i + 1]
            suf = word[i:]
            if suf in wordScores:
                score = min(wordScores[word], wordScores[suf])
                if filter(score, pre, suf):
                    ind = getInd(pre, suf)
                    if ind not in candidates_r:
                        candidates_r[ind] = []
                    candidates_r[ind].append([score, word, pre, suf])
            suf = suf[::-1]
            if suf in wordScores:
                score = min(wordScores[word], wordScores[suf])
                if filter(score, pre, suf):
                    ind = getInd(pre, suf)
                    if ind not in candidates_l:
                        candidates_l[ind] = []
                    candidates_l[ind].append([score, word, pre, suf])
    
    return candidates_r, candidates_l

wordScores = parseWordList(Path.cwd().parent / "words.txt")
candidates_r, candidates_l = findCandidates(wordScores)

print(f"Swipe Right: {candLen(candidates_r)}")
print(f"Swipe Left: {candLen(candidates_l)}")

inds = [ind for ind in candidates_r if ind in candidates_l]

with open("possibilities.txt", "w") as f:
    for height in range(3, 7):
        for length in range(4, 7):
            ind = (height, length)
            if ind in inds:
                f.write(f"{ind} right: {len(candidates_r[ind])}\n")
                for cand in random.sample(candidates_r[ind], min(DISPLAY, len(candidates_r[ind]))):
                    f.write(f"\t{cand[0]:.3f}: {cand[1]} = {cand[2]} + {cand[3]}\n")
                f.write(f"{ind} left: {len(candidates_l[ind])}\n")
                for cand in random.sample(candidates_l[ind], min(DISPLAY, len(candidates_l[ind]))):
                    f.write(f"\t{cand[0]:.3f}: {cand[1]} = {cand[2]} + {cand[3]}\n")