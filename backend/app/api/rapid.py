import json
import http.client
from typing import Optional
from app.config import config, RAW_RENTAL_DATA_API_SETTINGS
def get_rightmove_data(_config: Optional[RAW_RENTAL_DATA_API_SETTINGS] = None,
                       REGION: str = "87490",
                       search_radius: str = '0.0') -> Optional[str]:
    """
    Fetches property data from Rightmove using RapidAPI.
    Iterates through pages to fetch all data.
    Returns the response data as a string.
    """
    raw_rental_data_api_config = _config or config.raw_rental_data_api
    assert raw_rental_data_api_config is not None

    # Create a connection to the Rightmove API
    conn = http.client.HTTPSConnection(raw_rental_data_api_config.api_src)

    headers = {
        'x-rapidapi-key': raw_rental_data_api_config.api_key,
        'x-rapidapi-host': raw_rental_data_api_config.api_src
    }

    all_data = []
    page = 1

    while True:
        conn.request("GET", f"/rent/student-property-to-rent?identifier=REGION%5E{REGION}&page={page}&sort_by=HighestPrice&search_radius={search_radius}&added_to_site=1", headers=headers)
        res = conn.getresponse()
        data = res.read()
        decoded_data = data.decode("utf-8")
        try:
            json_data = json.loads(decoded_data)
            # Check if there's an error message
            if "messages" in json_data:
                print(f"API Error: {json_data['messages']}")
                break
            
            # The actual data is in the "data" field, not "properties"
            properties = json_data.get("data", [])
            if not properties:  # Stop if no more properties
                break
            all_data.extend(properties)
            page += 1
        except json.JSONDecodeError:
            print(f"Failed to decode JSON data on page {page}: {decoded_data[:200]}...")
            break

    # Save the complete data structure
    complete_data = {
        "currentPage": page - 1,  # Total pages fetched
        "totalResults": len(all_data),
        "data": all_data
    }
    
    json_file_path = f"{raw_rental_data_api_config.data_path}/raw/rightmove_data.json"
    with open(json_file_path, "w") as json_file:
        json.dump(complete_data, json_file, indent=4)

    return json_file_path

if __name__ == "__main__":
    # Example usage
    get_rightmove_data()
    print("Rightmove data fetched and saved successfully.")