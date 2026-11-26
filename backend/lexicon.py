"""Bilingual (English <-> Hinglish) concept lexicon and text helpers.

Each concept groups English words and the everyday Hinglish words people
actually type for the same idea.  A term ending in "*" is a prefix match
(handles Hinglish verb endings: bhej -> bhejna, bhejo, bheja ...).
A term containing a space is a phrase.
"""
import re

TOKEN_RE = re.compile(r"[a-z0-9\u0900-\u097f]+")


def stem(tok: str) -> str:
    """Very light stemmer + repeated-letter collapse (haan/han, booked/book)."""
    t = tok.lower()
    if len(t) > 4:
        if t.endswith("ing"):
            t = t[:-3]
        elif t.endswith("ed"):
            t = t[:-2]
        elif t.endswith(("ses", "xes", "zes", "ches", "shes")):
            t = t[:-2]
        elif t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
    return re.sub(r"(.)\1+", r"\1", t)


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in TOKEN_RE.findall(text.lower())]


CONCEPTS: dict[str, list[str]] = {
    "decide": ["decide", "decision", "finalize", "finalise", "final", "fix", "lock", "pakka",
               "pakki", "pakke", "tay", "settle", "vote", "voting", "ho gaya"],
    "agree": ["agree", "haan", "hanji", "yes", "sure", "volunteer", "manzoor", "chalega"],
    "trip": ["trip", "travel", "vacation", "holiday", "tour", "yatra", "ghoomne", "ghumne",
             "ghoomna", "outing", "getaway", "journey", "safar", "pahadi", "pahad*", "manali",
             "goa", "kullu", "snow", "road trip", "chalte", "tourist"],
    "pay": ["pay*", "paid", "transfer*", "bhej*", "send", "sent", "gpay", "phonepe", "paytm",
            "upi", "collect*"],
    "deposit": ["deposit", "advance", "security", "owner", "landlord", "account details",
                "account"],
    "budget": ["budget", "cost", "price", "expense", "kharcha", "kharch*", "paisa", "paise",
               "hisaab", "hisab", "rupee", "rupaye", "rupaya", "mehnga", "sasta", "amount",
               "lagbhag", "total", "money", "fund"],
    "rent": ["rent", "kiraya", "divide", "split", "per person", "har ek", "per head"],
    "flat": ["flat", "apartment", "bhk", "house", "ghar", "society"],
    "drive": ["drive", "driving", "driver", "car", "suv", "scorpio", "gaadi", "gadi", "chala*",
              "chalana", "steering", "highway", "road"],
    "fuel": ["petrol", "diesel", "fuel", "tel", "cng"],
    "stay": ["accommodation", "stay", "hotel", "airbnb", "cottage", "chalet", "homestay",
             "room", "resort", "lodge"],
    "book": ["book", "booking", "reserve", "reservation", "confirmation", "ticket", "seat",
             "pnr", "irctc"],
    "train": ["train", "irctc", "vande bharat", "railway", "platform"],
    "presentation": ["presentation", "present", "pitch", "deck", "slide", "jury", "demo", "ppt",
                     "figma", "showcase"],
    "food": ["food", "swiggy", "zomato", "biryani", "pizza", "khana", "dinner", "lunch", "eat",
             "eating", "maggi", "momos", "snack", "chips", "burger"],
    "eatery": ["restaurant", "dhaba", "cafe", "eatery", "diner", "table"],
    "order": ["order", "mangwa*", "mangva*", "mangaya", "mangao"],
    "meet": ["meet", "meeting", "milte", "milna", "milenge", "gather", "gate", "station",
             "metro", "pickup", "venue"],
    "warm": ["warm", "cold", "thand", "thandi", "jacket", "muffler", "sweater", "thermal",
             "woolen", "dastane", "gloves", "minus", "winter", "hoodie"],
    "pack": ["pack", "packing", "bring", "carry", "rakh liye", "rakh liya", "le ja*",
             "saath le"],
    "framework": ["framework", "stack", "backend", "server", "fastapi", "django", "flask",
                  "express", "nextjs", "python", "node", "library", "api", "tech"],
    "database": ["database", "db", "postgres", "postgresql", "pgvector", "sql", "mysql",
                 "mongo", "mongodb", "vector"],
    "domain": ["domain", "namecheap", "godaddy", "website", "url", "dot ai", "web address"],
    "buy": ["buy", "bought", "purchase", "kharid*", "le liya"],
    "broker": ["broker", "commission", "brokerage", "dalal", "negotiate", "negotiation"],
    "wifi": ["wifi", "broadband", "internet", "airtel", "fiber", "fibre", "router",
             "installation", "install", "lagane", "lagana"],
    "cook": ["cook", "cooking", "maid", "bai", "didi", "khana banana", "khana banane",
             "kitchen", "rasoi"],
    "win": ["win", "won", "prize", "inaam", "jeet*", "winner"],
    "deploy": ["deploy", "live", "launch", "hosted", "hosting"],
    "bill": ["bill", "bijli", "electricity"],
    "idproof": ["id", "aadhar", "aadhaar", "passport", "identity", "proof"],
    "help": ["help", "madad", "support", "sahayata"],
    "speed": ["speed", "fast", "tez", "jaldi", "latency", "ms", "slow"],
    "party": ["party", "celebration", "celebrate", "treat"],
    "arrive": ["arrive", "reach", "pahunch*"],
    "prepare": ["prepare", "draft", "bana", "banaya", "ready", "tayyar", "taiyaar"],
}

_STOP_RAW = """
a an the is are was were be been am do does did done have has had will would can could should
shall may might of in on at for to from by with about as into during before after over under
and or but if then so than too very just also who whom whose what which when where why how
much many we us our you your they them their i me my he she it its this that these those
there here any anyone someone something anything everyone said say says suggest suggested
tell told regarding talk talked talking discuss discussed discussion group chat message
messages tonight today going using use used plan planned scheduled schedule happened mention
mentioned person place looking look address
hai hain hu hun ho ka ki ke ko se me mein pe par aur ya toh to bhi nahi na kya kab kaun kaise
kitna kitni main mai mera meri hum tum tu tera apna sab kuch bas ab abhi phir fir yeh ye woh
wo jo jab tab ek
"""
STOPWORDS: set[str] = {stem(w) for w in _STOP_RAW.split()}

NUMBER_WORDS: set[str] = {stem(w) for w in
                          "hazaar hazar lakh sau ek do teen char paanch chhe saat aath nau das "
                          "gyarah barah terah chaudah pandrah solah bees tees chalis pachaas "
                          "saath sattar assi nabbe thousand hundred".split()}

DATE_WORDS: set[str] = {stem(w) for w in
                        "kal aaj parso subah shaam raat baje tareekh hafte hafta mahine "
                        "january february march october november december monday tuesday "
                        "wednesday thursday friday saturday sunday".split()}

MONTHS: dict[str, int] = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4,
    "apr": 4, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11,
    "nov": 11, "december": 12, "dec": 12,
}
