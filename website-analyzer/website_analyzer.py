import json
import os
import requests
from bs4 import BeautifulSoup
from uagents import Agent, Context, Model

agent = Agent(name="company_processor")

# Hugging Face API configuration
# Get a free API token from https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "hf_api_key_here")

# Using the Falcon-7B-Instruct model - a good free option for instruction following
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"
HEADERS = {
    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
    "Content-Type": "application/json"
}


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


def extract_text_from_website(url):
    """Extract text content from a website."""
    try:
        # Add http if not present
        if not url.startswith('http'):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up text (remove extra whitespace)
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Return a reasonable chunk of text (GPT context limits)
        return text[:4000], url  # Using a smaller limit for Hugging Face models
    except Exception as e:
        return f"Error extracting content from website: {str(e)}", url


def get_company_info(website_text, website_url):
    """Extract company information using a Hugging Face model"""
    # Create a prompt for the model
    prompt = f"""
You are a helpful AI assistant that extracts company information from website text.
Analyze the following text from {website_url} and extract key company details.

Website content:
{website_text}

Please extract the following information in JSON format:
- company_name: The name of the company
- industry: The industry or sector the company operates in
- products_services: Description of products and services offered
- company_size: Number of employees (if available, otherwise 'Not found')
- headquarters: Location of headquarters (if available, otherwise 'Not found')
- year_founded: Year the company was founded (if available, otherwise 'Not found')
- leadership: Key executives or leadership team (if available, otherwise 'Not found')
- description: Mission statement or company description

Respond ONLY with a valid JSON object containing these fields.
"""

    # Prepare the payload for the Hugging Face API
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.1,  # Low temperature for more deterministic output
            "return_full_text": False
        }
    }

    try:
        # Make request to Hugging Face Inference API
        response = requests.post(HUGGINGFACE_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        
        # Extract the generated text from the response
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            generated_text = result[0].get('generated_text', '')
        else:
            generated_text = result.get('generated_text', '')
            
        # Try to extract JSON from the response
        try:
            # First, try to find JSON-like structure in the text
            start_idx = generated_text.find('{')
            end_idx = generated_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = generated_text[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                
                # Ensure all required fields are present
                required_fields = ["company_name", "industry", "products_services", "company_size", 
                                "headquarters", "year_founded", "leadership", "description"]
                
                for field in required_fields:
                    if field not in parsed_data:
                        parsed_data[field] = "Not found"
                
                # Add source URL
                parsed_data["source_url"] = website_url
                
                # Return as CompanyData object
                return CompanyData(**parsed_data)
            else:
                raise ValueError("No JSON structure found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to extracting structured information from text
            # This is for cases where the model doesn't return proper JSON
            company_data = {
                "company_name": extract_field(generated_text, "company_name", website_url),
                "industry": extract_field(generated_text, "industry", "Technology"),
                "products_services": extract_field(generated_text, "products_services", "Various products and services"),
                "company_size": extract_field(generated_text, "company_size", "Not found"),
                "headquarters": extract_field(generated_text, "headquarters", "Not found"),
                "year_founded": extract_field(generated_text, "year_founded", "Not found"),
                "leadership": extract_field(generated_text, "leadership", "Not found"),
                "description": extract_field(generated_text, "description", "Company providing various services"),
                "source_url": website_url
            }
            return CompanyData(**company_data)
            
    except requests.exceptions.RequestException as e:
        return Error(text=f"Error connecting to Hugging Face API: {str(e)}")
    except Exception as e:
        # Fallback to domain-based information if everything else fails
        domain = website_url.split('//')[-1].split('/')[0].replace('www.', '')
        company_name = domain.split('.')[0].title()
        
        fallback_data = {
            "company_name": company_name,
            "industry": "Unknown",
            "products_services": "Unknown",
            "company_size": "Not found",
            "headquarters": "Not found",
            "year_founded": "Not found",
            "leadership": "Not found",
            "description": f"Information extracted from {website_url}",
            "source_url": website_url
        }
        return CompanyData(**fallback_data)


def extract_field(text, field_name, default_value):
    """Helper function to extract field values from text when JSON parsing fails"""
    # Try to find the field in the text
    lower_text = text.lower()
    field_pos = lower_text.find(field_name.lower())
    
    if field_pos != -1:
        # Find the value after the field name
        start = field_pos + len(field_name)
        # Look for the next 50 characters or until end of line
        end = min(start + 100, len(text))
        snippet = text[start:end]
        
        # Clean up the snippet
        snippet = snippet.strip(': "\'.,\n\t')
        if snippet:
            return snippet
    
    return default_value


@agent.on_message(model=Request)
async def handle_request(ctx: Context, sender: str, request: Request):
    """Process website URL and return company information"""
    ctx.logger.info(f"Received request to process website: {request.website}")
    
    # Extract text from website
    website_text, url = extract_text_from_website(request.website)
    
    if website_text.startswith("Error"):
        await ctx.send(sender, Error(text=website_text))
        return
    
    ctx.logger.info("Successfully extracted website text")
    
    # Process with Hugging Face model
    ctx.logger.info("Analyzing website content with Hugging Face model...")
    response = get_company_info(website_text, url)
    
    # Send response back
    await ctx.send(sender, response)


if __name__ == "__main__":
    agent.run()