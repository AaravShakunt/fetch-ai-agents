"""
This agent writes a greeting in the logs on startup.
"""

from uagents import Agent, Context, Model
import requests
import re

# Create the agent
agent = Agent(
    name="ticker_agent",
    port=8008,
    endpoint="http://localhost:8008/submit"
)

# Define message schemas
class CompanyRequest(Model):
    company_name: str

class TickerResponse(Model):
    company_name: str
    ticker: str
    success: bool
    message: str

@agent.on_event("startup")
async def startup(ctx: Context):
    """Logs hello message on startup"""
    ctx.logger.info(f"Ticker Agent started. Address: {ctx.address}")

@agent.on_message(model=CompanyRequest)
async def handle_company_request(ctx: Context, sender: str, request: CompanyRequest):
    """Handles incoming requests for company ticker symbols"""
    company_name = request.company_name
    ctx.logger.info(f"Received request for company: {company_name}")

    try:
        # Search for the ticker symbol using Yahoo Finance search API
        ticker_info = get_ticker_symbol(company_name)

        if ticker_info["success"]:
            ctx.logger.info(f"Found ticker for {company_name}: {ticker_info['ticker']}")
        else:
            ctx.logger.info(f"Could not find ticker for {company_name}: {ticker_info['message']}")

        # Send the response
        await ctx.send(
            sender,
            TickerResponse(
                company_name=company_name,
                ticker=ticker_info["ticker"],
                success=ticker_info["success"],
                message=ticker_info["message"]
            )
        )
    except Exception as e:
        ctx.logger.error(f"Error processing request: {str(e)}")
        await ctx.send(
            sender,
            TickerResponse(
                company_name=company_name,
                ticker="",
                success=False,
                message=f"Error processing request: {str(e)}"
            )
        )

def get_ticker_symbol(company_name):
    """
    Searches Yahoo Finance for a ticker symbol based on company name using their search API.
    """
    try:
        query = clean_company_name(company_name)
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=1&newsCount=0"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            quotes = data.get("quotes", [])
            if quotes:
                ticker = quotes[0].get("symbol", "")
                return {
                    "success": True,
                    "ticker": ticker,
                    "message": "Ticker found successfully"
                }
            else:
                return {
                    "success": False,
                    "ticker": "",
                    "message": "No matching ticker found"
                }
        else:
            return {
                "success": False,
                "ticker": "",
                "message": f"Yahoo Finance API error: {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "ticker": "",
            "message": f"Exception during ticker lookup: {str(e)}"
        }

def clean_company_name(name):
    """
    Clean and format company name to improve ticker lookup accuracy
    """
    # Remove common suffixes like Inc., Corp., etc.
    name = re.sub(r'\s+(Inc\.?|Corp\.?|Corporation|Company|Co\.?|Ltd\.?|.com\.?|.in\.?|.org\.?)$', '', name, flags=re.IGNORECASE)
    name = name.strip()
    return name


if __name__ == "__main__":
    agent.run()
