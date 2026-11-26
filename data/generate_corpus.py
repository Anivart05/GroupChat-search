"""Generate the synthetic Hinglish group-chat corpus and the 40-query benchmark.

    python data/generate_corpus.py

Output (deterministic, seed fixed):
    data/chat_messages.json   ~4,400 messages, 8 people, 2025-10-01 -> 2026-03-31
    data/test_queries.json    40 ground-truth queries (zero-overlap flag computed)

The chat = lots of random everyday chatter (incl. many *distractors* that reuse
words like "trip", "rent", "deposit", "presentation" without being the answer)
+ three scripted decision threads: Manali trip, Bangalore flat hunt, hackathon MVP.
"""
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from lexicon import STOPWORDS, tokenize  # noqa: E402

rnd = random.Random(7)

START = datetime(2025, 10, 1)
DAYS = 182
PEOPLE = {"Rohan": 1.3, "Priya": 1.1, "Kabir": 1.3, "Ananya": 1.0,
          "Vikram": 0.9, "Neha": 0.8, "Arjun": 1.0, "Sneha": 0.9}
HOUR_W = [1, 0.5, 0.2, 0.1, 0.1, 0.2, 0.6, 1.2, 1.5, 1.6, 1.8, 2, 2.2, 2, 1.8, 1.8, 2,
          2.4, 2.8, 3.4, 4, 4.4, 3.6, 2]

# ----------------------------------------------------------------- filler chatter
POOLS = {
    "food": ["maggi", "pizza", "momos", "chai samosa", "biryani", "paneer roll", "burger",
             "dosa", "chole bhature", "pasta"],
    "player": ["Kohli", "Bumrah", "Gill", "Rohit", "Jadeja", "Pant", "Siraj"],
    "movie": ["Jawan", "Dunki", "Tumbbad", "Animal", "Stree 2", "Laapataa Ladies", "Kalki"],
    "thing": ["assignment", "report", "timesheet", "form", "lab file", "invoice"],
    "weather": ["garmi", "barish", "thand", "dhup", "humidity"],
    "place": ["canteen", "cafe", "library", "parking", "gate ke paas", "terrace"],
    "show": ["Panchayat", "Mirzapur", "Kota Factory", "Scam 1992", "Made in Heaven"],
    "tool": ["django", "node", "react", "docker", "git", "excel"],
    "n": ["100", "200", "250", "300", "500", "40", "60", "150"],
}
REACT = ["haha", "lol", "sahi hai", "ok", "theek hai", "arre yaar", "bhai kya baat hai", "nice",
         "mast", "ho jayega", "pata nahi yaar", "dekhte hai", "😂😂", "ruk 5 min",
         "kal baat karte hai", "same here", "bilkul", "hmm", "accha", "pagal hai tu",
         "chal theek", "bas kar bhai", "👍", "🔥🔥", "wah wah", "kya scene hai", "sach mein?",
         "nahi yaar", "abhi busy hu", "arey wah", "mazaa aa gaya", "chill kar"]
