import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("IP Geolocation Server")


@mcp.tool()
async def get_ip_location(
    ip: str = "",
    fields: str = "",
    lang: str = "en"
) -> dict:
    """
    Get geolocation information for an IP address.
    
    Args:
        ip: IP address to lookup (IPv4 or IPv6). Leave empty for current IP.
        fields: Comma-separated list of fields (e.g., 'country,city,lat,lon'). 
                Leave empty for all fields.
        lang: Language code for city/region names (en, de, es, pt-BR, fr, ja, zh-CN, ru)
    
    Returns:
        Dictionary containing geolocation data including:
        - country, countryCode, region, regionName, city, zip
        - lat, lon (coordinates)
        - timezone, isp, org, as (ISP info)
        - query (IP address that was queried)
    """
    # Build URL
    url = "http://ip-api.com/json/"
    if ip:
        url += ip
    
    # Build query parameters
    params = {}
    if fields:
        params["fields"] = fields
    if lang != "en":
        params["lang"] = lang
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "fail":
                return {
                    "error": data.get("message", "Unknown error"),
                    "status": "fail"
                }
            
            return data
    
    except httpx.HTTPError as e:
        return {
            "error": f"HTTP error occurred: {str(e)}",
            "status": "fail"
        }
    except Exception as e:
        return {
            "error": f"Error: {str(e)}",
            "status": "fail"
        }

@mcp.tool()
async def get_current_location() -> dict:
    """
    Get geolocation information for the current request IP.
    
    Returns:
        Dictionary with location details for the current IP including:
        - Geographic location (country, city, coordinates)
        - ISP and network information
        - Timezone
    """
    return await get_ip_location()


if __name__ == "__main__":
    # Run the server
    mcp.run()