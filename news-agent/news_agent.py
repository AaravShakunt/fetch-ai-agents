import os
import json
import requests
from typing import List, Dict, Any, Optional
from uagents import Agent, Context, Model
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download NLTK data if not already present
nltk.download('vader_lexicon', quiet=True)

agent = Agent(name="news_agent", port=8007, endpoint=["http://localhost:8007/submit"])

# NewsAPI configuration
# Get a free API key from https://newsapi.org/
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "news_api_key_here")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Hugging Face API configuration
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "hf_api_key_here")
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"
HEADERS = {
    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
    "Content-Type": "application/json"
}

# Model definitions
class NewsRequest(Model):
    """Model for news request"""
    company_name: str  # Name of the company to get news for
    max_articles: Optional[int] = 20  # Maximum number of articles to return

class Article(Model):
    """Model for a news article"""
    title: Optional[str] = "No title"
    description: Optional[str] = "No description"
    source: Optional[str] = "Unknown source"
    url: Optional[str] = ""
    published_at: Optional[str] = ""
    content: Optional[str] = None
    sentiment: Optional[Dict[str, float]] = None  # Added sentiment field

class NewsSummary(Model):
    """Model for news summary"""
    overall_sentiment: str
    summary: str

class NewsResponse(Model):
    """Model for news response"""
    company_name: str
    articles: List[Article]
    total_results: int
    summary: Optional[NewsSummary] = None  # Added summary field

class Error(Model):
    """Model for error response"""
    text: str

def analyze_sentiment(text: str) -> Dict[str, float]:
    """Analyze sentiment of the given text using NLTK's VADER"""
    if not text:
        return {"neg": 0.0, "neu": 0.0, "pos": 0.0, "compound": 0.0}
    
    sia = SentimentIntensityAnalyzer()
    sentiment_scores = sia.polarity_scores(text)
    
    return sentiment_scores  # Returns {'neg': x, 'neu': y, 'pos': z, 'compound': c}

def get_overall_sentiment(articles: List[Article]) -> str:
    """Calculate the overall sentiment based on all articles"""
    if not articles:
        return "Neutral"
    
    # Calculate average compound sentiment score
    total_compound = 0
    for article in articles:
        if article.sentiment and "compound" in article.sentiment:
            total_compound += article.sentiment["compound"]
    
    avg_compound = total_compound / len(articles)
    
    # Interpret the average sentiment
    if avg_compound >= 0.05:
        return "Positive"
    elif avg_compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"

def generate_news_summary(company_name: str, articles: List[Article]) -> Optional[NewsSummary]:
    """Generate a summary of news articles using Hugging Face model"""
    try:
        # Prepare the content for the model (same as before)
        article_texts = []
        for i, article in enumerate(articles[:10]):  # Limit to 10 articles to avoid token limit
            sentiment_label = "positive" if article.sentiment and article.sentiment.get("compound", 0) > 0 else \
                             "negative" if article.sentiment and article.sentiment.get("compound", 0) < 0 else "neutral"
            
            article_text = f"Article {i+1}:\nTitle: {article.title}\nDescription: {article.description}\n" \
                          f"Source: {article.source}\nSentiment: {sentiment_label}\n\n"
            article_texts.append(article_text)
        
        all_articles_text = "".join(article_texts)
        
        # Create a prompt for the model
        prompt = f"""You are an AI assistant analyzing recent news about {company_name}. Below are several recent news articles about this company:{all_articles_text}Based on these articles, please provide:1. A comprehensive summary of the recent news about {company_name} (2-3 paragraphs)2. An analysis of the general sentiment and public perception around the companyPlease be objective and focus on factual information from the articles."""

        # Prepare the payload for the Hugging Face API
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.1,
                "return_full_text": False
            }
        }

        # Add debugging to see what we're sending
        print(f"Sending request to Hugging Face API with prompt length: {len(prompt)}")
        
        # Make request to Hugging Face Inference API
        response = requests.post(HUGGINGFACE_API_URL, headers=HEADERS, json=payload)
        
        # Debug the response
        print(f"Hugging Face API response status code: {response.status_code}")
        print(f"Response content: {response.text[:500]}...")  # Print first 500 chars
        
        response.raise_for_status()
        
        # Extract the generated text from the response - improved parsing
        result = response.json()
        summary_text = ""
        
        # Different models might return data in different formats
        if isinstance(result, list) and len(result) > 0:
            summary_text = result[0].get('generated_text', '')
        elif isinstance(result, dict):
            summary_text = result.get('generated_text', '')
        
        # If we still don't have a summary, try other possible response formats
        if not summary_text and isinstance(result, list) and len(result) > 0:
            if 'text' in result[0]:
                summary_text = result[0]['text']
        
        print(f"Extracted summary text: {summary_text[:100]}...")  # Print first 100 chars
        
        # Fallback if no summary is generated
        if not summary_text:
            print("No summary from API, generating fallback summary")
            # Create a simple fallback summary
            summary_text = f"Recent news about {company_name} includes "
            # Add titles of a few articles
            for i, article in enumerate(articles[:3]):
                if i > 0:
                    summary_text += ", " if i < len(articles[:3])-1 else " and "
                summary_text += f"'{article.title}'"
            summary_text += "."
        
        # Calculate overall sentiment
        overall_sentiment = get_overall_sentiment(articles)
        
        return NewsSummary(
            overall_sentiment=overall_sentiment,
            summary=summary_text
        )
    
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        # Create a fallback summary on exception
        fallback_summary = f"Recent news about {company_name} includes multiple articles with an overall {get_overall_sentiment(articles).lower()} sentiment."
        return NewsSummary(
            overall_sentiment=get_overall_sentiment(articles),
            summary=fallback_summary
        )