GENERAL = [
    "good morning sabko", "gm", "gn sab log", "subah subah uth gaye kya", "kaun jaag raha hai",
    "so ja bhai", "chai pi?", "aaj {weather} bohot hai yaar", "kal ka match dekha? {player} ne kya khela",
    "{movie} dekhi kisi ne?", "{show} ka naya season aa gaya hai", "kal {thing} jama karna hai, bhool mat jana",
    "office mein aaj bohot kaam tha", "ye reel dekh, hasi nahi ruk rahi", "https://youtu.be/dQw{n}xyz",
    "{food} khaane chale kya aaj?", "{place} mein milte hai 5 min mein", "kisi ke paas charger hai?",
    "mera phone hang ho raha hai yaar", "{tool} seekh raha hu aajkal, bohot mazaa aa raha hai",
    "kal subah jaldi uthna hai, alarm laga lo", "bhai {n} rupaye udhaar chahiye, kal de dunga",
    "aaj gym gaya tha, haath dukh rahe hai", "metro mein itni bheed thi aaj", "can someone share the notes pls",
    "reminder: submit the {thing} by tonight", "wifi nahi chal raha yaar, hotspot de na",
    "mausam kitna accha ho gaya hai", "kal holiday hai kya?", "sunday ko cricket khelte hai?",
    "meme bheji hai group mein dekh lo", "kisne mera hoodie liya?", "aaj ka khana bekar tha",
    "interview ke liye dua karo yaar", "neend nahi aa rahi, kuch interesting bolo",
    "ye song sun, bohot mast hai", "bhai {place} pe koi hai?", "traffic mein phans gaya hu",
    "birthday hai kal kisi ka? yaad nahi aa raha", "photo bhej na kal ki", "sab theek? kaafi din se chup ho",
]
# Distractors: reuse topic words but are *not* the decision/answer messages.
DISTRACTORS = [
    "manali ki photos dekhi insta pe, kya jagah hai", "trip ka plan kya hua? koi update?",
    "goa ke reels dekh dekh ke mann ho raha hai", "mera driving test kal hai, dua karo",
    "gaadi service pe di hai, kal milegi", "wo hotel ka review dekha? bekar tha", "room ki chaabi kisne li?",
    "mera kiraya due hai, kal dena hai", "pg ka rent badhne wala hai pata chala?", "phone ka budget 20k hai bas",
    "is mahine ka kharcha bahut ho gaya", "ye broker log loot rahe hai sach mein", "didi aaj nahi aayi, khana khud banana padega",
    "wifi bill kaun bharega is baar?", "internet slow hai aaj", "presentation ka kaam bacha hai abhi office mein",
    "slides bhejna zara, kal chahiye", "django ka error aa raha hai samajh nahi aa raha", "sql ka assignment hai kal tak",
    "mongo seekhna hai ek din", "kal milte hai canteen mein", "kahan mil raha hai sab?", "jacket purani ho gayi, nayi leni hai",
    "aaj thand badh gayi hai bohot", "swiggy order kiya tha kal, bakwaas tha", "swiggy pe pizza offer chal raha hai",
    "zomato ka order late aaya yaar", "kabhi aisa lagta hai deposit wapas hi nahi aayega", "security guard ne rok liya aaj",
    "gpay pe 200 bhej diye chai ke", "paytm cashback aaya kya?", "paisa kab milega yaar salary late hai",
    "naya domain leke blog banana hai", "website ka design kaisa laga mera?", "meeting 11 baje hai, laptop ready rakho",
    "demo kaisa raha kal ka? sab theek?", "party kab de raha hai tu?", "kal kaun kaun aa raha hai? pakka batao",
    "mujhe toh kuch pakka nahi pata", "tickets sold out ho gaye movie ke", "train late hai aaj phir se",
    "car ki battery down ho gayi", "hostel mein bijli gayi hui hai", "pitch deck ke liye template mil gaya kya?",
    "kya server down hai? app nahi khul raha", "python ka code run nahi ho raha", "bill bhar diya maine apna",
    "aadhar update karana hai kal", "passport renew hona hai is saal", "help chahiye yaar thoda sa",
    "jeet gaye hum match, mazaa aa gaya", "kal reach kar jaunga office", "winter aa gaya, subah uthna mushkil",
]
ENGLISHY = [
    "bro i'm so tired today", "anyone free this weekend?", "just reached home finally", "this is so funny 😂",
    "can we do a quick call?", "send me the pic na", "what's the plan for tonight?", "lunch pe kya hai aaj",
    "i'll be late by like 10 mins", "wait what? when did this happen", "ok cool see you all tomorrow",
]


def fill(tpl: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: rnd.choice(POOLS[m.group(1)]), tpl)


def rand_ts() -> datetime:
    d = START + timedelta(days=rnd.randrange(DAYS))
    h = rnd.choices(range(24), HOUR_W)[0]
    return d.replace(hour=h, minute=rnd.randrange(60), second=rnd.randrange(60))


def sender() -> str:
    return rnd.choices(list(PEOPLE), list(PEOPLE.values()))[0]


