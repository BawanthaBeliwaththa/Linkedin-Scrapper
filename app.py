from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import csv
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import LinkedInScraper

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

scraper = None

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scraper/init', methods=['POST'])
def init_scraper():
    global scraper
    
    try:
        if scraper:
            try:
                run_async(scraper.close())
            except:
                pass
            scraper = None
        
        data = request.json or {}
        
        async def init():
            global scraper
            scraper = LinkedInScraper(
                headless=data.get('headless', False),
                browser_type=data.get('browser_type', 'chromium'),
                session_name=data.get('session_name', 'default')
            )
            await scraper.initialize()
            return {'success': True, 'message': 'Browser initialized'}
        
        result = run_async(init())
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scraper/login', methods=['POST'])
def login():
    global scraper
    
    if not scraper:
        return jsonify({'success': False, 'error': 'Not initialized'}), 400
    
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        async def do_login():
            return await scraper.login(email, password)
        
        success = run_async(do_login())
        
        return jsonify({
            'success': success,
            'message': 'Login successful!' if success else 'Login failed'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scraper/search', methods=['POST'])
def search():
    global scraper
    
    if not scraper or not scraper.is_authenticated:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        company = data.get('company', '').strip()
        max_results = data.get('max_results', 10)
        
        if not first_name or not last_name:
            return jsonify({'success': False, 'error': 'Name required'}), 400
        
        async def do_search():
            return await scraper.search_people(first_name, last_name, company, max_results)
        
        results = run_async(do_search())
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scraper/extract', methods=['POST'])
def extract():
    global scraper
    
    if not scraper or not scraper.is_authenticated:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        profile_url = data.get('profile_url', '').strip()
        
        if not profile_url:
            return jsonify({'success': False, 'error': 'Profile URL required'}), 400
        
        async def do_extract():
            return await scraper.extract_profile(profile_url)
        
        profile = run_async(do_extract())
        
        return jsonify({
            'success': True,
            'profile': profile
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scraper/search-and-extract', methods=['POST'])
def search_and_extract():
    global scraper
    
    if not scraper or not scraper.is_authenticated:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        company = data.get('company', '').strip()
        max_profiles = data.get('max_profiles', 3)
        
        if not first_name or not last_name:
            return jsonify({'success': False, 'error': 'Name required'}), 400
        
        async def do_both():
            return await scraper.search_and_extract(first_name, last_name, company, max_profiles)
        
        result = run_async(do_both())
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scraper/stats', methods=['GET'])
def stats():
    global scraper
    
    if not scraper:
        return jsonify({'success': False, 'error': 'Not initialized'})
    
    try:
        async def get_stats():
            return await scraper.get_stats()
        
        stats_data = run_async(get_stats())
        return jsonify({'success': True, 'stats': stats_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scraper/close', methods=['POST'])
def close():
    global scraper
    
    try:
        if scraper:
            run_async(scraper.close())
            scraper = None
        return jsonify({'success': True, 'message': 'Closed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scraper/export', methods=['POST'])
def export_data():
    try:
        data = request.json
        export_data = data.get('data', {})
        format_type = data.get('format', 'json')
        
        if not export_data:
            return jsonify({'success': False, 'error': 'No data'}), 400
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == 'json':
            filename = f"linkedin_export_{timestamp}.json"
            filepath = Path("exports") / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return send_file(filepath, as_attachment=True, download_name=filename)
        
        elif format_type == 'csv':
            filename = f"linkedin_export_{timestamp}.csv"
            output = io.StringIO()
            writer = csv.writer(output)
            
            profiles = export_data.get('profiles', [])
            if profiles:
                # Write headers
                headers = ['Name', 'Headline', 'Location', 'Profile URL', 'About', 
                          'Experiences Count', 'Education Count', 'Skills Count']
                writer.writerow(headers)
                
                for profile in profiles:
                    writer.writerow([
                        profile.get('name', ''),
                        profile.get('headline', ''),
                        profile.get('location', ''),
                        profile.get('profile_url', ''),
                        profile.get('about', '')[:200],
                        len(profile.get('experiences', [])),
                        len(profile.get('education', [])),
                        len(profile.get('skills', []))
                    ])
            
            output.seek(0)
            from flask import make_response
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        
        return jsonify({'success': False, 'error': 'Invalid format'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("LinkedIn Scraper Server")
    print("http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)