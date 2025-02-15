import yfinance as yf
import json

def get_stock_news(ticker):
    # Create a Ticker object for the given stock ticker
    stock = yf.Ticker(ticker)

    # Fetch the news articles for the stock
    news = stock.news

    # Prepare the list to store the formatted news articles
    news_data = []

    if news:
        for article in news:
            # Check if article contains the necessary data
            content = article.get('content', {})
            if content:
                news_article = {
                    'title': content.get('title', 'No title available'),
                    'summary': content.get('summary', 'No summary available'),
                    'pubDate': content.get('pubDate', 'No publish date available'),
                    'provider': content.get('provider', {}).get('displayName', 'No provider available'),
                    'thumbnailUrl': content.get('thumbnail', {}).get('originalUrl', 'No thumbnail available'),
                    'url': content.get('canonicalUrl', {}).get('url', 'No URL available')
                }
                # Append the formatted article to the news_data list
                news_data.append(news_article)
    else:
        return json.dumps({"message": f"No news found for {ticker}."})

    # Return the news data as a JSON string
    return json.dumps(news_data, indent=4)

if __name__ == "__main__":
    ticker = input("Enter stock ticker: ").upper()
    # Print the returned JSON data
    print(get_stock_news(ticker))