# ------------------------------------------------------------- scripted threads
# (key, "MM-DD", "HH:MM", sender, text). key=None -> context only.
SCRIPT = [
    # ---- Winter Manali trip ----
    (None, "11-09", "21:10", "Rohan", "yaar december mein kahin ghoomne chalte hai, kuch plan banao"),
    (None, "11-09", "21:12", "Kabir", "goa ya manali? mujhe toh pahadon ka mann hai"),
    (None, "11-09", "21:15", "Priya", "goa mein december mein bheed bohot hoti hai, mehnga bhi padega"),
    (None, "11-09", "21:18", "Sneha", "manali mein snow milegi, main kuch options dekhti hu"),
    (None, "11-09", "21:25", "Rohan", "voting kar lete hai, manali ke liye haath uthao 🙋"),
    ("k01", "11-09", "21:31", "Rohan", "sabka vote manali ko gaya, toh pakka hua. 18 se 22 december ka plan"),
    ("k15", "11-10", "16:00", "Sneha", "chalet ke liye teen options dekhe hai, link neeche daal rahi hu"),
    ("k02", "11-12", "19:05", "Arjun", "irctc pe sabki seats nikal li, pnr group mein daal diya"),
    ("k13", "11-14", "20:30", "Rohan", "kal subah tak sab apna hissa gpay se bhej dena, main collect kar lunga"),
    ("k03", "11-15", "22:40", "Sneha", "chalet reserve ho gaya, confirmation mail aa gayi hai"),
    ("k04", "11-16", "20:20", "Priya", "ek bande ka kharcha lagbhag nau hazaar aayega sab milake"),
    ("k05", "11-17", "18:50", "Arjun", "scorpio main chalaunga, baaki log aaram se baithna"),
    ("k06", "12-10", "22:15", "Ananya", "maine do sweater aur dastane rakh liye, wahan minus mein jaata hai"),
    ("k19", "12-12", "20:20", "Kabir", "passport ya aadhar, kuch bhi saath le lena, wahan check karte hai"),
    ("k07", "12-14", "21:40", "Neha", "thermals amazon se mangwa liye, kal tak aa jayenge"),
    ("k11", "12-17", "23:30", "Rohan", "kal subah paanch baje metro ke gate pe milte hai, late mat hona"),
    ("k10", "12-18", "06:30", "Arjun", "highway pe tel bharwa liya, ab sab nikalne ke liye taiyaar ho jao"),
    ("k20", "12-18", "09:30", "Sneha", "chalet ka caretaker chaabi lekar mil gaya, andar bohot achha hai"),
    ("k09", "12-19", "21:30", "Ananya", "kullu mein ek dhaba hai, wahan ka khana famous hai, table pakka kar deti hu"),
    # ---- Bangalore flat hunt ----
    ("k21", "01-06", "20:05", "Sneha", "indiranagar mein ek teen bhk dikha hai, ghar bohot achha hai"),
    (None, "01-08", "19:30", "Rohan", "kitna padega ek ka? total kiraya achha khasa hai"),
    ("k22", "01-08", "19:40", "Priya", "chaar log mein divide karo toh barah hazaar har ek ko padega"),
    ("k23", "01-10", "17:25", "Arjun", "dalal pandrah din ka kiraya maang raha hai, main bol dunga ek hafte pe maane"),
    (None, "01-12", "21:00", "Rohan", "owner ko pachaas hazaar advance dena hai, koi sambhal lega?"),
    ("k24", "01-12", "21:03", "Vikram", "haan main transfer kar deta hu, account details bhej do"),
    ("k25", "01-14", "20:10", "Priya", "pehle mahine ka hisaab ek sheet mein daal diya hai, sab check kar lo"),
    ("k26", "01-24", "18:10", "Neha", "airtel wale bhaiya kal subah aayenge lagane"),
    ("k27", "01-26", "11:15", "Arjun", "pehla mahina maine bijli ka bill bhar diya, ab agli baari kisi aur ki"),
    ("k28", "01-22", "19:00", "Kabir", "sunita didi kal se khana banana shuru karengi"),
    # ---- Hackathon startup MVP ----
    ("k29", "02-03", "22:30", "Vikram", "python mein fastapi chalega, halka hai aur tez bhi"),
    ("k30", "02-05", "22:10", "Vikram", "postgres le lete hai, aur pgvector se search ka kaam ho jayega"),
    ("k31", "02-10", "21:15", "Rohan", "namecheap se chatsearch dot ai le liya maine"),
    ("k32", "02-14", "20:45", "Kabir", "swiggy se biryani mangwa raha hu, address batao"),
    ("k33", "02-20", "23:00", "Vikram", "pgvector index bana diya, ab search chaar sau ms mein aa jata hai"),
    ("k34", "02-26", "22:40", "Priya", "pitch mein market size ka slide mujhse nahi ban raha, koi madad karega?"),
    ("k35", "03-01", "15:20", "Neha", "pitch ka pehla draft figma pe bana diya, dekh lo"),
    ("k36", "03-08", "17:00", "Rohan", "pandrah march ko jury ke saamne demo hai, subah das baje"),
    ("k37", "03-10", "16:45", "Vikram", "server deploy ho gaya, link sabko bhej diya"),
    ("k38", "03-12", "23:10", "Kabir", "demo ke baad party pakki, sab log pizza ke liye ready raho"),
    ("k39", "03-14", "22:00", "Rohan", "kal sab 9 baje tak venue pe pahunch jaana, laptop charge karke aana"),
    ("k40", "03-15", "14:30", "Neha", "jury ne humein pehla inaam de diya!! 🏆"),
]
PRE = ["sun ek baat", "ek minute guys", "dhyan do sab", "ek important baat thi", "arey suno"]
ACK = ["haan sahi hai", "done", "ok noted", "👍", "bilkul", "theek hai fir", "sahi bola", "mast"]

