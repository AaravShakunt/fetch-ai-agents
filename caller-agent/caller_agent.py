"""
This agent can send a company website URL to the AI model agent and display the company information.
"""
from uagents import Agent, Context, Model

agent = Agent(name="company_requestor")

# Replace with the website you want to get information about
WEBSITE_URL = "speargrowth.com"

COMPANY_INFO_PROCESSOR_ADDRESS = "agent1qgk5zq6eczlunmdu3ffc009v8qjle4nvdly8yjwxupztylkrf0r7gnx5fjy"

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
