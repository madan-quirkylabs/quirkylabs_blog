import requests
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ----------- CONFIG -----------
SERVICE_ACCOUNT_FILE = "service-account.json"
SITEMAP_URL = "https://blog.quirkylabs.ai/sitemap.xml"
# ------------------------------

def get_urls_from_sitemap(sitemap_url):
    response = requests.get(sitemap_url)
    tree = ET.fromstring(response.content)
    urls = [elem.text for elem in tree.iter() if 'loc' in elem.tag]
    return urls

def index_url(url, service):
    try:
        response = service.urlNotifications().publish(
            body={"url": url, "type": "URL_UPDATED"}
        ).execute()
        print(f"✅ Indexed: {url}")
    except Exception as e:
        print(f"❌ Failed to index {url}: {e}")

def main():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/indexing"]
    )
    service = build("indexing", "v3", credentials=credentials)

    urls = get_urls_from_sitemap(SITEMAP_URL)
    print(f"Found {len(urls)} URLs in sitemap.")

    for url in urls:
        if any(x in url for x in ["/tags/", "/categories/", "/page/", "?"]):
            print(f"⏭️ Skipping non-content URL: {url}")
            continue
        index_url(url, service)


if __name__ == "__main__":
    main()
