"""
This agent can send a company website URL to the AI model agent and display the company information.
"""
import os
from uagents import Agent, Context, Model

agent = Agent(name="company_requestor", port=8003, endpoint=["http://localhost:8003/submit"])

# Replace with the website you want to get information about
WEBSITE_URL = "apple.com"

# Get agent address from environment with fallback options
# For local testing, we'll use the address of the locally hosted website analyzer agent
# In production, use the remote agent address
USE_LOCAL_AGENT = os.environ.get("USE_LOCAL_AGENT", "true").lower() == "true"

# Local and remote agent addresses
LOCAL_AGENT_ADDRESS = "agent1q0zllemwuq5swr5tfudeeq7k9a4nrs92q6f8cft64cgzvv5mmgs77csa7jx"  # This should match the website_analyzer agent address
REMOTE_AGENT_ADDRESS = "agent1qgk5zq6eczlunmdu3ffc009v8qjle4nvdly8yjwxupztylkrf0r7gnx5fjy"

# Select the appropriate address based on environment
COMPANY_INFO_PROCESSOR_ADDRESS = LOCAL_AGENT_ADDRESS if USE_LOCAL_AGENT else REMOTE_AGENT_ADDRESS

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
    
    if USE_LOCAL_AGENT:
        ctx.logger.info(f"Using local website analyzer agent at address: {COMPANY_INFO_PROCESSOR_ADDRESS}")
    else:
        ctx.logger.info(f"Using remote website analyzer agent at address: {COMPANY_INFO_PROCESSOR_ADDRESS}")
    
    await ctx.send(COMPANY_INFO_PROCESSOR_ADDRESS, Request(website=WEBSITE_URL))


@agent.on_message(model=CompanyData)
async def handle_company_data(ctx: Context, sender: str, data: CompanyData):
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


@agent.on_message(model=Error)
async def handle_error(ctx: Context, sender: str, error: Error):
    """Log error from company info processor agent"""
    ctx.logger.info(f"Got error from company info processor agent: {error.text}")


if __name__ == "__main__":
    agent.run()
