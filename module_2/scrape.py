from bs4 import BeautifulSoup
from urllib.request import urlopen

# pulls data from grad cafe
def scrape_data():
    url = "https://www.thegradcafe.com/survey/"
    page = urlopen(url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup
 
soup = scrape_data()
print(soup.title)