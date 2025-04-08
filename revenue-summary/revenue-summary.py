import json
import os
import requests
from bs4 import BeautifulSoup
from uagents import Agent, Context, Model

agent = Agent(name="revenue_summary", port=8009)

# Hugging Face API configuration

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ALPHAVANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY")

# Using the Falcon-7B-Instruct model
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
HEADERS = {
    "Content-Type": "application/json"
}


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

def get_revenue_summary(company_overview):
    # Formatted prompt that explicitly requests JSON formatting with specific keys
    prompt = f"""You are a specialized financial analyst. Analyze the following company data: {json.dumps(company_overview, indent=2)} Create a comprehensive financial analysis with the following structure: 1. Company Overview: Briefly describe the company's business model and sector. 2. Valuation: Analyze P/E, PEG, P/S, P/B, EV/EBITDA ratios. 3. Profitability: Review profit margins, ROE, ROA, and operational efficiency. 4. Growth: Examine revenue and earnings growth rates. 5. Financial Health: Assess EPS, book value, and dividend policies. 6. Stock Performance: Evaluate beta, moving averages, and 52-week range. 7. Analyst Sentiment: Summarize analyst ratings and target prices. Return ONLY a valid JSON object with these exact keys: 'company_overview_summary', 'valuation_summary', 'profitability_summary', 'growth_summary', 'financial_health_summary', 'stock_performance_summary', 'analyst_sentiment_summary' Each value should be a concise, insightful paragraph without any formatting. Do not include any text outside the JSON object."""

    payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": prompt
                }
            ]
        }
    ]
    }

    try:
        # Make request to Gemini API
        response = requests.post(GEMINI_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()

        # Extract the response
        result = response.json()
        # Parse the actual text content from Gemini's response structure
        generated_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean the text to extract just the JSON part
        # Remove markdown code block indicators if present
        cleaned_text = generated_text.replace('```json', '').replace('```', '').strip()
        
        # Parse the JSON
        parsed_data = json.loads(cleaned_text)
        
        # Create and return a CompanyAnalysis object with the extracted data
        return CompanyAnalysis(
            company_overview_summary=parsed_data.get("company_overview_summary", "No company overview information available."),
            valuation_summary=parsed_data.get("valuation_summary", "No valuation information available."),
            profitability_summary=parsed_data.get("profitability_summary", "No profitability information available."),
            growth_summary=parsed_data.get("growth_summary", "No growth information available."),
            financial_health_summary=parsed_data.get("financial_health_summary", "No financial health information available."),
            stock_performance_summary=parsed_data.get("stock_performance_summary", "No stock performance information available."),
            analyst_sentiment_summary=parsed_data.get("analyst_sentiment_summary", "No analyst sentiment information available.")
        )

    except requests.exceptions.RequestException as e:
        # Handle API connection errors
        return CompanyAnalysis(
            company_overview_summary=f"Error connecting to Gemini API: {str(e)}",
            valuation_summary="Error: Connection failure",
            profitability_summary="Error: Connection failure",
            growth_summary="Error: Connection failure",
            financial_health_summary="Error: Connection failure",
            stock_performance_summary="Error: Connection failure",
            analyst_sentiment_summary="Error: Connection failure"
        )
    except json.JSONDecodeError as e:
        # Handle JSON parsing errors
        return CompanyAnalysis(
            company_overview_summary=f"Error parsing JSON from API response: {str(e)}",
            valuation_summary="Error: JSON parsing failure",
            profitability_summary="Error: JSON parsing failure",
            growth_summary="Error: JSON parsing failure",
            financial_health_summary="Error: JSON parsing failure",
            stock_performance_summary="Error: JSON parsing failure",
            analyst_sentiment_summary="Error: JSON parsing failure"
        )
    except Exception as e:
        # Handle any other unexpected errors
        return CompanyAnalysis(
            company_overview_summary=f"Unexpected error: {str(e)}",
            valuation_summary="Error: Unexpected failure",
            profitability_summary="Error: Unexpected failure",
            growth_summary="Error: Unexpected failure",
            financial_health_summary="Error: Unexpected failure",
            stock_performance_summary="Error: Unexpected failure",
            analyst_sentiment_summary="Error: Unexpected failure"
        )

def get_company_overview(ticker):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}'
    r = requests.get(url)
    data = r.json()
    return data

# @agent.on_event("startup")
# async def request_company_info(ctx: Context):
#     ctx.logger.info(f"Requesting company information for ticker: {company_test_ticker}")
#     overview = get_company_overview("IBM")
#     ctx.logger.info(f"Overview {str(overview)}")
#     revenue_overview_summary = get_revenue_summary(overview)
#     ctx.logger.info(f"Revenue Overview Summary {str(revenue_overview_summary)}")


@agent.on_message(model=overviewRequest)
async def handle_response(ctx: Context, sender: str, msg: overviewRequest):
    ctx.logger.info(f"Received response from {sender}:")
    overview = get_company_overview(msg.ticker)
    revenue_overview_summary = get_revenue_summary(overview)
    ctx.logger.info(f"Revenue Overview Summary {str(revenue_overview_summary)}")
    await ctx.send(sender,revenue_overview_summary)




