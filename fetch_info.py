import requests
from bs4 import BeautifulSoup

def fetch_title_description(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Get title
        title = soup.title.string.strip() if soup.title else "No Title Found"

        # Get meta description
        description_tag = soup.find("meta", attrs={"name": "description"}) or \
                          soup.find("meta", attrs={"property": "og:description"})
        description = description_tag["content"].strip() if description_tag and description_tag.get("content") else "No Description Found"

        return title, description

    except Exception as e:
        return "Error fetching title", f"Error: {str(e)}"
