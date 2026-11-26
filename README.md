# Search a Group Chat Properly

> "When did we decide on Manali?" You know the message exists. It's somewhere in four thousand messages, and you don't remember the words — someone probably typed *"sabka vote manali ko gaya, pakka hua"*. Searching "decide" returns nothing; searching "Manali" returns two hundred results.

A semantic search engine for **code-mixed English + Hinglish** group chats. It finds messages by *meaning*, shows them in their surrounding conversation, and understands who said it and when.

## Features

- **Three query shapes**
  - *Semantic* — "who agreed to pay the security deposit"
  - *Attributed* — "what did Priya say about the budget"
  - *Temporal* — "what wifi installation was scheduled in late January", "who is collecting money on November 14" (a date with no topic words just browses that day)
- **Zero-keyword-overlap matching** — the query and the answer can share no words at all (`"who is driving during the vacation"` → `"scorpio main chalaunga, baaki log aaram se baithna"`).
- **Conversation context** — every hit is shown with ±N surrounding messages, speaker avatars and the target highlighted.
- **Explainable** — each result lists the concepts that matched, and the UI shows how the query was parsed (person, month, concepts, exact terms).
- **Typo tolerant** for names and rare words (fuzzy matching).
- **No model download, no GPU** — pure Python, starts instantly.

## How it works

```
query ──► parse ──► concepts ──► score ──► filter ──► rank ──► +context
          sender    (bilingual   concept     sender/    top-k
          month/day  lexicon,     overlap ×  month/day
          intent     IDF-weighted) coverage  (auto-relax if
                                   + exact    nothing matches)
                                   words
```

1. **Query parsing** (`backend/search_engine.py`) pulls out a participant name, a month / day / early-mid-late, and intent (*how much* favours messages with numbers, *when* favours messages with dates).
2. **Concept space** (`backend/lexicon.py`) — a hand-built bilingual lexicon of ~45 concepts. *deposit* ↔ `advance, owner, account details`; *rent* ↔ `kiraya, divide, har ek`; *drive* ↔ `scorpio, chalaunga, gaadi`. Queries and messages are both mapped into it, so words never need to match. Prefix rules (`bhej*`, `mangwa*`) handle Hinglish verb endings; a light stemmer collapses spelling variants (`haan/han`).
3. **Scoring** — each matched concept contributes its IDF in this corpus (rare concepts count more), multiplied by how many of the query's concepts the message covers, plus a lexical score for exact rare words (names, places). Short messages get a mild boost.
4. **Filters** — person/month/day filters are hard, but automatically relaxed if they would return nothing.

## Quickstart

```bash
pip install -r requirements.txt

python data/generate_corpus.py      # (optional) regenerate the dataset
python evaluate.py                  # run the 40-query benchmark

python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
# open http://127.0.0.1:8001
```

## Dataset

`data/generate_corpus.py` deterministically generates **4,400 messages**, **8 participants**, **2025-10-01 → 2026-03-31**:

- random everyday chatter, including many *distractors* that reuse topic words ("trip", "rent", "deposit", "presentation") without being the answer
- three scripted decision threads: **Winter Manali trip** (Nov–Dec), **Bangalore flat hunt** (Jan), **Hackathon MVP** (Feb–Mar)

## Benchmark (40 queries)

```
Top-1:            33/40  (82.5%)
Recall@5:         39/40  (97.5%)
MRR:              0.875
Zero-overlap R@5: 29/30
```

| Shape | n | Top-1 | Recall@5 |
|---|---|---|---|
| semantic | 20 | 18 | 19 |
| attributed | 10 | 7 | 10 |
| temporal | 10 | 8 | 10 |

### Honest caveats

- The corpus is **synthetic** and the lexicon was written by the same author as the test set, so these numbers show the approach works on this data, not that it generalises to your real chat. Expect lower numbers on real exports.
- Remaining misses are mostly genuine ambiguity: e.g. *"did we win the hackathon"* competes with every message that says someone "jeet gaye" a cricket match.
- A query concept missing from the lexicon falls back to exact-word matching.

## API

`POST /api/search`
```json
{"query": "who agreed to pay the security deposit", "top_k": 5, "context_window": 3, "sender": null, "month": null}
```
Returns `intent` (how the query was parsed), and `hits[]` with `message`, `score`, `matched_concepts`, and `thread` (surrounding messages, `is_target` flagged).

Also: `GET /api/meta`, `GET /api/benchmark`.

## Project layout

```
backend/   lexicon.py · search_engine.py · benchmark.py · main.py (FastAPI)
frontend/  index.html (single-file dashboard)
data/      generate_corpus.py · chat_messages.json · test_queries.json
evaluate.py
```

## Ideas to extend

- Add a multilingual embedding model (e.g. `paraphrase-multilingual-MiniLM`) and blend its cosine score with the concept score.
- Learn the lexicon automatically from co-occurrence in a real chat.
- Import a real WhatsApp export (`DD/MM/YYYY, HH:MM - Name: text`) instead of the synthetic corpus.
