import streamlit as st
import re
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables if any
load_dotenv()

def detect_api_service(api_key):
    if not api_key:
        return "No API key provided"
    
    # Check for OpenAI API key pattern (sk-...)
    if api_key.startswith("sk-"):
        return "OpenAI"
    
    # Check for Google/Gemini API key pattern
    if re.match(r'^AIza[0-9A-Za-z_-]{35}$', api_key):
        return "Google/Gemini"
    
    # Check for Anthropic/Claude API key pattern
    if api_key.startswith("sk-ant-"):
        return "Anthropic/Claude"
    
    # If no pattern matches, try to validate with OpenAI as default
    try:
        # Basic test request to OpenAI
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        if response.status_code == 200:
            return "OpenAI"
    except:
        pass
    
    # If we get here, we couldn't determine the API service
    return "Unknown API service"

def format_event_info(name, desc, date, location):
    event_info = f"Event Name: {name}\n"
    event_info += f"Description: {desc}\n"
    if date:
        event_info += f"Date: {date}\n"
    if location:
        event_info += f"Location: {location}\n"
    return event_info

def create_prompt(platform, event_info, tone):
    char_limit = 1000  # Default
    if platform == "Twitter":
        char_limit = 280
    
    prompt = f"Create a {tone.lower()} {platform} post about the following event:\n\n"
    prompt += event_info + "\n"
    
    if platform == "LinkedIn":
        prompt += "The post should be professional, informative, and include relevant hashtags. It should be suitable for a business audience."
    elif platform == "Twitter":
        prompt += f"The post should be concise (under {char_limit} characters), engaging, and include relevant hashtags."
    elif platform == "WhatsApp":
        prompt += "The post should be conversational, informative, and use emojis where appropriate. It should feel personal and friendly."
    
    prompt += f"\nThe tone should be {tone.lower()}."
    
    # Add specific tone instructions
    if tone == "Sarcastic":
        prompt += " Use witty sarcasm and humor while still conveying the important information."
    elif tone == "Professional":
        prompt += " Use formal language and focus on the business value of the event."
    elif tone == "Enthusiastic":
        prompt += " Show high energy and excitement about the event."
    elif tone == "Humorous":
        prompt += " Include appropriate jokes or wordplay while still being informative."
    
    return prompt

