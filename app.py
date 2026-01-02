import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
import webbrowser
from threading import Timer
import re

app = Flask(__name__)

def scrape_booth(url):
    """
    Scrapes the provided Booth URL for item details.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

    soup = BeautifulSoup(response.content, "html.parser")
    
    items = []
    # Try different common selectors if the main one fails, but stick to the one we found first
    item_containers = soup.select(".item-card")
    
    # Fallback for different page layouts (sometimes lists look different)
    if not item_containers:
        item_containers = soup.select("li.item")

    for container in item_containers:
        try:
            # Title
            title_elem = container.select_one(".item-card__title")
            if not title_elem: continue # Skip if structure is totally different
            title = title_elem.get_text(strip=True)

            # Price
            price_elem = container.select_one(".price") # Generic price selector often works better
            if not price_elem:
                price_elem = container.select_one(".item-card__price")
            price = price_elem.get_text(strip=True) if price_elem else "Free/Unknown"

            # Link
            link_elem = container.select_one("a.item-card__link")
            # Sometimes the container itself is NOT the link, but contains it, or IS the link
            if not link_elem and container.name == 'a':
                link_elem = container
            elif not link_elem:
                link_elem = container.find("a")
            
            link = link_elem['href'] if link_elem else "#"
            if not link.startswith("http"):
                link = "https://booth.pm" + link

            # Extract ID for sorting
            item_id = 0
            id_match = re.search(r'/items/(\d+)', link)
            if id_match:
                item_id = int(id_match.group(1))

            # Image
            # Handle lazy loading: often src is a placeholder, real image is in data-src or data-original
            img_elem = container.select_one(".item-card__thumbnail-image")
            if not img_elem:
                img_elem = container.select_one("img")
            
            img_url = ""
            if img_elem:
                img_url = img_elem.get("data-src") or img_elem.get("data-original") or img_elem.get("src")

            # Shop Name
            shop_elem = container.select_one(".item-card__shop-name")
            shop_name = shop_elem.get_text(strip=True) if shop_elem else "Unknown Shop"

            # Category/Genre (Optional, good for filtering colors)
            category_elem = container.select_one(".item-card__category")
            category = category_elem.get_text(strip=True) if category_elem else ""

            items.append({
                "id": item_id,
                "title": title,
                "price": price,
                "link": link,
                "image": img_url,
                "shop": shop_name,
                "category": category
            })

        except Exception as e:
            print(f"Error parsing item: {e}")
            continue

    return {"products": items, "count": len(items)}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        urls_text = request.form.get("urls")
        if not urls_text:
            return render_template("index.html", error="URLを入力してください")
        
        # Split by lines and remove empty lines
        urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
        
        all_products = []
        total_count = 0
        errors = []

        for url in urls:
            data = scrape_booth(url)
            if "error" in data:
                errors.append(f"{url}: {data['error']}")
                continue
            
            # Add source URL to each product and extend the main list
            products = data.get("products", [])
            for p in products:
                p["source_url"] = url
            
            all_products.extend(products)
            total_count += len(products)
        
        # Sort all products by ID descending (newest first)
        all_products.sort(key=lambda x: x['id'], reverse=True)
        
        return render_template("result.html", products=all_products, count=total_count, errors=errors)
    
    return render_template("index.html")

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    # Timer to open browser automatically
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)
