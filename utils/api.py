import pandas as pd
import requests
import random
import streamlit as st

# Define API URL (change when deploying)
API_URL = "http://0.0.0.0:8000"


# Load sample data for development/demo purposes
@st.cache_data
def load_sample_data():
    try:
        books = pd.read_csv('data/books.csv')
        return books
    except:
        # Create dummy data with diverse book titles and authors if CSV not available
        genres = ["Fantasy", "Sci-Fi", "Romance", "Mystery", "Historical", "Biography", "Self-Help", "Fiction"]
        titles = [
            "The Midnight Library", "Project Hail Mary", "The Invisible Life of Addie LaRue",
            "Klara and the Sun", "The Four Winds", "The Vanishing Half", "Atomic Habits",
            "A Promised Land", "The Song of Achilles", "Where the Crawdads Sing"
        ]
        authors = [
            "Matt Haig", "Andy Weir", "V.E. Schwab", "Kazuo Ishiguro", "Kristin Hannah",
            "Brit Bennett", "James Clear", "Barack Obama", "Madeline Miller", "Delia Owens"
        ]
        
        descriptions = [
            "Between life and death there is a library, and within that library, the shelves go on forever.",
            "A lone astronaut must save the earth from disaster in this incredible new science-based thriller.",
            "A girl who made a deal to live forever but was forgotten by everyone she met.",
            "From the bestselling author comes a thrilling new novel about artificial intelligence.",
            "A powerful American epic about love and heroism and hope, set during the Great Depression.",
            "The Vignes twin sisters will always be identical. But after growing up in a small southern community, their lives diverge.",
            "Tiny Changes, Remarkable Results: An Easy & Proven Way to Build Good Habits & Break Bad Ones.",
            "A riveting, deeply personal account of history in the making—from the president who inspired us to believe in the power of democracy.",
            "A thrilling, profoundly moving, and utterly unique retelling of the legend of Achilles and the Trojan War.",
            "For years, rumors of the 'Marsh Girl' have haunted Barkley Cove, a quiet town on the North Carolina coast."
        ]
        
        books = pd.DataFrame({
            'book_id': range(1, 11),
            'title': titles,
            'authors': authors,
            'average_rating': [round(4.0 + random.uniform(-0.5, 0.5), 1) for _ in range(10)],
            'image_url': [f"/api/placeholder/150/225" for _ in range(10)],
            'description': descriptions,
            'genre': [random.choice(genres) for _ in range(10)],
            'published_date': [f"{2010 + random.randint(0, 13)}" for _ in range(10)]
        })
        return books

# Function to get book recommendations from API
def get_recommendations(user_id, book_id=None, num_recommendations=6):
    try:
        params = {
            "user_id": user_id,
            "num_recommendations": num_recommendations
        }
        if book_id:
            params["book_id"] = book_id
            
        response = requests.get(f"{API_URL}/recommendations/", params=params)
        if response.status_code == 200:
            return response.json()["recommendations"]
        else:
            st.error(f"Error: {response.json()['detail']}")
            return []
    except Exception as e:
        # Return dummy recommendations for demonstration
        books = load_sample_data()
        return books.sample(num_recommendations).to_dict('records')

# Function to search books
def search_books(query):
    try:
        response = requests.get(f"{API_URL}/books/search/", params={"query": query})
        if response.status_code == 200:
            return response.json()["results"]
        else:
            st.error(f"Error: {response.json()['detail']}")
            return []
    except Exception as e:
        # Return filtered sample data for demonstration
        books = load_sample_data()
        return books[books['title'].str.contains(query, case=False) | 
                    books['authors'].str.contains(query, case=False)].to_dict('records')