def generate_with_openai(api_key, name, desc, date, location, tone):
    event_info = format_event_info(name, desc, date, location)
    results = {}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    with st.spinner("Generating posts with OpenAI..."):
        for platform in ["LinkedIn", "Twitter", "WhatsApp"]:
            prompt = create_prompt(platform, event_info, tone)
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            try:
                response = requests.post("https://api.openai.com/v1/chat/completions", 
                                        headers=headers, 
                                        json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"].strip()
                    results[platform] = content
                else:
                    results[platform] = f"Error with OpenAI API: {response.text}"
            except Exception as e:
                results[platform] = f"Error: {str(e)}"
    
    return results

def generate_with_gemini(api_key, name, desc, date, location, tone):
    event_info = format_event_info(name, desc, date, location)
    results = {}
    
    headers = {
        "Content-Type": "application/json"
    }
    
    with st.spinner("Generating posts with Google/Gemini..."):
        for platform in ["LinkedIn", "Twitter", "WhatsApp"]:
            prompt = create_prompt(platform, event_info, tone)
            
            # Updated Gemini API endpoint
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    try:
                        # Updated response parsing for Gemini
                        content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                        results[platform] = content
                    except (KeyError, IndexError) as e:
                        results[platform] = f"Error parsing Gemini API response: {str(e)}"
                else:
                    # Add detailed error information
                    error_msg = response.text if response.text else "Unknown error"
                    results[platform] = f"Error with Gemini API: {error_msg}"
                    st.error(f"Gemini API Error ({response.status_code}): {error_msg}")
            except Exception as e:
                results[platform] = f"Error: {str(e)}"
    
    return results

def generate_with_anthropic(api_key, name, desc, date, location, tone):
    event_info = format_event_info(name, desc, date, location)
    results = {}
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    with st.spinner("Generating posts with Anthropic/Claude..."):
        for platform in ["LinkedIn", "Twitter", "WhatsApp"]:
            prompt = create_prompt(platform, event_info, tone)
            
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            try:
                response = requests.post("https://api.anthropic.com/v1/messages", 
                                        headers=headers, 
                                        json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"].strip()
                    results[platform] = content
                else:
                    results[platform] = f"Error with Anthropic API: {response.text}"
            except Exception as e:
                results[platform] = f"Error: {str(e)}"
    
    return results

def generate_mock_posts(name, desc, date, location, tone):
    event_info = format_event_info(name, desc, date, location)
    results = {}
    
    with st.spinner("Generating sample posts..."):
        # LinkedIn post (more professional/formal)
        linkedin_post = f"I'm excited to announce {name}!\n\n"
        linkedin_post += f"{desc}\n\n"
        if date:
            linkedin_post += f"📅 When: {date}\n"
        if location:
            linkedin_post += f"📍 Where: {location}\n"
        linkedin_post += "\nLooking forward to connecting with industry professionals at this event. #ProfessionalDevelopment #Networking"
        
        # Twitter post (shorter, more casual)
        twitter_post = f"Join us for {name}! "
        twitter_post += f"{desc[:80]}..." if len(desc) > 100 else desc
        twitter_post += f" {date} at {location}" if date and location else ""
        twitter_post += " #excited #event"
        
        # WhatsApp post (more personal/informative)
        whatsapp_post = f"Hey everyone! 👋\n\nJust wanted to let you know about {name}.\n\n"
        whatsapp_post += f"{desc}\n\n"
        if date:
            whatsapp_post += f"📅 Date: {date}\n"
        if location:
            whatsapp_post += f"📍 Location: {location}\n"
        whatsapp_post += "\nHope to see you there! Feel free to share with others who might be interested. 😊"
        
        # Apply tone modifications based on tone selection
        if tone == "Sarcastic":
            linkedin_post = f"Oh great, another event to add to your calendar: {name}. 🙄\n\n"
            linkedin_post += f"{desc}\n\n"
            if date and location:
                linkedin_post += f"If you really have nothing better to do on {date} at {location}, I guess you could show up.\n\n"
            linkedin_post += "Can't wait to pretend to be interested in small talk. #NetworkingJoy #ProfessionalSmiling"
            
            twitter_post = f"Wow, {name}! Because what we all needed was ANOTHER event to attend. 🙄 "
            twitter_post += f"{date} at {location}" if date and location else ""
            twitter_post += " #blessed #sarcasm"
            
            whatsapp_post = f"Attention everyone! 📢\n\nApparently we're supposed to be excited about {name}.\n\n"
            whatsapp_post += f"{desc}\n\n"
            if date and location:
                whatsapp_post += f"Mark your calendars (or don't) for {date} at {location}.\n\n"
            whatsapp_post += "Feel free to come up with creative excuses not to attend. 😂"
        
        elif tone == "Enthusiastic":
            linkedin_post = f"🎉 INCREDIBLY EXCITED to announce {name}!! 🎉\n\n"
            linkedin_post += f"{desc}\n\n"
            if date and location:
                linkedin_post += f"📅 MARK YOUR CALENDARS: {date}\n📍 BE THERE: {location}\n\n"
            linkedin_post += "This is going to be ABSOLUTELY AMAZING!! Can't WAIT to see everyone there!!! #Excited #BestEventEver"
            
            twitter_post = f"OMG! You DO NOT want to miss {name}!! It's going to be INCREDIBLE! "
            twitter_post += f"{date} at {location}" if date and location else ""
            twitter_post += " #CantWait #SoExcited"
            
            whatsapp_post = f"HEY EVERYONE!!! 🔥🔥🔥\n\nDROP EVERYTHING YOU'RE DOING! {name} is happening and it's going to be EPIC!!!\n\n"
            whatsapp_post += f"{desc}\n\n"
            if date and location:
                whatsapp_post += f"📅 When: {date} (SET THOSE ALARMS!)\n📍 Where: {location} (GET THERE EARLY!)\n\n"
            whatsapp_post += "I AM SOOOO EXCITED!!! 🎉🎉🎉 PLEASE COME!!! SHARE WITH EVERYONE!!!"
        
        results["LinkedIn"] = linkedin_post
        results["Twitter"] = twitter_post
        results["WhatsApp"] = whatsapp_post
    
    return results

def main():
    st.set_page_config(
        page_title="Social Media Post Generator",
        page_icon="📱",
        layout="wide",
    )
    
    st.title("Social Media Post Generator 📱")
    st.markdown("Generate professional posts for LinkedIn, Twitter, and WhatsApp from your event details.")
    
    # Create a sidebar for API configuration
    st.sidebar.header("API Configuration")
    
    api_key = st.sidebar.text_input("Enter your API Key", type="password")
    show_key = st.sidebar.checkbox("Show API Key")
    
    if show_key:
        st.sidebar.code(api_key)
    
    if api_key:
        service = detect_api_service(api_key)
        st.sidebar.success(f"Detected API Service: {service}")
    else:
        st.sidebar.info("Enter an API key to detect the service")
        service = "Not Detected"
    
    # Add a manual service selection option
    selected_service = st.sidebar.radio(
        "Or select service manually:",
        ["Auto-detect", "OpenAI", "Google/Gemini", "Anthropic/Claude", "Use Mock Generator (No API)"],
        index=0
    )
    
    if selected_service != "Auto-detect":
        if selected_service == "Use Mock Generator (No API)":
            service = "Mock"
        else:
            service = selected_service
            st.sidebar.info(f"Manually selected: {service}")
    
    # Main content area for event details
    st.header("Event Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        event_name = st.text_input("Event Name", placeholder="Tech Conference 2025")
        event_date = st.text_input("Event Date", placeholder="March 25-27, 2025")
    
    with col2:
        event_location = st.text_input("Event Location", placeholder="San Francisco Convention Center")
        tone = st.selectbox(
            "Post Tone",
            ["Professional", "Casual", "Enthusiastic", "Sarcastic", "Formal", "Humorous"]
        )
    
    event_desc = st.text_area(
        "Event Description",
        placeholder="Describe your event here...",
        height=150
    )
    
    # Add a "View Example"  expander
    with st.expander("View Example"):
        st.markdown("""
        ### Example Event Details
        
        **Name**: AI Developer Conference 2025
        
        **Description**: Join us for three days of cutting-edge AI workshops, keynote presentations from industry leaders, and networking opportunities with the best minds in artificial intelligence. This event features hands-on labs, technical deep dives, and the latest in generative AI, machine learning, and neural networks.
        
        **Date**: April 15-17, 2025
        
        **Location**: Silicon Valley Convention Center, Mountain View
        
        **Tone Options**: Try different tones to see how they change your posts!
        """)
    
    generate_button = st.button("Generate Posts", type="primary", use_container_width=True)
    
    # Initialize session state for storing generated posts
    if 'posts' not in st.session_state:
        st.session_state.posts = {"LinkedIn": "", "Twitter": "", "WhatsApp": ""}
    
    # Add debug information expandable section
    debug_expander = st.sidebar.expander("Debug Information")
    with debug_expander:
        st.write("This section helps troubleshoot API issues.")
        show_debug_info = st.checkbox("Show API Request/Response")
    
    if generate_button:
        if not event_name or not event_desc:
            st.error("Event name and description are required!")
        else:
            if service == "OpenAI":
                st.session_state.posts = generate_with_openai(api_key, event_name, event_desc, event_date, event_location, tone)
            elif service == "Google/Gemini":
                # Add a note about the Gemini API version
                st.info("Using Gemini API. If you encounter errors, verify your API key and check that you have access to the Gemini Pro model.")
                st.session_state.posts = generate_with_gemini(api_key, event_name, event_desc, event_date, event_location, tone)
            elif service == "Anthropic/Claude":
                st.session_state.posts = generate_with_anthropic(api_key, event_name, event_desc, event_date, event_location, tone)
            else:
                # Use mock generation if API service is unknown or not provided
                st.session_state.posts = generate_mock_posts(event_name, event_desc, event_date, event_location, tone)
            
            st.toast("Posts generated successfully!")
    
    # Display results in tabs
    if any(st.session_state.posts.values()):
        st.header("Generated Posts")
        tab1, tab2, tab3 = st.tabs(["LinkedIn", "Twitter", "WhatsApp"])
        
        with tab1:
            linkedin_post = st.session_state.posts.get("LinkedIn", "")
            st.text_area("LinkedIn Post", value=linkedin_post, height=250)
            if linkedin_post:
                st.markdown(f"Character count: {len(linkedin_post)}")
                if st.button("Copy LinkedIn", use_container_width=True):
                    st.toast("LinkedIn post copied to clipboard!")
        
        with tab2:
            twitter_post = st.session_state.posts.get("Twitter", "")
            st.text_area("Twitter Post", value=twitter_post, height=150)
            if twitter_post:
                char_count = len(twitter_post)
                st.markdown(f"Character count: {char_count}")
                if char_count > 280:
                    st.warning(f"This post exceeds Twitter's 280 character limit by {char_count - 280} characters.")
                if st.button("Copy Twitter", use_container_width=True):
                    st.toast("Twitter post copied to clipboard!")
        
        with tab3:
            whatsapp_post = st.session_state.posts.get("WhatsApp", "")
            st.text_area("WhatsApp Post", value=whatsapp_post, height=250)
            if whatsapp_post:
                st.markdown(f"Character count: {len(whatsapp_post)}")
                if st.button("Copy WhatsApp", use_container_width=True):
                    st.toast("WhatsApp post copied to clipboard!")
    
    # Footer
    st.divider()
    st.caption("This app uses AI to generate social media posts for your events. It detects whether you're using OpenAI, Google/Gemini, or Anthropic APIs.")

if __name__ == "__main__":
    main()
