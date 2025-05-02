import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from fetch_info import *
import json
from pathlib import Path

# --------------------- DB SETUP ---------------------
conn = sqlite3.connect('resources.db')
c = conn.cursor()

# Create users table
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    email TEXT
)''')

# Create resources table
c.execute('''CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    link TEXT,
    tags TEXT,
    title TEXT,
    description TEXT
)''')

# Create tags table
c.execute('''CREATE TABLE IF NOT EXISTS tags (
    tag TEXT PRIMARY KEY
)''')

# Insert default tags if not present
default_tags = ['#book', '#tutorial', '#machinelearning', '#quantum', '#youtube', '#course']
for tag in default_tags:
    c.execute("INSERT OR IGNORE INTO tags (tag) VALUES (?)", (tag,))
conn.commit()

# ------------------ HELPER FUNCTIONS ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    hashed_pw = hash_password(password)
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pw))
    return c.fetchone()

def register_user(username, password, email=None):
    try:
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", 
                  (username, hash_password(password), email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_all_tags():
    rows = c.execute("SELECT tag FROM tags").fetchall()
    return [row[0] for row in rows]

def search_resources(keyword=None, tags=None):
    """
    Search for resources based on various criteria
    
    Parameters:
    - keyword: Search term for title and description
    - tags: List of tags to filter by
    
    Returns:
    - List of resource tuples matching criteria
    """
    # Base query
    query = "SELECT * FROM resources WHERE 1=1"
    params = []
    
    # Add keyword search for title and description
    if keyword and keyword.strip():
        query += " AND (title LIKE ? OR description LIKE ?)"
        keyword_param = f"%{keyword.strip()}%"
        params.extend([keyword_param, keyword_param])
    
    # Add tag filtering
    if tags and len(tags) > 0:
        # For each tag, we need to check if it's in the tags column
        tag_conditions = []
        for tag in tags:
            tag_conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")
        
        # Connect all tag conditions with OR or AND based on search type
        tag_operator = "OR" if st.session_state.get("tag_search_any", True) else "AND"
        query += f" AND ({' {tag_operator} '.join(tag_conditions)})"
    
    # Execute the query
    c.execute(query, params)
    results = c.fetchall()
    
    return results

# ------------------ LOGIN & REGISTRATION ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login or Register")

    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        email = st.text_input("Email (optional)", key="reg_email")
        
        if st.button("Register"):
            if register_user(reg_username, reg_password, email):
                st.success("User registered! Please log in.")
            else:
                st.error("Username already exists.")

# ------------------ MAIN APP ------------------
if st.session_state.logged_in:
    st.sidebar.title("Resource Manager")
    st.sidebar.markdown("---")
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    
    # Unified resource management interface
    
    
    # ------- ADD RESOURCE SECTION -------
    st.header("Add Resource")
    link = st.text_input("Webpage Link")

    current_tags = get_all_tags()
    # Show tags selector + "Add new tag" button in the same row
    st.text("Select Tags")

    col1, col2 = st.columns([4, 1])
    selected_tags = col1.multiselect("Select Tags", current_tags, label_visibility="collapsed")

    if st.button("Add Resource"):
        if not link:
            st.warning("Please enter a link.")
        else:
            title, description = fetch_title_description(link)
            tag_string = ",".join(selected_tags)
            c.execute("INSERT INTO resources (title, description, link, tags) VALUES (?, ?, ?, ?)",
                    (title, description, link, tag_string))
            conn.commit()
            st.success("Resource added!")
            st.rerun()

    # Button to toggle "Add Tag" section
    if 'show_add_tag' not in st.session_state:
        st.session_state.show_add_tag = False

    if col2.button("➕ Add Tag"):
        st.session_state.show_add_tag = not st.session_state.show_add_tag

    # Conditional "Add Tag" UI
    if st.session_state.show_add_tag:
        with st.expander("Add a New Tag", expanded=True):
            new_tag = st.text_input("Enter new tag (e.g. #ai)", key="new_tag_input")
            if st.button("Add New Tag"):
                if new_tag.strip():
                    try:
                        c.execute("INSERT INTO tags (tag) VALUES (?)", (new_tag.strip(),))
                        conn.commit()
                        st.success(f"Tag '{new_tag}' added!")
                        st.session_state.show_add_tag = False  # close expander
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning("Tag already exists.")
                else:
                    st.warning("Tag cannot be empty.")
    
    st.markdown("---")
    
    # ------- SEARCH AND VIEW RESOURCES SECTION -------
    st.header("Search & View Resources")
    
    # Initialize session state for tag search type if not exists
    if "tag_search_any" not in st.session_state:
        st.session_state.tag_search_any = True
    
    # Create columns for a more compact search interface
    search_col1, search_col2 = st.columns([3, 2])
    
with st.container():
    col1, col2, col3 = st.columns([3, 3, 2])

    with col1:
        keyword = st.text_input("Keyword", placeholder="Search title or description")

    with col2:
        all_tags = get_all_tags()
        search_tags = st.multiselect("Filter by tags", all_tags)

    with col3:
        any_tags = st.radio(
            "Tag match",
            ["Match ANY", "Match ALL"],
            index=0 if st.session_state.tag_search_any else 1
        )
        st.session_state.tag_search_any = (any_tags == "Match ANY")

        
        # Apply filters button
        
    # search_pressed = st.button("Search")
    
    # Get resources to display (filtered or all)
    if  keyword or search_tags:
        results = search_resources(keyword, search_tags)
        st.write(f"Found {len(results)} resources")
    else:
        results = c.execute("SELECT * FROM resources").fetchall()
    
    # Display resources
    if not results:
        st.info("No resources available.")
    else:
        for row in results:
            resource_id, link, tags, title, description = row

            with st.expander(f"🗂️ {title}"):
                st.markdown(f"**Link**: [{link}]({link})")
                st.markdown(f"**Tags**: `{tags}`")
                st.markdown(f"**Description**: {description}")
                if st.button("❌ Delete", key=f"delete_{resource_id}"):
                    c.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
                    conn.commit()
                    st.success(f"Deleted: {title}")
                    st.rerun()

    ################################################# LOGOUT ################################
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.markdown("---")