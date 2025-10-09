import requests
import re
import json
import argparse

def get_stream_url(url):
    if url.startswith("https://npo.nl/start/serie/") and url.endswith("/afspelen"):
        try:
            # Step 1: Get the JSON data
            response = requests.get(url)
            response.raise_for_status()

            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
            if match:
                json_data = match.group(1)
                data = json.loads(json_data)

                product_info = None
                for item in data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', []):
                    for episode_data in item.get('state', {}).get('data', []):
                        # Debug output to understand structure
                        if isinstance(episode_data, dict) and episode_data.get('slug') == url.split('/')[-2]:
                            product_info = {
                                'productId': episode_data.get('productId'),
                                'guid': episode_data.get('guid')
                            }
                            break
                    if product_info:
                        break

                if product_info:
                    # Step 2: Get JWT
                    token_url = f"https://npo.nl/start/api/domain/player-token?productId={product_info['productId']}"
                    token_response = requests.get(token_url)
                    token_response.raise_for_status()
                    jwt = token_response.json().get('jwt')

                    if jwt:
                        # Step 3: Make POST request to get stream link
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                            "Authorization": jwt,
                            "Content-Type": "application/json",
                            "Accept": "*/*",
                            "Referer": "https://npo.nl/"
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
                        
                        stream_response = requests.post("https://prod.npoplayer.nl/stream-link", headers=headers, json=body)
                        stream_response.raise_for_status()
                        
                        # Step 4: Extract streams URL and drmToken
                        stream_data = stream_response.json().get('stream', {})
                        stream_url = stream_data.get('streamURL', "streamURL not found in response.")
                        drm_token = stream_data.get('drmToken', "drmToken not found in response.")
                        
                        return (stream_url, drm_token)  # Return both if needed
                
                return "Product ID and GUID not found for the given slug."
            return "JSON script not found in the response."
        except requests.exceptions.RequestException as e:
            return f"An error occurred: {str(e)}"
        except json.JSONDecodeError:
            return "Failed to decode JSON data."
    return "Invalid URL. Please provide a URL that starts with 'https://npo.nl/start/serie/' and ends with '/afspelen'."

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
