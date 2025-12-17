import requests
import re
import json
import argparse
import os

def load_cookies(cookie_file):
    """Load cookies from a Netscape format cookie file and return a Cookie header string."""
    cookie_header = []
    try:
        with open(cookie_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue  # Skip comments and empty lines
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    if domain.startswith('.'):
                        domain = domain[1:]  # Remove leading dot
                    
                    cookie_name = parts[5]
                    cookie_value = parts[6]
                    cookie_header.append(f"{cookie_name}={cookie_value}")
    except Exception as e:
        print(f"Error loading cookies: {str(e)}")
    return '; '.join(cookie_header)

def get_stream_url(url):
    # Validate the new URL structure
    if url.startswith("https://npo.nl/start/afspelen/"):
        try:
            # Load cookies from cookies.txt if it exists
            cookie_file = 'cookies.txt'
            cookie_header = load_cookies(cookie_file) if os.path.exists(cookie_file) else None

            # Step 1: Make a request to the input URL
            headers = {'Cookie': cookie_header} if cookie_header else {}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Extract the JSON data embedded in the HTML
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
            if match:
                json_data = match.group(1)
                data = json.loads(json_data)

                product_info = None
                slug = url.split('/')[-1]

                for item in data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', []):
                    state = item.get('state', {})
                    if state:
                        episode_data = state.get('data', {})
                        if isinstance(episode_data, dict):
                            if episode_data.get('slug') == slug:
                                product_info = {
                                    'productId': episode_data.get('productId'),
                                    'guid': episode_data.get('guid')
                                }
                                break

                if product_info:
                    # Step 2: Get JWT using the same cookies
                    token_url = f"https://npo.nl/start/api/domain/player-token?productId={product_info['productId']}"
                    token_response = requests.get(token_url, headers=headers)
                    token_response.raise_for_status()
                    jwt = token_response.json().get('jwt')

                    if jwt:
                        # Step 3: Make POST request to get stream link
                        post_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                            "Authorization": jwt,
                            "Content-Type": "application/json",
                            "Accept": "*/*",
                            "Referer": "https://npo.nl/",
                            'Cookie': cookie_header
                        }
                        
                        body = {
                            "profileName": "dash",
                            "drmType": "widevine",
                            "referrerUrl": url,
                            "ster": {
                                "identifier": "npo-app-desktop",
                                "deviceType": 4,
                                "player": "web"
                            }
                        }
                        
                        # Send the POST request to get the stream link
                        stream_response = requests.post("https://prod.npoplayer.nl/stream-link", headers=post_headers, json=body)
                        stream_response.raise_for_status()
                        
                        # Step 4: Extract streams URL and drmToken
                        stream_data = stream_response.json().get('stream', {})
                        stream_url = stream_data.get('streamURL', "streamURL not found in response.")
                        drm_token = stream_data.get('drmToken', "drmToken not found in response.")
                        
                        return (stream_url, drm_token)  # Return both if needed
                
                return "Product ID and GUID not found for the given slug."
            return "JSON script not found in the response."
        except requests.exceptions.RequestException as e:
            return f"An error occurred while making the request: {str(e)}"
        except json.JSONDecodeError:
            return "Failed to decode JSON data."
    return "Invalid URL. Please provide a URL that starts with 'https://npo.nl/start/afspelen/'."

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get the streaming URL from an NPO series page.")
    parser.add_argument("url", type=str, help="The URL of the NPO series page.")
    args = parser.parse_args()

    stream_url_response = get_stream_url(args.url)

    # Print the final result
    if isinstance(stream_url_response, tuple):
        print(f"Stream URL: {stream_url_response[0]}")
        print(f"DRM Token: {stream_url_response[1]}")
    else:
        print(stream_url_response)
