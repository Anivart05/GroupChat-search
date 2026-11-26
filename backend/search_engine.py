"""Semantic search over a code-mixed (English + Hinglish) group chat.

No heavy model download: queries and messages are both mapped into a shared
*concept space* via a bilingual lexicon, so "security deposit" can match
"owner ko account details bhej do" with zero shared words.  Exact-token
matching (names, places, rare words) is blended in with fuzzy spell tolerance.

Pipeline
  1. parse the query   -> sender ("what did Priya say"), time ("late January",
                          "November 14"), question intent (how much / when)
  2. extract concepts  -> weighted by rarity (IDF) in this corpus
  3. score messages    -> concept overlap x coverage + lexical overlap
  4. filter + rank     -> hard filters with automatic fallback
  5. attach context    -> +/- N surrounding messages for each hit
"""
from __future__ import annotations

import difflib
import math
import re
from collections import Counter
from datetime import datetime

from lexicon import (CONCEPTS, DATE_WORDS, MONTHS, NUMBER_WORDS, STOPWORDS,
                     stem, tokenize)

MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
PART_RANGES = {"early": (1, 10), "mid": (11, 20), "late": (21, 31)}
PART_RE = re.compile(r"\b(early|beginning of|start of|mid|middle of|late|end of)\b")
PART_MAP = {"early": "early", "beginning of": "early", "start of": "early",
            "mid": "mid", "middle of": "mid", "late": "late", "end of": "late"}


class ConceptIndex:
    """Maps stemmed tokens / phrases to concept ids."""

    def __init__(self) -> None:
        self.exact: dict[str, set[str]] = {}
        self.prefix: list[tuple[str, str]] = []
        for cid, terms in CONCEPTS.items():
            for term in terms:
                if term.endswith("*"):
                    self.prefix.append((stem(term[:-1]), cid))
                else:
                    key = " ".join(stem(w) for w in term.split())
                    self.exact.setdefault(key, set()).add(cid)
        self.max_phrase = max(len(k.split()) for k in self.exact)
        self._cache: dict[str, frozenset[str]] = {}

    def token_concepts(self, tok: str) -> frozenset[str]:
        if tok not in self._cache:
            found = set(self.exact.get(tok, ()))
            for pre, cid in self.prefix:
                if tok.startswith(pre):
                    found.add(cid)
            self._cache[tok] = frozenset(found)
        return self._cache[tok]

    def extract(self, tokens: list[str]) -> tuple[Counter, set[int]]:
        """Return concept hit counts and the token positions they consumed."""
        hits: Counter = Counter()
        used: set[int] = set()
        i = 0
        while i < len(tokens):
            matched = False
            for n in range(min(self.max_phrase, len(tokens) - i), 1, -1):
                key = " ".join(tokens[i:i + n])
                if key in self.exact:
                    for c in self.exact[key]:
                        hits[c] += 1
                    used.update(range(i, i + n))
                    i += n
                    matched = True
                    break
            if matched:
                continue
            for c in self.token_concepts(tokens[i]):
                hits[c] += 1
                used.add(i)
            i += 1
        return hits, used


def parse_temporal(q: str):
    """Pull month / day / early-mid-late out of a lower-cased query."""
    month = day = part = None
    m = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_ALT})\b", q)
    if m:
        day, month = int(m.group(1)), MONTHS[m.group(2)]
        q = q[:m.start()] + " " + q[m.end():]
    else:
        m = re.search(rf"\b({MONTH_ALT})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", q)
        if m:
            month, day = MONTHS[m.group(1)], int(m.group(2))
            q = q[:m.start()] + " " + q[m.end():]
        else:
            m = re.search(rf"\b({MONTH_ALT})\b", q)
            if m:
                month = MONTHS[m.group(1)]
                q = q[:m.start()] + " " + q[m.end():]
    if month:
        p = PART_RE.search(q)
        if p:
            part = PART_MAP[p.group(1)]
            q = q[:p.start()] + " " + q[p.end():]
    return month, day, part, q


