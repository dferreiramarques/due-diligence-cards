import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import json
from newsapi import NewsApiClient

# Database Initialization
def init_db():
    conn = sqlite3.connect('company_cards.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS companies
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  linkedin_url TEXT,
                  website_url TEXT,
                  key_personnel TEXT,
                  contact_emails TEXT,
                  contact_form TEXT,
                  upcoming_events TEXT,
                  engagement_suggestions TEXT,
                  news TEXT,
                  crunchbase_profile TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Database Operations
def insert_company(data):
    conn = sqlite3.connect('company_cards.db')
    c = conn.cursor()
    c.execute('''INSERT INTO companies (name, linkedin_url, website_url, key_personnel, contact_emails, contact_form, upcoming_events, engagement_suggestions, news, crunchbase_profile)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['name'], data['linkedin_url'], data['website_url'], json.dumps(data['key_personnel']), json.dumps(data['contact_emails']), data['contact_form'], json.dumps(data['upcoming_events']), json.dumps(data['engagement_suggestions']), json.dumps(data['news']), json.dumps(data['crunchbase_profile'])))
    conn.commit()
    conn.close()

def update_company(id, data):
    conn = sqlite3.connect('company_cards.db')
    c = conn.cursor()
    c.execute('''UPDATE companies SET name=?, linkedin_url=?, website_url=?, key_personnel=?, contact_emails=?, contact_form=?, upcoming_events=?, engagement_suggestions=?, news=?, crunchbase_profile=?
                 WHERE id=?''',
              (data['name'], data['linkedin_url'], data['website_url'], json.dumps(data['key_personnel']), json.dumps(data['contact_emails']), data['contact_form'], json.dumps(data['upcoming_events']), json.dumps(data['engagement_suggestions']), json.dumps(data['news']), json.dumps(data['crunchbase_profile']), id))
    conn.commit()
    conn.close()

def get_company(id):
    conn = sqlite3.connect('company_cards.db')
    c = conn.cursor()
    c.execute('SELECT * FROM companies WHERE id=?', (id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'name': row[1], 'linkedin_url': row[2], 'website_url': row[3],
            'key_personnel': json.loads(row[4]), 'contact_emails': json.loads(row[5]),
            'contact_form': row[6], 'upcoming_events': json.loads(row[7]),
            'engagement_suggestions': json.loads(row[8]), 'news': json.loads(row[9]),
            'crunchbase_profile': json.loads(row[10])
        }
    return None

def get_all_companies():
    conn = sqlite3.connect('company_cards.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM companies')
    rows = c.fetchall()
    conn.close()
    return rows

# Fetch News from High-Confidence Sources
def fetch_news(company_name):
    if 'news_api_key' not in st.session_state or not st.session_state['news_api_key']:
        return []
    newsapi = NewsApiClient(api_key=st.session_state['news_api_key'])
    try:
        response = newsapi.get_everything(q=company_name, language='en', sort_by='relevancy')
        articles = response['articles'][:3]
        return [{'title': article['title'], 'source': article['source']['name'], 'published_at': article['publishedAt']} for article in articles]
    except Exception as e:
        st.error(f"Failed to fetch news: {str(e)}")
        return []

# Fetch Crunchbase Free Profile
def fetch_crunchbase_profile(company_name):
    if 'crunchbase_api_key' not in st.session_state or not st.session_state['crunchbase_api_key']:
        return {}
    try:
        autocomplete_url = f"https://api.crunchbase.com/v3.1/autocompletes?query={company_name}"
        response = requests.get(autocomplete_url)
        data = response.json()
        if 'data' in data and 'items' in data['data'] and data['data']['items']:
            item = data['data']['items'][0]
            if item['type'] == 'Organization':
                uuid = item['identifier']['uuid']
                profile_url = f"https://api.crunchbase.com/v3.1/organizations/{uuid}?user_key={st.session_state['crunchbase_api_key']}"
                response = requests.get(profile_url)
                profile = response.json()
                if 'data' in profile:
                    company_data = profile['data']['properties']
                    return {
                        'description': company_data.get('short_description', 'N/A'),
                        'location': company_data.get('location_identifiers', [{}])[0].get('value', 'N/A'),
                        'funding_rounds': company_data.get('num_funding_rounds', 0),
                        'total_funding': company_data.get('funding_total', {}).get('value_usd', 0)
                    }
        return {}
    except Exception as e:
        st.error(f"Failed to fetch Crunchbase profile: {str(e)}")
        return {}

# Fetch Web Search Results with Caching
@st.cache(ttl=600, allow_output_mutation=True)
def fetch_web_search_results(company_name, api_key, search_engine_id):
    if not api_key or not search_engine_id:
        return []
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={company_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('items', [])
        return results
    except Exception as e:
        st.error(f"Failed to fetch web search results: {str(e)}")
        return []

# Main Application
st.title("Company Due Diligence Tool")
st.write("Profile companies for engagement opportunities with the British-Portuguese Chamber of Commerce.")

# Sidebar Navigation and API Settings
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["New Company", "Saved Companies"])

st.sidebar.title("API Settings")
st.sidebar.write("Enter your API keys below (optional for News and Crunchbase, required for Web Search):")
news_api_key = st.sidebar.text_input("News API Key", type="password", key="news_api_key")
crunchbase_api_key = st.sidebar.text_input("Crunchbase API Key", type="password", key="crunchbase_api_key")
google_api_key = st.sidebar.text_input("Google API Key", type="password", key="google_api_key")
search_engine_id = st.sidebar.text_input("Search Engine ID (cx)", key="search_engine_id")

if page == "New Company":
    with st.form("company_form"):
        company_name = st.text_input("Company Name", placeholder="e.g., Acme Corp")
        linkedin_url = st.text_input("LinkedIn Company Page URL", placeholder="e.g., https://www.linkedin.com/company/acme-corp")
        linkedin_posts = st.text_area("Recent LinkedIn Posts", placeholder="Paste recent posts, one per line.")
        profiles = st.text_area("Key Personnel (name, role, LinkedIn URL)", placeholder="e.g., John Doe, CEO, https://linkedin.com/in/johndoe")
        website_url = st.text_input("Official Website URL", placeholder="e.g., https://www.acme-corp.com")
        submit = st.form_submit_button("Generate Company Card")

    if submit:
        # Parse LinkedIn Posts for Events
        events = []
        for line in linkedin_posts.split('\n'):
            if line.strip() and any(keyword in line.lower() for keyword in ['event', 'webinar', 'conference']):
                date_match = re.search(r'on (\w+ \d{1,2}, \d{4})', line)
                date = date_match.group(1) if date_match else 'Unknown date'
                events.append({'title': line.strip(), 'date': date})

        # Parse Key Personnel
        key_personnel = []
        for profile in profiles.split('\n'):
            if profile.strip():
                parts = [p.strip() for p in profile.split(',')]
                if len(parts) >= 2:
                    name, role = parts[:2]
                    linkedin = parts[2] if len(parts) > 2 else ''
                    key_personnel.append({'name': name, 'role': role, 'linkedin': linkedin})

        # Scrape Website
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(website_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = list(set(re.findall(email_pattern, response.text)))[:3]
            contact_form = soup.find('a', href=re.compile('contact|form', re.I))
            contact_form_url = contact_form['href'] if contact_form else None
            if contact_form_url and not contact_form_url.startswith('http'):
                contact_form_url = website_url.rstrip('/') + '/' + contact_form_url.lstrip('/')
            website_events = []
            for link in soup.find_all('a', href=True):
                if re.search(r'event|webinar|conference', link.text, re.I):
                    website_events.append({'title': link.text.strip(), 'url': link['href']})
        except Exception as e:
            st.error(f"Failed to scrape website: {str(e)}")
            emails = []
            contact_form_url = None
            website_events = []

        # Fetch News and Crunchbase Data
        news = fetch_news(company_name)
        crunchbase_profile = fetch_crunchbase_profile(company_name)

        # Generate Engagement Suggestions
        suggestions = []
        if events or website_events:
            suggestions.append("Attend an upcoming event to network and introduce the Chamber.")
        if emails:
            suggestions.append("Email a contact to introduce the Chamber and discuss benefits.")
        if contact_form_url:
            suggestions.append(f"Use the contact form at {contact_form_url} to reach out.")
        if key_personnel:
            suggestions.append("Connect with key personnel on LinkedIn about UK-Portugal relations.")
        if not suggestions:
            suggestions.append("Research further for engagement opportunities.")

        # Create Company Card
        company_card = {
            'name': company_name,
            'linkedin_url': linkedin_url,
            'website_url': website_url,
            'key_personnel': key_personnel,
            'contact_emails': emails,
            'contact_form': contact_form_url,
            'upcoming_events': events + website_events,
            'engagement_suggestions': suggestions,
            'news': news,
            'crunchbase_profile': crunchbase_profile
        }
        st.session_state['current_card'] = company_card
        st.session_state['edit_mode'] = False

    if 'current_card' in st.session_state:
        display_company_card(st.session_state['current_card'])

elif page == "Saved Companies":
    companies = get_all_companies()
    company_names = [company[1] for company in companies]
    selected_company = st.selectbox("Select a Company", company_names)
    if selected_company:
        company_id = [company[0] for company in companies if company[1] == selected_company][0]
        company_card = get_company(company_id)
        st.session_state['current_card'] = company_card
        display_company_card(company_card)

# Display and Edit Company Card
def display_company_card(card):
    st.header("Company Card")
    if st.button("Toggle Edit"):
        st.session_state['edit_mode'] = not st.session_state['edit_mode']

    if st.session_state.get('edit_mode', False):
        # Edit Mode
        edited_card = {
            'name': st.text_input("Company Name", value=card['name']),
            'linkedin_url': st.text_input("LinkedIn URL", value=card['linkedin_url']),
            'website_url': st.text_input("Website URL", value=card['website_url']),
            'key_personnel': card['key_personnel'],
            'contact_emails': card['contact_emails'],
            'contact_form': card['contact_form'],
            'upcoming_events': card['upcoming_events'],
            'engagement_suggestions': card['engagement_suggestions'],
            'news': card['news'],
            'crunchbase_profile': card['crunchbase_profile']
        }
        if st.button("Save"):
            st.session_state['current_card'] = edited_card
            st.session_state['edit_mode'] = False
            if 'id' in card:
                update_company(card['id'], edited_card)
            else:
                insert_company(edited_card)
            st.success("Changes saved!")
    else:
        # View Mode
        st.write(f"**Name:** {card['name']}")
        st.write(f"**LinkedIn:** [{card['linkedin_url']}]({card['linkedin_url']})")
        st.write(f"**Website:** [{card['website_url']}]({card['website_url']})")

        st.subheader("Key Personnel")
        for person in card['key_personnel']:
            st.write(f"- {person['name']}, {person['role']}, [LinkedIn]({person['linkedin']})")

        st.subheader("Contact Information")
        if card['contact_emails']:
            st.write(f"**Emails:** {', '.join(card['contact_emails'])}")
        if card['contact_form']:
            st.write(f"**Contact Form:** [{card['contact_form']}]({card['contact_form']})")

        st.subheader("Upcoming Events")
        for event in card['upcoming_events']:
            st.write(f"- {event['title']} ({event.get('date', 'N/A')})")

        st.subheader("Engagement Suggestions")
        for suggestion in card['engagement_suggestions']:
            st.write(f"- {suggestion}")

        st.subheader("Latest News (High-Confidence Sources)")
        if card['news']:
            for article in card['news']:
                st.write(f"- {article['title']} ({article['source']}, {article['published_at']})")
        else:
            st.write("No news available. Enter News API Key in the sidebar to fetch news.")

        st.subheader("Crunchbase Profile")
        if card['crunchbase_profile']:
            profile = card['crunchbase_profile']
            st.write(f"**Description:** {profile.get('description', 'N/A')}")
            st.write(f"**Location:** {profile.get('location', 'N/A')}")
            st.write(f"**Funding Rounds:** {profile.get('funding_rounds', 0)}")
            st.write(f"**Total Funding:** ${profile.get('total_funding', 0):,}")
        else:
            st.write("No Crunchbase profile available. Enter Crunchbase API Key in the sidebar to fetch profile.")

        # New Web Search Results Section
        st.subheader("Relevant Web Search Results")
        if 'google_api_key' in st.session_state and 'search_engine_id' in st.session_state and st.session_state['google_api_key'] and st.session_state['search_engine_id']:
            search_results = fetch_web_search_results(card['name'], st.session_state['google_api_key'], st.session_state['search_engine_id'])
            if search_results:
                for result in search_results[:3]:
                    st.write(f"- [{result['title']}]({result['link']})")
            else:
                st.write("No recent information found.")
        else:
            st.write("Please enter Google API Key and Search Engine ID in the sidebar to see web search results.")

        if st.button("Refresh News"):
            if 'news_api_key' in st.session_state and st.session_state['news_api_key']:
                news = fetch_news(card['name'])
                card['news'] = news
                st.session_state['current_card'] = card
                st.rerun()
            else:
                st.warning("Please enter News API Key in the sidebar to refresh news.")

        if st.button("Save to Database") and 'id' not in card:
            insert_company(card)
            st.success("Card saved to database!")