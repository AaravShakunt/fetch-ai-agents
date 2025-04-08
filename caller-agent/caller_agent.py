from uagents import Agent, Context, Model
from typing import List, Optional, Dict, Any

agent = Agent(name="company_requestor", port=8003)

# Replace with the website you want to get information about
WEBSITE_URL = "apple.com"

COMPANY_INFO_PROCESSOR_ADDRESS = "agent1qtz02l3radupfymrepmcmvjfpwd9c6zrql5u8hfykvqvaxm2wumm7rx0txw"
TICKER_ADDRESS="agent1qd7wrm64tupqvtkpwu3ds5awmk30fmwnedr4fm36ty5na97aawjrc0p9mx9"
REVENUE_ADDRESS="agent1qwg43f9euf5vdtz5kxkz6mdch32sjgdqjdlx0n4un5lzpmj64ws85gfydhn"

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
    # Core fields likely to be found on homepage
    company_name: str
    domain: str
    main_offerings: str
    tagline: str
    summary: str
    source_url: str
    
    # Optional fields that might be extracted if available
    contact_info: str = "Not found"
    social_media: str = "Not found"

class CompanyRequest(Model):
    company_name: str

class TickerResponse(Model):
    company_name: str
    ticker: str
    success: bool
    message: str
class overviewRequest(Model):
    ticker :str

class CompanyAnalysis(Model):
    company_overview_summary: str
    valuation_summary: str
    profitability_summary: str
    growth_summary: str
    financial_health_summary: str
    stock_performance_summary: str
    analyst_sentiment_summary: str

class RequestsModel(Model):
    company_website: str

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
    ctx.logger.info(f"Domain: {data.domain}")
    ctx.logger.info(f"Main Offerings: {data.main_offerings}")
    ctx.logger.info(f"Tagline: {data.tagline}")
    ctx.logger.info(f"Summary: {data.summary}")
    ctx.logger.info(f"Contact Info: {data.contact_info}")
    ctx.logger.info(f"Social Media: {data.social_media}")
    ctx.logger.info(f"Source URL: {data.source_url}")
    
    # Clean up company name for news request
    company_name = data.company_name.strip()
    # Remove any quotes and other JSON syntax that might be in the string
    for char in ['"', "'", '{', '}', '[', ']']:
        company_name = company_name.replace(char, '')
    
    # If company name contains common suffixes, remove them for better news search
    for suffix in [" Inc", " LLC", " Ltd", " Corporation", " Corp", " Co", " Group"]:
        if company_name.endswith(suffix):
            company_name = company_name[:-len(suffix)]
    
    ctx.logger.info(f"Requesting news about '{company_name}' from news agent")
    
    news_request = NewsRequest(
        company_name=company_name,
        max_articles=MAX_NEWS_ARTICLES
    )
    ticker_request = CompanyRequest(
        company_name = company_name
    )
    await ctx.send(TICKER_ADDRESS,ticker_request)
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
        
        for i, article in enumerate(news.articles[:3], 1):  # Show first 3 articles
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
    
    # A comprehensive report could be generated here combining company info and news
    if company_data and news_data:
        ctx.logger.info("Both company data and news data are available")
        ctx.logger.info("A full business intelligence report could be generated")

@agent.on_message(model=TickerResponse)
async def handle_ticker_response(ctx: Context, sender: str, ticker: TickerResponse):
    global ticker_value
    ticker_value = ticker
    ctx.logger.info(f"Received Ticker of company {ticker.ticker}")
    overview_request=overviewRequest(
        ticker = ticker_value.ticker
    )
    await ctx.send(REVENUE_ADDRESS,overview_request)

@agent.on_message(model=CompanyAnalysis)
async def handle_company_analysis(ctx: Context, sender: str, analysis: CompanyAnalysis):
    global companyanalysis
    companyanalysis = analysis
    ctx.logger.info(f"Company Overview: {analysis.company_overview_summary}")
    ctx.logger.info(f"Valuation: {analysis.valuation_summary}")
    ctx.logger.info(f"Profitability: {analysis.profitability_summary}")
    ctx.logger.info(f"Growth: {analysis.growth_summary}")
    ctx.logger.info(f"Financial Health: {analysis.financial_health_summary}")
    ctx.logger.info(f"Stock Performance: {analysis.stock_performance_summary}")
    ctx.logger.info(f"Analyst Sentiment: {analysis.analyst_sentiment_summary}")



@agent.on_message(model=Error)
async def handle_error(ctx: Context, sender: str, error: Error):
    """Log error from company info processor agent"""
    ctx.logger.error(f"Got error from agent: {error.text}")


if __name__ == "__main__":
    agent.run()