# (id, query, shape, [expected keys], note)
QUERIES = [
    ("Q01", "when did we finalize the holiday destination", "semantic", ["k01"]),
    ("Q02", "who booked the train tickets", "semantic", ["k02"]),
    ("Q03", "did we book the place to stay", "semantic", ["k03"]),
    ("Q04", "who is driving during the vacation", "semantic", ["k05"]),
    ("Q05", "is anyone bringing warm clothes", "semantic", ["k06"]),
    ("Q06", "how much is the rent per person", "semantic", ["k22"]),
    ("Q07", "who agreed to pay the security deposit", "semantic", ["k24"]),
    ("Q08", "what framework are we using for the backend", "semantic", ["k29"]),
    ("Q09", "when is the project presentation", "semantic", ["k36"]),
    ("Q10", "who is ordering food tonight", "semantic", ["k32"]),
    ("Q11", "where are we meeting before the journey", "semantic", ["k11"]),
    ("Q12", "when is the internet being installed", "semantic", ["k26"]),
    ("Q13", "who is the cook", "semantic", ["k28"]),
    ("Q14", "who bought the website address", "semantic", ["k31"]),
    ("Q15", "which house are we looking at", "semantic", ["k21"]),
    ("Q16", "has the app been deployed", "semantic", ["k37"]),
    ("Q17", "whose turn is it to pay the electricity bill", "semantic", ["k27"]),
    ("Q18", "do we need any id proof", "semantic", ["k19"]),
    ("Q19", "who needs help with the slides", "semantic", ["k34"]),
    ("Q20", "did we win the hackathon", "semantic", ["k40"]),
    ("Q21", "what did Priya say about the budget", "attributed", ["k04"]),
    ("Q22", "what did Arjun say about the broker commission", "attributed", ["k23"]),
    ("Q23", "what did Vikram suggest for the database", "attributed", ["k30"]),
    ("Q24", "what did Neha prepare for the pitch", "attributed", ["k35"]),
    ("Q25", "what did Sneha say about the accommodation options", "attributed", ["k15"]),
    ("Q26", "what did Ananya say about restaurants", "attributed", ["k09"]),
    ("Q27", "what did Kabir say about the celebration", "attributed", ["k38"]),
    ("Q28", "what did Rohan say about reaching the venue", "attributed", ["k39"]),
    ("Q29", "what did Vikram say about search speed", "attributed", ["k33"]),
    ("Q30", "what did Arjun say about fuel", "attributed", ["k10"]),
    ("Q31", "what did we discuss in December regarding warm jackets", "temporal", ["k06", "k07"]),
    ("Q32", "what did we decide in November about the trip", "temporal", ["k01", "k03"]),
    ("Q33", "who is collecting money on November 14", "temporal", ["k13"]),
    ("Q34", "what wifi installation was scheduled in late January", "temporal", ["k26"]),
    ("Q35", "what did the group say about rent in January", "temporal", ["k22", "k23"]),
    ("Q36", "what was said about the demo in March", "temporal", ["k36", "k38"]),
    ("Q37", "early February who talked about database", "temporal", ["k30"]),
    ("Q38", "what was ordered in mid December", "temporal", ["k07"]),
    ("Q39", "who met us at the chalet on December 18", "temporal", ["k20"]),
    ("Q40", "what did we decide in February about the tech stack", "temporal", ["k29"]),
]


