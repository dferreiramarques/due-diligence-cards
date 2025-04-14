import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# Set up the app title and description
st.title("Company Due Diligence Tool")
st.write("""
This tool helps you profile companies for engagement opportunities with the British-Portuguese Chamber of Commerce.
Please input the required information below.
""")

# Create a form for user inputs
with st.form("company_form"):
    company_name = st.text_input("Company Name", placeholder="e.g., Acme Corp")
    linkedin_url = st.text_input("LinkedIn Company Page URL", placeholder="e.g., https://www.linkedin.com/company/acme-corp")
    linkedin_posts = st.text_area("Recent LinkedIn Posts (copy-paste text)", placeholder="Paste the text of recent posts here, one per line.")
    profiles = st.text_area("Key Personnel (name, role, LinkedIn URL, separated by commas)", placeholder="e.g., John Doe, CEO, https://linkedin.com/in/johndoe\nJane Smith, Marketing Director, https://linkedin.com/in/janesmith")
    website_url = st.text_input("Official Website URL", placeholder="e.g., https://www.acme-corp.com")
    submit = st.form_submit_button("Generate Company Card")

# Process the inputs when the form is submitted
if submit:
    # Parse LinkedIn posts for events
    events = []
    for line in linkedin_posts.split('\n'):
        if line.strip():
            if any(keyword in line.lower() for keyword in ['event', 'webinar', 'conference']):
                date_match = re.search(r'on (\w+ \d{1,2}, \d{4})', line)
                date = date_match.group(1) if date_match else 'Unknown date'
                events.append({'title': line.strip(), 'date': date})

    # Parse key personnel profiles
    key_personnel = []
    for profile in profiles.split('\n'):
        if profile.strip():
            parts = [p.strip() for p in profile.split(',')]
            if len(parts) >= 2:
                name, role = parts[:2]
                linkedin = parts[2] if len(parts) > 2 else ''
                key_personnel.append({'name': name, 'role': role, 'linkedin': linkedin})

    # Scrape the company website
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(website_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = list(set(re.findall(email_pattern, response.text)))[:3]  # Limit to 3 unique emails

        # Look for a contact form link
        contact_form = soup.find('a', href=re.compile('contact|form', re.I))
        contact_form_url = contact_form['href'] if contact_form else None
        if contact_form_url and not contact_form_url.startswith('http'):
            contact_form_url = website_url.rstrip('/') + '/' + contact_form_url.lstrip('/')

        # Look for events on the website
        website_events = []
        for link in soup.find_all('a', href=True):
            if re.search(r'event|webinar|conference', link.text, re.I):
                website_events.append({'title': link.text.strip(), 'url': link['href']})
    except Exception as e:
        st.error(f"Failed to scrape website: {str(e)}")
        emails = []
        contact_form_url = None
        website_events = []

    # Generate engagement suggestions
    suggestions = []
    if events or website_events:
        suggestions.append("Consider attending an upcoming event to network and introduce the British-Portuguese Chamber of Commerce.")
    if emails:
        suggestions.append("Send a polite email to one of the contact emails, introducing the chamber and offering to discuss potential benefits of association.")
    if contact_form_url:
        suggestions.append(f"Use the contact form at {contact_form_url} to send a brief message about the chamber.")
    if key_personnel:
        suggestions.append("Connect with key personnel on LinkedIn and engage with their posts, mentioning the chamber's role in fostering UK-Portugal business relations.")
    if not suggestions:
        suggestions.append("Research further to find appropriate engagement opportunities.")

    # Build the company card
    company_card = {
        'company': {
            'name': company_name,
            'linkedin': linkedin_url,
            'website': website_url
        },
        'key_personnel': key_personnel,
        'contact_information': {
            'emails': emails,
            'contact_form': contact_form_url
        },
        'upcoming_events': events + website_events,
        'engagement_suggestions': suggestions
    }

    # Display the company card
    st.header("Company Overview")
    st.write(f"**Name:** {company_card['company']['name']}")
    st.write(f"**LinkedIn:** [{company_card['company']['linkedin']}]({company_card['company']['linkedin']})")
    st.write(f"**Website:** [{company_card['company']['website']}]({company_card['company']['website']})")

    st.header("Key Personnel")
    if key_personnel:
        for person in key_personnel:
            st.write(f"- {person['name']}, {person['role']}, [LinkedIn]({person['linkedin']})")
    else:
        st.write("No key personnel provided.")

    st.header("Contact Information")
    if emails:
        st.write(f"**Emails:** {', '.join(emails)}")
    else:
        st.write("No contact emails found.")
    if contact_form_url:
        st.write(f"**Contact Form:** [{contact_form_url}]({contact_form_url})")
    else:
        st.write("No contact form found.")

    st.header("Upcoming Events")
    if company_card['upcoming_events']:
        for event in company_card['upcoming_events']:
            title = event['title']
            date = event.get('date', 'N/A')
            url = event.get('url', '')
            if url:
                st.write(f"- [{title}]({url}) ({date})")
            else:
                st.write(f"- {title} ({date})")
    else:
        st.write("No upcoming events found.")

    st.header("Engagement Suggestions")
    for suggestion in company_card['engagement_suggestions']:
        st.write(f"- {suggestion}")