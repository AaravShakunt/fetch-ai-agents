import json
import os
import requests
from bs4 import BeautifulSoup
from uagents import Agent, Context, Model

agent = Agent(name="company_processor", port=8004)

# Hugging Face API configuration
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "hf_api_key_here")

# Using a more reliable summarization model
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


def extract_text_from_website(url):
    """Extract text content from a website homepage."""
    try:
        # Add http if not present
        if not url.startswith('http'):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract meta data that might contain company info
        meta_description = ""
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            if tag.get('name') and tag.get('name').lower() == 'description' and tag.get('content'):
                meta_description = tag.get('content')
                break
                
        # Extract title
        title = soup.title.string if soup.title else ""
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Try to extract main content areas likely to contain company info
        main_content = ""
        
        # Prioritize main sections, headers, and prominent text
        priority_tags = soup.find_all(['main', 'header', 'h1', 'h2', 'section', 'div'], 
                                     class_=['hero', 'banner', 'intro', 'about', 'main', 'header'])
        
        for tag in priority_tags:
            main_content += tag.get_text(separator=' ', strip=True) + " "
        
        # Get overall page text as fallback
        all_text = soup.get_text(separator=' ', strip=True)
        
        # Clean up text (remove extra whitespace)
        lines = (line.strip() for line in all_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        all_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Get social media links
        social_links = []
        social_patterns = ['facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'tiktok']
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(pattern in href for pattern in social_patterns):
                social_links.append(href)
        
        # Package up the extracted data
        extracted_data = {
            "title": title,
            "meta_description": meta_description,
            "main_content": main_content[:1500] if main_content else "",  # First 1500 chars of priority content
            "all_text": all_text[:4000],  # First 4000 chars of all text as fallback
            "social_links": social_links[:5],  # Up to 5 social links
            "url": url
        }
        
        return extracted_data, url
    except Exception as e:
        return {"error": f"Error extracting content from website: {str(e)}"}, url


def get_company_info(website_data, website_url):
    """Extract company information using a Hugging Face model"""
    if "error" in website_data:
        return Error(text=website_data["error"])
    
    # Extract the domain from the URL
    domain = website_url.split('//')[-1].split('/')[0].replace('www.', '')
    
    # Create a more focused prompt for the model
    prompt = f"""You are an AI assistant that extracts company information from website text. Analyze the following content from {website_url} and extract key company details. Title: {website_data['title']} Meta Description: {website_data['meta_description']} Main Content: {website_data['main_content']} Social Links: {', '.join(website_data['social_links']) if website_data['social_links'] else 'None found'} Please extract the following information in JSON format: - company_name: The official name of the company - domain: {domain} - main_offerings: A brief description of the main products, services, or solutions the company offers (1-2 sentences) - tagline: The company's slogan or tagline if present - summary: A 2-3 sentence summary of what the company does and its key value proposition - contact_info: Any contact information visible on the homepage (email, phone, address) - social_media: List of social media platforms the company is present on Respond ONLY with a valid JSON object containing these fields."""
    # Prepare the payload for the Hugging Face API
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.1,
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
            # Find JSON-like structure in the text
            start_idx = generated_text.find('{')
            end_idx = generated_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = generated_text[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                
                # Ensure all required fields are present
                required_fields = ["company_name", "domain", "main_offerings", "tagline", 
                                 "summary", "contact_info", "social_media"]
                
                for field in required_fields:
                    if field not in parsed_data:
                        if field == "domain":
                            parsed_data[field] = domain
                        else:
                            parsed_data[field] = "Not found"
                    elif isinstance(parsed_data[field], dict) or isinstance(parsed_data[field], list):
                        # Convert nested JSON objects to strings
                        parsed_data[field] = str(parsed_data[field])
                
                # Add source URL
                parsed_data["source_url"] = website_url
                
                # Return as CompanyData object
                return CompanyData(**parsed_data)
            else:
                raise ValueError("No JSON structure found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback with best-guess extraction
            company_name = website_data['title'].split('-')[0].split('|')[0].strip() if website_data['title'] else domain.split('.')[0].title()
            
            # Extract tagline from meta description or title
            tagline = website_data['meta_description'][:100] if website_data['meta_description'] else ""
            if not tagline and len(website_data['title'].split('|')) > 1:
                tagline = website_data['title'].split('|')[1].strip()
            elif not tagline and len(website_data['title'].split('-')) > 1:
                tagline = website_data['title'].split('-')[1].strip()
            
            # Create a simple summary from the text we have
            text_for_summary = website_data['main_content'] if website_data['main_content'] else website_data['all_text'][:1000]
            
            fallback_data = {
                "company_name": company_name,
                "domain": domain,
                "main_offerings": extract_field_clean(generated_text, "main_offerings", "Products and services related to their industry"),
                "tagline": tagline[:100] if tagline else "Not found",
                "summary": f"This appears to be the website for {company_name}. " + 
                          (website_data['meta_description'] if website_data['meta_description'] else 
                           "The website contains information about their products, services, and company information."),
                "contact_info": extract_field_clean(generated_text, "contact_info", "Not found"),
                "social_media": ', '.join(website_data['social_links']) if website_data['social_links'] else "Not found",
                "source_url": website_url
            }
            return CompanyData(**fallback_data)
            
    except requests.exceptions.RequestException as e:
        return Error(text=f"Error connecting to Hugging Face API: {str(e)}")
    except Exception as e:
        # Fallback to domain-based information if everything else fails
        fallback_data = {
            "company_name": domain.split('.')[0].title(),
            "domain": domain,
            "main_offerings": "Unable to determine from homepage",
            "tagline": "Not found",
            "summary": f"This is the website for {domain.split('.')[0].title()}. Limited information could be extracted from the homepage.",
            "contact_info": "Not found",
            "social_media": "Not found",
            "source_url": website_url
        }
        return CompanyData(**fallback_data)


def extract_field_clean(text, field_name, default_value):
    """Helper function to extract field values from text"""
    try:
        # Try to find the field in the text
        lower_text = text.lower()
        field_pos = lower_text.find(field_name.lower())
        
        if field_pos != -1:
            # Find the value after the field name
            start = field_pos + len(field_name)
            
            # Look for the next field or end of text
            next_field_pos = float('inf')
            for field in ["company_name", "domain", "main_offerings", "tagline", 
                        "summary", "contact_info", "social_media"]:
                if field != field_name:
                    pos = lower_text.find(field.lower(), start)
                    if pos != -1 and pos < next_field_pos:
                        next_field_pos = pos
            
            # Extract the snippet
            end = min(next_field_pos, len(text)) if next_field_pos != float('inf') else len(text)
            snippet = text[start:end]
            
            # Clean up the snippet - remove JSON syntax and quotes
            snippet = snippet.strip().strip(':"\',.{}\n\t')
            
            # Remove any trailing commas or quotes
            if snippet.endswith(','):
                snippet = snippet[:-1]
            
            # Check if snippet is not empty
            if snippet and not snippet.isspace():
                return snippet
                
    except Exception:
        pass
    
    return default_value


@agent.on_message(model=Request)
async def handle_request(ctx: Context, sender: str, request: Request):
    """Process website URL and return company information"""
    ctx.logger.info(f"Received request to process website: {request.website}")
    
    # Extract text from website
    website_data, url = extract_text_from_website(request.website)
    
    if "error" in website_data:
        await ctx.send(sender, Error(text=website_data["error"]))
        return
    
    ctx.logger.info("Successfully extracted website content")
    
    # Process with Hugging Face model
    ctx.logger.info("Analyzing website content with Hugging Face model...")
    company_data = get_company_info(website_data, url)
    
    # Log the company data before sending
    if isinstance(company_data, CompanyData):
        ctx.logger.info(f"Sending company data: {company_data.company_name}")
    
    # Send response back
    await ctx.send(sender, company_data)


if __name__ == "__main__":
    agent.run()