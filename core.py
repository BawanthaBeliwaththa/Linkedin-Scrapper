import asyncio
import random
import time
import json
import os
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from datetime import datetime
import pickle
from pathlib import Path

class SessionManager:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
    
    def save(self, name: str, cookies: List[Dict]) -> bool:
        try:
            with open(self.sessions_dir / f"{name}.pkl", 'wb') as f:
                pickle.dump({'cookies': cookies, 'created_at': datetime.now().isoformat()}, f)
            return True
        except Exception as e:
            print(f"Session save error: {e}")
            return False
    
    def load(self, name: str) -> Optional[Dict]:
        try:
            file_path = self.sessions_dir / f"{name}.pkl"
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
        except:
            pass
        return None
    
    def list_sessions(self) -> List[str]:
        return [f.stem for f in self.sessions_dir.glob("*.pkl")]

class LinkedInScraper:
    def __init__(self, headless: bool = False, browser_type: str = "chromium", 
                 session_name: str = "default"):
        self.headless = headless
        self.browser_type = browser_type
        self.session_name = session_name
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_authenticated = False
        self.session_manager = SessionManager()
        
        self.stats = {
            'requests_made': 0,
            'profiles_scraped': 0,
            'errors': 0,
            'start_time': None,
            'runtime_seconds': 0
        }
    
    async def initialize(self):
        print("Initializing browser...")
        self.stats['start_time'] = datetime.now()
        
        self.playwright = await async_playwright().start()
        
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080',
        ]
        
        if self.browser_type == "firefox":
            self.browser = await self.playwright.firefox.launch(headless=self.headless)
        else:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=args
            )
        
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        ]
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(user_agents),
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        
        print("Browser initialized")
        return self
    
    async def _random_delay(self, min_s: float = 1, max_s: float = 3):
        await asyncio.sleep(random.uniform(min_s, max_s))
        self.stats['requests_made'] += 1
    
    async def login(self, email: str, password: str) -> bool:
        print(f"Logging in as {email}")
        
        # Try session restore
        saved = self.session_manager.load(self.session_name)
        if saved:
            print("Loading saved session...")
            await self.context.add_cookies(saved['cookies'])
            
            await self.page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
            await self._random_delay(2, 4)
            
            if 'feed' in self.page.url:
                print("Session restored!")
                self.is_authenticated = True
                return True
        
        await self.page.goto('https://www.linkedin.com/login', wait_until='networkidle')
        await self._random_delay(2, 4)
        
        await self.page.fill('input#username', email)
        await self._random_delay(0.5, 1)
        await self.page.fill('input#password', password)
        await self._random_delay(0.5, 1)
        
        await self.page.click('button[type="submit"]')
        await self._random_delay(3, 6)
        
        # Handle checkpoint
        if 'checkpoint' in self.page.url:
            print("Security check required - complete it in browser")
            for i in range(120):
                await asyncio.sleep(1)
                if 'feed' in self.page.url:
                    print("Security check passed!")
                    break
        
        if 'feed' in self.page.url:
            print("Login successful!")
            self.is_authenticated = True
            
            # Save session
            cookies = await self.context.cookies()
            self.session_manager.save(self.session_name, cookies)
            return True
        
        print("Login failed")
        return False
    
    async def search_people(self, first_name: str, last_name: str, 
                           company: str = "", max_results: int = 10) -> List[Dict]:
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        print(f"Searching: {first_name} {last_name}")
        
        query = f"{first_name} {last_name}"
        if company:
            query += f" {company}"
        
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={query.replace(' ', '%20')}"
        
        await self.page.goto(search_url, wait_until='domcontentloaded')
        await self._random_delay(3, 5)
        
        for _ in range(3):
            await self.page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(1.5)
        
        results = []
        
        cards = await self.page.query_selector_all('.reusable-search__result-container, .entity-result__item')
        print(f"Found {len(cards)} cards")
        
        for card in cards[:max_results]:
            try:
                link = await card.query_selector('a[href*="/in/"]')
                if not link:
                    continue
                
                href = await link.get_attribute('href')
                if not href:
                    continue
                
                profile_url = href if href.startswith('http') else f"https://www.linkedin.com{href}"
                profile_url = profile_url.split('?')[0]
                
                name = f"{first_name} {last_name}"
                name_elem = await card.query_selector('span[aria-hidden="true"]')
                if name_elem:
                    name_text = await name_elem.text_content()
                    if name_text and name_text.strip():
                        name = name_text.strip().split('\n')[0].strip()
                
                headline = ""
                headline_elem = await card.query_selector('.entity-result__primary-subtitle')
                if headline_elem:
                    headline = (await headline_elem.text_content()).strip()
                
                results.append({
                    'name': name,
                    'headline': headline,
                    'profile_url': profile_url
                })
                
            except Exception as e:
                continue
        
        seen = set()
        unique = []
        for r in results:
            if r['profile_url'] not in seen:
                seen.add(r['profile_url'])
                unique.append(r)
        
        print(f"Found {len(unique)} unique profiles")
        return unique
    
    async def extract_profile(self, profile_url: str) -> Dict:
        print(f"Extracting: {profile_url}")
        
        try:
            await self.page.goto(profile_url, wait_until='domcontentloaded')
            await self._random_delay(3, 5)
            
            for _ in range(5):
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
            
            await self.page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(2)
            
            await self.page.wait_for_selector('h1', timeout=10000)
            
            profile_data = await self.page.evaluate('''
                () => {
                    const data = {
                        name: '',
                        headline: '',
                        location: '',
                        connections: '',
                        about: '',
                        experiences: [],
                        education: [],
                        skills: [],
                        featured: [],
                        recommendations: [],
                        certifications: [],
                        volunteer: [],
                        courses: [],
                        projects: [],
                        honors: [],
                        languages: []
                    };
                    
                    // Get name - try multiple selectors
                    const h1 = document.querySelector('h1');
                    if (h1) data.name = h1.textContent.trim();
                    
                    // Get headline
                    const headlineElem = document.querySelector('.text-body-medium.break-words, [class*="headline"]');
                    if (headlineElem) data.headline = headlineElem.textContent.trim();
                    
                    // Get location
                    const locationElem = document.querySelector('.text-body-small.inline.t-black--light.break-words, [class*="location"]');
                    if (locationElem) data.location = locationElem.textContent.trim();
                    
                    // Get connections
                    const connectionsSpan = document.querySelector('.t-bold span[aria-hidden="true"], [class*="connection"]');
                    if (connectionsSpan) data.connections = connectionsSpan.textContent.trim();
                    
                    // Get ABOUT section
                    const aboutSection = document.querySelector('#about, [data-section="about"]');
                    if (aboutSection) {
                        const parent = aboutSection.closest('section');
                        if (parent) {
                            const aboutText = parent.querySelector('.inline-show-more-text, .display-flex.ph5.pv3, .pv-shared-text-with-see-more');
                            if (aboutText) {
                                data.about = aboutText.textContent.trim().substring(0, 2000);
                            }
                        }
                    }
                    
                    // Get EXPERIENCE
                    const expSection = document.querySelector('#experience, [data-section="experience"]');
                    if (expSection) {
                        const parent = expSection.closest('section');
                        if (parent) {
                            const expItems = parent.querySelectorAll('li.pvs-list__paged-list-item, li.artdeco-list__item');
                            expItems.forEach(item => {
                                const titleEl = item.querySelector('.t-bold span[aria-hidden="true"], .mr1.t-bold');
                                const companyEl = item.querySelector('.t-14.t-normal span[aria-hidden="true"], .t-14.t-normal:first-of-type');
                                const durationEl = item.querySelector('.t-14.t-normal.t-black--light span[aria-hidden="true"], .pvs-entity__caption-wrapper');
                                const descriptionEl = item.querySelector('.pvs-list__container, .inline-show-more-text');
                                
                                const exp = {
                                    title: titleEl ? titleEl.textContent.trim() : '',
                                    company: companyEl ? companyEl.textContent.trim() : '',
                                    duration: durationEl ? durationEl.textContent.trim() : '',
                                    description: descriptionEl ? descriptionEl.textContent.trim().substring(0, 500) : ''
                                };
                                
                                if (exp.title || exp.company) {
                                    data.experiences.push(exp);
                                }
                            });
                        }
                    }
                    
                    // Get EDUCATION
                    const eduSection = document.querySelector('#education, [data-section="education"]');
                    if (eduSection) {
                        const parent = eduSection.closest('section');
                        if (parent) {
                            const eduItems = parent.querySelectorAll('li.pvs-list__paged-list-item, li.artdeco-list__item');
                            eduItems.forEach(item => {
                                const schoolEl = item.querySelector('.t-bold span[aria-hidden="true"], .mr1.t-bold');
                                const degreeEl = item.querySelector('.t-14.t-normal span[aria-hidden="true"]');
                                const yearEl = item.querySelector('.t-14.t-normal.t-black--light span[aria-hidden="true"]');
                                
                                const edu = {
                                    school: schoolEl ? schoolEl.textContent.trim() : '',
                                    degree: degreeEl ? degreeEl.textContent.trim() : '',
                                    year: yearEl ? yearEl.textContent.trim() : ''
                                };
                                
                                if (edu.school) {
                                    data.education.push(edu);
                                }
                            });
                        }
                    }
                    
                    // Get SKILLS
                    const skillsSection = document.querySelector('#skills, [data-section="skills"]');
                    if (skillsSection) {
                        const parent = skillsSection.closest('section');
                        if (parent) {
                            const skillItems = parent.querySelectorAll('span[aria-hidden="true"]');
                            skillItems.forEach(skill => {
                                const text = skill.textContent.trim();
                                if (text && text.length > 1 && text.length < 50 && 
                                    !text.includes('Skills') && !text.includes('skill') &&
                                    !text.includes('endorsement') && !text.includes('profile')) {
                                    data.skills.push(text);
                                }
                            });
                        }
                    }
                    
                    // Get FEATURED section
                    const featuredSection = document.querySelector('#featured, [data-section="featured"]');
                    if (featuredSection) {
                        const parent = featuredSection.closest('section');
                        if (parent) {
                            const items = parent.querySelectorAll('li.pvs-list__paged-list-item');
                            items.forEach(item => {
                                const text = item.textContent.trim();
                                if (text && text.length > 5) {
                                    data.featured.push(text.substring(0, 200));
                                }
                            });
                        }
                    }
                    
                    // Get CERTIFICATIONS
                    const certSection = document.querySelector('#certifications, [data-section="certifications"]');
                    if (certSection) {
                        const parent = certSection.closest('section');
                        if (parent) {
                            const items = parent.querySelectorAll('li.pvs-list__paged-list-item');
                            items.forEach(item => {
                                const text = item.textContent.trim();
                                if (text && text.length > 5) {
                                    data.certifications.push(text.substring(0, 200));
                                }
                            });
                        }
                    }
                    
                    return data;
                }
            ''')
            
            if not profile_data.get('name'):
                print("JS extraction failed, trying HTML fallback...")
                content = await self.page.content()
                profile_data = await self._fallback_extraction(content, profile_url)
            
            # Clean up empty arrays
            for key in ['experiences', 'education', 'skills', 'featured', 'certifications', 'volunteer', 'courses', 'projects', 'honors', 'languages']:
                if key in profile_data and not profile_data[key]:
                    profile_data[key] = []
            
            # Add metadata
            profile_data['profile_url'] = profile_url
            profile_data['scraped_at'] = datetime.now().isoformat()
            
            self.stats['profiles_scraped'] += 1
            
            print(f"Extracted: {profile_data.get('name', 'Unknown')}")
            print(f"Experiences: {len(profile_data.get('experiences', []))}")
            print(f"Education: {len(profile_data.get('education', []))}")
            print(f"Skills: {len(profile_data.get('skills', []))}")
            
            return profile_data
            
        except Exception as e:
            print(f"Extraction error: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
            return {
                'profile_url': profile_url,
                'name': '',
                'headline': '',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    async def _fallback_extraction(self, html: str, profile_url: str) -> Dict:
        print("Using fallback HTML extraction...")
        
        data = {
            'name': '',
            'headline': '',
            'location': '',
            'about': '',
            'experiences': [],
            'education': [],
            'skills': []
        }
        
        try:
            json_ld_data = await self.page.evaluate('''
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const script of scripts) {
                        try {
                            const data = JSON.parse(script.textContent);
                            if (data['@type'] === 'Person') {
                                return {
                                    name: data.name || '',
                                    headline: data.description || '',
                                    sameAs: data.sameAs || ''
                                };
                            }
                        } catch(e) {}
                    }
                    return null;
                }
            ''')
            
            if json_ld_data:
                data['name'] = json_ld_data.get('name', '')
                data['headline'] = json_ld_data.get('headline', '')
            
            sections = await self.page.evaluate('''
                () => {
                    const sections = {};
                    
                    // Get all section headers and their content
                    const sectionElems = document.querySelectorAll('section');
                    sectionElems.forEach(section => {
                        const header = section.querySelector('h2, h3');
                        if (header) {
                            const headerText = header.textContent.trim().toLowerCase();
                            const content = section.textContent.trim().substring(0, 1000);
                            
                            if (headerText.includes('about')) sections.about = content;
                            if (headerText.includes('experience')) sections.experience = content;
                            if (headerText.includes('education')) sections.education = content;
                            if (headerText.includes('skill')) sections.skills = content;
                        }
                    });
                    
                    return sections;
                }
            ''')
            
            if sections:
                data['about'] = sections.get('about', data.get('about', ''))
                
                if sections.get('experience'):
                    exp_text = sections['experience']
                    lines = [l.strip() for l in exp_text.split('\\n') if l.strip() and len(l.strip()) > 3]
                    for i in range(0, len(lines)-1, 2):
                        if lines[i] and lines[i+1]:
                            data['experiences'].append({
                                'title': lines[i][:100],
                                'company': lines[i+1][:100]
                            })
                
                if sections.get('education'):
                    edu_text = sections['education']
                    lines = [l.strip() for l in edu_text.split('\\n') if l.strip() and len(l.strip()) > 3]
                    for line in lines[:10]:
                        if len(line) > 3:
                            data['education'].append({'school': line[:200]})
                
                if sections.get('skills'):
                    skills_text = sections['skills']
                    skills = [s.strip() for s in skills_text.split('\\n') if s.strip() and len(s.strip()) > 1 and len(s.strip()) < 50]
                    data['skills'] = skills[:30]
            
            print("Fallback extraction completed")
            
        except Exception as e:
            print(f"Fallback extraction error: {e}")
        
        return data
    
    async def search_and_extract(self, first_name: str, last_name: str,
                                company: str = "", max_profiles: int = 3) -> Dict:
        print(f"\nSearch & Extract: {first_name} {last_name}")
        
        search_results = await self.search_people(first_name, last_name, company, max_profiles * 2)
        
        if not search_results:
            return {
                'success': False,
                'error': f'No profiles found for {first_name} {last_name}',
                'profiles': []
            }
        
        extracted = []
        for i, result in enumerate(search_results[:max_profiles]):
            print(f"\nExtracting profile {i+1}/{min(max_profiles, len(search_results))}")
            profile = await self.extract_profile(result['profile_url'])
            profile['search_rank'] = i + 1
            profile['search_headline'] = result.get('headline', '')
            extracted.append(profile)
            
            if i < max_profiles - 1:
                await self._random_delay(4, 8)
        
        return {
            'success': True,
            'search_query': f"{first_name} {last_name}",
            'total_found': len(search_results),
            'profiles_extracted': len(extracted),
            'profiles': extracted,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_stats(self) -> Dict:
        if self.stats['start_time']:
            self.stats['runtime_seconds'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'is_authenticated': self.is_authenticated,
            'session_name': self.session_name
        }
    
    async def close(self):
        print("Closing browser...")
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Closed")