class SearchEngine:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = sorted(messages, key=lambda m: m["timestamp"])
        self.participants = sorted({m["sender"] for m in self.messages})
        self.index = ConceptIndex()
        self.docs: list[dict] = []
        df_c: Counter = Counter()
        df_t: Counter = Counter()
        for m in self.messages:
            toks = tokenize(m["text"])
            hits, _ = self.index.extract(toks)
            dt = datetime.strptime(m["timestamp"], "%Y-%m-%d %H:%M:%S")
            tokset = set(toks)
            self.docs.append({
                "tokens": toks, "tokset": tokset, "hits": hits, "dt": dt,
                "has_num": bool(re.search(r"\d", m["text"])) or bool(tokset & NUMBER_WORDS),
                "has_date": bool(re.search(r"\d", m["text"])) or bool(tokset & DATE_WORDS),
            })
            df_c.update(hits.keys())
            df_t.update(tokset)
        n = len(self.docs)
        self.n = n
        self.idf_c = {c: math.log(1 + (n - df_c[c] + 0.5) / (df_c[c] + 0.5)) for c in CONCEPTS}
        self.df_t = df_t
        self.vocab = list(df_t)
        self._idf_t = lambda t: math.log(1 + (n - df_t[t] + 0.5) / (df_t[t] + 0.5))

    # ------------------------------------------------------------------ query
    def parse_query(self, query: str) -> dict:
        q = query.lower()
        sender = None
        for name in self.participants:
            pat = rf"\b{re.escape(name.lower())}(?:'s)?\b"
            if re.search(pat, q):
                sender = name
                q = re.sub(pat, " ", q)
        month, day, part, q = parse_temporal(q)
        wants_number = bool(re.search(r"\bhow (much|many)\b|\bkitn[ae]\b", q))
        wants_date = bool(re.search(r"\bwhen\b|\bwhat (date|time)\b|\bkab\b", q))
        tokens = [t for t in tokenize(q) if t not in STOPWORDS]
        concepts, used = self.index.extract(tokens)
        residual: dict[str, float] = {}
        for i, t in enumerate(tokens):
            if i in used:
                continue
            if t not in self.df_t:  # spelling tolerance
                close = difflib.get_close_matches(t, self.vocab, n=1, cutoff=0.82)
                if not close:
                    continue
                t = close[0]
            residual[t] = self._idf_t(t)
        shape = "attributed" if sender else "temporal" if (month or day) else "semantic"
        return {"sender": sender, "month": month, "day": day, "part": part,
                "concepts": concepts, "residual": residual, "tokens": tokens,
                "wants_number": wants_number, "wants_date": wants_date, "shape": shape}

    # ----------------------------------------------------------------- scoring
    def _score(self, d: dict, p: dict) -> tuple[float, list[str]]:
        qc = p["concepts"]
        concept_score, matched = 0.0, []
        for c in qc:
            h = d["hits"].get(c, 0)
            if h:
                concept_score += self.idf_c[c] * (1 + 0.2 * min(h - 1, 2))
                matched.append(c)
        coverage = len(matched) / len(qc) if qc else 0.0
        lexical = sum(w for t, w in p["residual"].items() if t in d["tokset"])
        total = concept_score * (0.3 + 0.7 * coverage) + 0.8 * lexical
        if total <= 0:
            return 0.0, []
        total /= 1 + 0.03 * max(0, len(d["tokens"]) - 8)
        if p["wants_number"] and d["has_num"]:
            total *= 1.15
        if p["wants_date"] and d["has_date"]:
            total *= 1.10
        return total, matched

    @staticmethod
    def _passes(d: dict, sender, month, day, part, msg_sender) -> bool:
        if sender and msg_sender != sender:
            return False
        dt = d["dt"]
        if month and dt.month != month:
            return False
        if day and dt.day != day:
            return False
        if part and not day:
            lo, hi = PART_RANGES[part]
            if not lo <= dt.day <= hi:
                return False
        return True

    # ------------------------------------------------------------------ search
    def search(self, query: str, top_k: int = 5, context_window: int = 3,
               sender: str | None = None, month: int | None = None) -> dict:
        p = self.parse_query(query)
        f_sender = sender or p["sender"]
        f_month = month or p["month"]
        scored = []
        for i, d in enumerate(self.docs):
            s, matched = self._score(d, p)
            if s > 0:
                scored.append((s, i, matched))

        def apply(filters: bool):
            if not filters:
                return scored
            return [t for t in scored if self._passes(
                self.docs[t[1]], f_sender, f_month, p["day"], p["part"],
                self.messages[t[1]]["sender"])]

        has_filter = bool(f_sender or f_month or p["day"])
        browse = False
        if not p["concepts"] and not p["residual"] and has_filter:
            # Nothing to rank by ("what was planned on November 14"): browse the
            # filtered slice chronologically instead of returning nothing.
            scored = [(0.001, i, []) for i in range(len(self.docs))]
            browse = True
        pool, relaxed = apply(True), False
        if not pool and has_filter:
            pool, relaxed = scored, True
        pool.sort(key=lambda t: (-t[0], t[1]))

        hits = []
        for s, i, matched in pool[:top_k]:
            lo, hi = max(0, i - context_window), min(len(self.messages), i + context_window + 1)
            hits.append({
                "message": self.messages[i],
                "score": round(s, 3),
                "matched_concepts": matched,
                "thread": [{**self.messages[j], "is_target": j == i} for j in range(lo, hi)],
            })
        return {
            "query": query,
            "intent": {
                "query_shape": p["shape"],
                "sender": f_sender,
                "month": f_month,
                "day": p["day"],
                "part": p["part"],
                "concepts": sorted(p["concepts"]),
                "exact_terms": sorted(p["residual"]),
                "filters_relaxed": relaxed,
                "browse_mode": browse,
            },
            "total_candidates": len(pool),
            "hits": hits,
        }
