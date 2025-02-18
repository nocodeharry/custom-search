from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Google Custom Search API configuration
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
SEARCH_ENGINE_ID = os.environ.get('SEARCH_ENGINE_ID')
GOOGLE_SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/search', methods=['GET', 'POST'])
def api_search():
    """
    Search endpoint that accepts both GET and POST requests.
    
    Curl examples:
    GET:  curl "http://localhost:5000/api/search?q=your+search+query"
    POST: curl -X POST -H "Content-Type: application/json" -d '{"query":"your search query"}' http://localhost:5000/api/search
    """
    if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
        return jsonify({
            'error': 'Search service configuration is missing. Please check GOOGLE_API_KEY and SEARCH_ENGINE_ID environment variables.'
        }), 500

    if request.method == 'POST':
        data = request.get_json()
        query = data.get('query', '')
    else:
        query = request.args.get('q', '')

    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    try:
        params = {
            'key': GOOGLE_API_KEY,
            'cx': SEARCH_ENGINE_ID,
            'q': query,
            'num': 10
        }
        
        response = requests.get(GOOGLE_SEARCH_API_URL, params=params)
        response.raise_for_status()  # This will raise an exception for bad status codes
        search_results = response.json()
        
        if 'error' in search_results:
            error_message = search_results.get('error', {}).get('message', 'Unknown error occurred')
            print(f"Google API Error: {error_message}")
            return jsonify({
                'error': f'Search API error: {error_message}',
                'details': search_results.get('error', {})
            }), 500
            
        results = []
        if 'items' in search_results:
            for item in search_results['items']:
                results.append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
        
        return jsonify({
            'status': 'success',
            'query': query,
            'results': results
        })

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {str(e)}")
        return jsonify({
            'error': 'Failed to connect to Google Search API',
            'details': str(e)
        }), 500
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape', methods=['GET', 'POST'])
def api_scrape():
    """
    Scrape endpoint that accepts both GET and POST requests.
    
    Curl examples:
    GET:  curl "http://localhost:5000/api/scrape?url=https://example.com"
    POST: curl -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com"}' http://localhost:5000/api/scrape
    """
    if request.method == 'POST':
        data = request.get_json()
        url = data.get('url', '')
    else:
        url = request.args.get('url', '')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        for script in soup(["script", "style"]):
            script.decompose()

        content = {
            'title': soup.title.string if soup.title else 'No title found',
            'headings': {
                'h1': [],
                'h2': [],
                'h3': [],
                'h4': [],
                'h5': [],
                'h6': []
            },
            'structure': []
        }

        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_level = tag.name
            heading_text = tag.get_text(strip=True)
            
            if not heading_text:
                continue
                
            content['headings'][heading_level].append(heading_text)
            content['structure'].append({
                'level': int(heading_level[1]),
                'text': heading_text
            })

        return jsonify({
            'status': 'success',
            'url': url,
            'content': content
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