def fetch_news(company_name: str, max_articles: int = 20) -> Dict[str, Any]:
    """Fetch news about a company from NewsAPI"""
    try:
        # Prepare the API request
        params = {
            "q": company_name,  # Search query
            "apiKey": NEWS_API_KEY,
            "language": "en",
            "pageSize": max_articles  # Limit the number of articles returned
        }
        
        # Make the API request
        response = requests.get(NEWS_API_URL, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        if data.get("status") != "ok":
            return Error(text=f"NewsAPI error: {data.get('message', 'Unknown error')}")
        
        # Add debug logging to see what we're getting from the API
        articles_data = data.get("articles", [])
        print(f"API returned {len(articles_data)} articles")
        if len(articles_data) > 0:
            print(f"First article: {articles_data[0]}")
        
        # Process all the articles returned (up to max_articles)
        articles = []
        # Make sure we're processing all returned articles
        for article_data in articles_data:
            # Analyze sentiment from title and description
            title = article_data.get("title", "")
            description = article_data.get("description", "")
            text_for_sentiment = f"{title} {description}"
            sentiment = analyze_sentiment(text_for_sentiment)
            
            article = Article(
                title=title or "No title",
                description=description or "No description",
                source=article_data.get("source", {}).get("name", "Unknown source"),
                url=article_data.get("url", ""),
                published_at=article_data.get("publishedAt", ""),
                content=article_data.get("content", ""),
                sentiment=sentiment  # Add sentiment analysis
            )
            articles.append(article)
        
        # Generate a summary using Hugging Face
        summary = None
        if articles:
            summary = generate_news_summary(company_name, articles)
        
        # Create the response
        return NewsResponse(
            company_name=company_name,
            articles=articles,
            total_results=data.get("totalResults", 0),
            summary=summary
        )
    
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return Error(text=f"Failed to fetch news: {str(e)}")


@agent.on_event("startup")
async def startup(ctx: Context):
    """Log when the agent starts up"""
    ctx.logger.info(f"News agent started with address: {agent.address}")
    if NEWS_API_KEY == "your_news_api_key_here":
        ctx.logger.warning("NewsAPI key not configured. Please set the NEWS_API_KEY environment variable.")
    if HUGGINGFACE_API_KEY == "hf_api_key_here":
        ctx.logger.warning("Hugging Face API key not configured. Please set the HUGGINGFACE_API_KEY environment variable.")
    
    # # Test fetch news and log the result
    # test_result = fetch_news("Apple", 5)  # Reduced to 5 for faster testing
    # if isinstance(test_result, NewsResponse):
    #     ctx.logger.info(f"Test fetch news found {len(test_result.articles)} articles")
    #     for i, article in enumerate(test_result.articles):
    #         ctx.logger.info(f"Article {i+1}: {article.title}")
    #     if test_result.summary:
    #         ctx.logger.info(f"Summary generated with sentiment: {test_result.summary.summary}")
    # else:
    #     ctx.logger.error(f"Test fetch failed: {test_result.text}")

@agent.on_message(model=NewsRequest)
async def handle_news_request(ctx: Context, sender: str, request: NewsRequest):
    """Handle news request and return news articles"""
    ctx.logger.info(f"Received request to fetch news about: {request.company_name}")
    
    # Fetch news about the company
    response = fetch_news(request.company_name, request.max_articles)

    # Add more detailed logging to debug
    if isinstance(response, NewsResponse):
        ctx.logger.info(f"Found {response.total_results} articles about {request.company_name}")
        ctx.logger.info(f"Returning {len(response.articles)} articles to {sender}")
        
        # Print details of the first few articles for debugging
        for i, article in enumerate(response.articles):
            ctx.logger.info(f"Article {i+1}: {article.title} - Sentiment: {article.sentiment}")
        
        # Log summary information if available
        if response.summary:
            ctx.logger.info(f"Overall sentiment: {response.summary.overall_sentiment}")
            ctx.logger.info(f"Summary content: {response.summary.summary[:100]}...") # Print first 100 chars
            ctx.logger.info(f"Summary generated successfully")
    else:
        ctx.logger.error(f"Error response: {response.text}")
    
    # Send the response
    await ctx.send(sender, response)

if __name__ == "__main__":
    agent.run()