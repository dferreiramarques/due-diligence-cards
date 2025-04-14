import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

# Fetch Web Search Results with Caching
@st.cache_data(ttl=600)
def fetch_web_search_results(company_name, api_key, search_engine_id):
    if not api_key or not search_engine_id:
        return []
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={company_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('items', [])
    except Exception as e:
        st.error(f"Failed to fetch web search results: {str(e)}")
        return []

# Display and Edit Company Card
def display_company_card(card):
    st.header("Company Card")
    if st.button("Toggle Edit"):
        st.session_state['edit_mode'] = not st.session_state.get('edit_mode', False)

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
        # Add more display logic as needed...

        st.subheader("Relevant Web Search Results")
        if 'google_api_key' in st.session_state and 'search_engine_id' in st.session_state:
            search_results = fetch_web_search_results(card['name'], st.session_state['google_api_key'], st.session_state['search_engine_id'])
            if search_results:
                for result in search_results[:3]:
                    st.write(f"- [{result['title']}]({result['link']})")
            else:
                st.write("No recent information found.")
        else:
            st.write("Please enter Google API Key and Search Engine ID in the sidebar.")

        if st.button("Save to Database") and 'id' not in card:
            insert_company(card)
            st.success("Card saved to database!")

# Main Application
st.title("Company Due Diligence Tool")
st.write("Profile companies for engagement opportunities.")

# Sidebar for API Keys
st.sidebar.title("API Settings")
google_api_key = st.sidebar.text_input("Google API Key", type="password", key="google_api_key")
search_engine_id = st.sidebar.text_input("Search Engine ID (cx)", key="search_engine_id")

# Page Logic
page = st.sidebar.radio("Go to", ["New Company", "Saved Companies"])

if page == "New Company":
    with st.form("company_form"):
        company_name = st.text_input("Company Name")
        linkedin_url = st.text_input("LinkedIn URL")
        website_url = st.text_input("Website URL")
        submit = st.form_submit_button("Generate Company Card")

    if submit:
        company_card = {
            'name': company_name,
            'linkedin_url': linkedin_url,
            'website_url': website_url,
            'key_personnel': [],
            'contact_emails': [],
            'contact_form': None,
            'upcoming_events': [],
            'engagement_suggestions': [],
            'news': [],
            'crunchbase_profile': None
        }
        st.session_state['current_card'] = company_card
        st.session_state['edit_mode'] = False

    if 'current_card' in st.session_state:
        display_company_card(st.session_state['current_card'])

elif page == "Saved Companies":
    companies = get_all_companies()  # Assuming this function exists
    company_names = [company[1] for company in companies]
    selected_company = st.selectbox("Select a Company", company_names)
    if selected_company:
        company_id = [company[0] for company in companies if company[1] == selected_company][0]
        company_card = get_company(company_id)  # Assuming this function exists
        st.session_state['current_card'] = company_card
        display_company_card(company_card)