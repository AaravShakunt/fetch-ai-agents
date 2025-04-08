from uagents import Agent, Context, Model
from typing import List, Optional, Dict, Any

agent = Agent(name="company_requestor", port=8003)

# Replace with the website you want to get information about
WEBSITE_URL = "apple.com"

COMPANY_INFO_PROCESSOR_ADDRESS = "agent1qtz02l3radupfymrepmcmvjfpwd9c6zrql5u8hfykvqvaxm2wumm7rx0txw"

# News agent configuration
NEWS_AGENT_ADDRESS = "agent1qdsxvhmlg9mqlnqvujvs7cxf3x5yhglsqylgdgqfc0r0tfpx8yre6ghhh8s"
MAX_NEWS_ARTICLES = 20

# State variables
company_data = None
news_data = None

# Models for news agent
class NewsRequest(Model):
    """Model for news request"""
    company_name: str
    max_articles: Optional[int] = 20

class NewsSummary(Model):
    """Model for news summary"""
    overall_sentiment: str
    summary: str

class Article(Model):
    """Model for a news article"""
    title: Optional[str] = "No title"
    description: Optional[str] = "No description"
    source: Optional[str] = "Unknown source"
    url: Optional[str] = ""
    published_at: Optional[str] = ""
    content: Optional[str] = None
    sentiment: Optional[Dict[str, float]] = None  # Added sentiment field


class NewsResponse(Model):
    """Model for news response"""
    company_name: str
    articles: List[Article]
    total_results: int
    summary: Optional[NewsSummary] = None  # Added summary field


class Request(Model):
    website: str


class Error(Model):
    text: str


class CompanyData(Model):
    company_name: str
    industry: str
    products_services: str
    company_size: str
    headquarters: str
    year_founded: str
    leadership: str
    description: str
    source_url: str


@agent.on_event("startup")
async def request_company_info(ctx: Context):
    """Send website URL to company info processor agent"""
    ctx.logger.info(f"Requesting company information for website: {WEBSITE_URL}")
    await ctx.send(COMPANY_INFO_PROCESSOR_ADDRESS, Request(website=WEBSITE_URL))


@agent.on_message(model=CompanyData)
async def handle_company_data(ctx: Context, sender: str, data: CompanyData):
    global company_data
    company_data = data
    
    """Log response from company info processor agent"""
    ctx.logger.info(f"Received company information from processor agent:")
    ctx.logger.info(f"Company Name: {data.company_name}")
    ctx.logger.info(f"Industry: {data.industry}")
    ctx.logger.info(f"Products/Services: {data.products_services}")
    ctx.logger.info(f"Company Size: {data.company_size}")
    ctx.logger.info(f"Headquarters: {data.headquarters}")
    ctx.logger.info(f"Year Founded: {data.year_founded}")
    ctx.logger.info(f"Leadership: {data.leadership}")
    ctx.logger.info(f"Description: {data.description}")
    ctx.logger.info(f"Source URL: {data.source_url}")
    
    # Extract just the company name without any JSON syntax
    # Remove any quotes and other JSON characters that might be in the string
    company_name = data.company_name.strip()
    if company_name.startswith('"'):
        company_name = company_name.strip('"')
    if ',' in company_name:
        company_name = company_name.split(',')[0]
    
    # Clean up any remaining JSON syntax artifacts
    for char in ['"', "'", '{', '}', '[', ']']:
        company_name = company_name.replace(char, '')
    
    ctx.logger.info(f"Requesting news about '{company_name}' from news agent")
    
    news_request = NewsRequest(
        company_name=company_name,
        max_articles=MAX_NEWS_ARTICLES
    )
    
    await ctx.send(NEWS_AGENT_ADDRESS, news_request)


@agent.on_message(model=NewsResponse)
async def handle_news_response(ctx: Context, sender: str, news: NewsResponse):
    """Handle news response and display the information"""
    global news_data
    news_data = news
    
    ctx.logger.info(f"Received news about {news.company_name}")
    ctx.logger.info(f"Found {news.total_results} articles, showing {len(news.articles)}")
    
    if news.articles:
        if news.summary:
            ctx.logger.info(f"Overall sentiment: {news.summary.overall_sentiment}")
            ctx.logger.info(f"Summary content: {news.summary.summary[:100]}...") # Print first 100 chars
            ctx.logger.info(f"Summary generated successfully")
        
        for i, article in enumerate(news.articles[:1], 1):  # Only get the first article
            ctx.logger.info(f"Article {i}: {article.title}")
            ctx.logger.info(f"Description: {article.description}")
            ctx.logger.info(f"Source: {article.source}")
            ctx.logger.info(f"URL: {article.url}")
            ctx.logger.info(f"Published: {article.published_at}")
            if article.sentiment:
                ctx.logger.info(f"Sentiment: {article.sentiment}")
            ctx.logger.info("---")
    else:
        ctx.logger.info("No articles found in news response.")


@agent.on_message(model=Error)
async def handle_error(ctx: Context, sender: str, error: Error):
    """Log error from company info processor agent"""
    ctx.logger.error(f"Got error from agent: {error.text}")


if __name__ == "__main__":
    agent.run()