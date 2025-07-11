import os, sqlite3, requests
from bs4 import BeautifulSoup
from telegram import Bot
from apify_client import ApifyClient

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
MAX_PRICE = int(os.getenv("MAX_PRICE", 15000))
KEYWORDS = os.getenv("KEYWORDS", "småfel,rost").split(",")

DB = "/tmp/seen.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
    conn.close()

def get_seen_ids():
    conn = sqlite3.connect(DB)
    ids = {row[0] for row in conn.execute("SELECT id FROM seen")}
    conn.close()
    return ids

def mark_seen(ids):
    conn = sqlite3.connect(DB)
    for _id in ids:
        conn.execute("INSERT OR IGNORE INTO seen (id) VALUES (?)", (_id,))
    conn.commit()
    conn.close()

def fetch_blocket():
    url = f"https://www.blocket.se/annonser/hela_sverige/bilar?cg=1020&w=3&pe={MAX_PRICE}"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    ads=[]
    for ad in soup.select("article"):
        title_elem = ad.select_one("h2")
        if not title_elem: continue
        title = title_elem.get_text(strip=True)
        href = ad.find("a", href=True)
        if not href: continue
        adid = href["href"].split("/")[-1]
        price_elem = ad.select_one("div.price")
        price = 0
        if price_elem:
            price = int(''.join(filter(str.isdigit, price_elem.get_text())))
        if price <= MAX_PRICE and any(k.lower() in title.lower() for k in KEYWORDS):
            ads.append({"source":"Blocket","id":adid,"title":title,"url":"https://www.blocket.se"+href["href"],"price":price})
    return ads

def fetch_facebook():
    client = ApifyClient(APIFY_TOKEN)
    run = client.actor("apify/facebook-marketplace-scraper").call({
        "startUrls": [{"url": "https://www.facebook.com/marketplace/stockholm/search/?query=bil"}],
        "resultsLimit": 20
    })
    dataset = client.dataset(run["defaultDatasetId"]).list_items()["items"]
    ads = []
    for item in dataset:
        title = item.get("title", "")
        price_str = item.get("price", "0").replace(" SEK", "").replace(",", "")
        try:
            price = int(price_str)
        except:
            price = 0
        if price <= MAX_PRICE and any(k.lower() in title.lower() for k in KEYWORDS):
            ads.append({"source":"Facebook","id":item["id"],"title":title,"url":item["url"],"price":price})
    return ads

def send_notice(ad):
    text = f"[{ad['source']}] {ad['title']} – {ad['price']} kr\n{ad['url']}"
    Bot(BOT_TOKEN).send_message(chat_id=CHAT_ID, text=text, disable_web_page_preview=True)

def main(request=None):
    init_db()
    seen = get_seen_ids()
    all_ads = fetch_blocket() + fetch_facebook()
    new_ads = [ad for ad in all_ads if ad["id"] not in seen]
    for ad in new_ads:
        send_notice(ad)
    mark_seen([a["id"] for a in new_ads])
    return f"Skickade {len(new_ads)} nya annonser!"