def build():
    msgs = []
    key_to_msg = {}

    def add(dt, who, text, key=None):
        m = {"timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"), "sender": who, "text": text}
        msgs.append(m)
        if key:
            key_to_msg[key] = m

    for key, md, hm, who, text in SCRIPT:
        month, day = map(int, md.split("-"))
        hh, mm = map(int, hm.split(":"))
        dt = datetime(2025 if month >= 10 else 2026, month, day, hh, mm, rnd.randrange(60))
        if key:  # a short lead-in and acknowledgement make threads look natural
            others = [p for p in PEOPLE if p != who]
            add(dt - timedelta(seconds=rnd.randrange(40, 100)), rnd.choice(others), rnd.choice(PRE))
            add(dt, who, text, key)
            add(dt + timedelta(seconds=rnd.randrange(30, 120)), rnd.choice(others), rnd.choice(ACK))
        else:
            add(dt, who, text)

    target = 4400
    while len(msgs) < target:
        r = rnd.random()
        if r < 0.28:
            text = rnd.choice(REACT)
        elif r < 0.45:
            text = rnd.choice(DISTRACTORS)
        elif r < 0.52:
            text = rnd.choice(ENGLISHY)
        else:
            text = fill(rnd.choice(GENERAL))
        add(rand_ts(), sender(), text)

    msgs.sort(key=lambda m: m["timestamp"])
    for i, m in enumerate(msgs, 1):
        m["id"] = f"MSG_{i:05d}"
    msgs = [{"id": m["id"], "timestamp": m["timestamp"], "sender": m["sender"], "text": m["text"]}
            for m in msgs]
    return msgs, key_to_msg


def main():
    msgs, key_to_msg = build()
    queries = []
    for qid, query, shape, keys in QUERIES:
        expected = [key_to_msg[k]["id"] for k in keys]
        q_tokens = {t for t in tokenize(query) if t not in STOPWORDS}
        overlaps = [bool(q_tokens & set(tokenize(key_to_msg[k]["text"]))) for k in keys]
        queries.append({"id": qid, "query": query, "shape": shape,
                        "expected_ids": expected, "zero_overlap": not any(overlaps)})
    (ROOT / "chat_messages.json").write_text(json.dumps(msgs, ensure_ascii=False, indent=1), "utf-8")
    (ROOT / "test_queries.json").write_text(json.dumps(queries, ensure_ascii=False, indent=1), "utf-8")
    people = sorted({m["sender"] for m in msgs})
    zero = sum(q["zero_overlap"] for q in queries)
    print(f"{len(msgs)} messages | {len(people)} people | {msgs[0]['timestamp']} -> {msgs[-1]['timestamp']}")
    print(f"{len(queries)} queries | {zero} with zero keyword overlap")


if __name__ == "__main__":
    main()
