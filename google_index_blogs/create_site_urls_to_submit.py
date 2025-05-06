import requests
from bs4 import BeautifulSoup
import csv

def extract_sitemap_urls(sitemap_url):
    response = requests.get(sitemap_url)
    soup = BeautifulSoup(response.content, 'xml')
    urls = [loc.text for loc in soup.find_all('loc')]
    return urls

# Example usage
sitemap_url = 'https://blog.quirkylabs.ai/sitemap.xml'
urls = extract_sitemap_urls(sitemap_url)

# Write URLs to a CSV file
with open('sitemap_urls.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['URL'])
    for url in urls:
        writer.writerow([url])
