import streamlit as st
import pandas as pd
import random
from datetime import datetime
from fpdf import FPDF
import time

from utils.api import get_recommendations, search_books, load_sample_data

# Set page configuration
st.set_page_config(
    page_title="BookMatch - AI Book Recommendations",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("static/css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = 12345
if 'favorites' not in st.session_state:
    st.session_state.favorites = []
if 'selected_book_id' not in st.session_state:
    st.session_state.selected_book_id = None
if 'is_first_visit' not in st.session_state:
    st.session_state.is_first_visit = True

# --- Display functions (merged from utils/display.py) ---
def display_book_card(book, key=None):
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 1rem;">
        <h4 style="margin-bottom: 0.5rem;">{book.get('title', 'Untitled')}</h4>
        <p style="margin: 0;">by {book.get('author', 'Unknown')}</p>
        <p style="margin: 0; font-size: 0.9rem; color: #6c757d;">Genre: {book.get('genre', 'N/A')}</p>
        <p style="margin: 0; font-size: 0.9rem; color: #6c757d;">Rating: {book.get('average_rating', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("❤️ Add to Favorites", key=key):
        if book not in st.session_state.favorites:
            st.session_state.favorites.append(book)
            st.success("Added to favorites!")

def display_books_grid(books, cols=3):
    if not books:
        st.write("No books to display.")
        return

    rows = [books[i:i+cols] for i in range(0, len(books), cols)]
    for row in rows:
        cols_row = st.columns(cols)
        for i, book in enumerate(row):
            with cols_row[i]:
                display_book_card(book, key=f"fav_{book['book_id']}_{i}")

# --- PDF generation ---
def generate_pdf(favorites):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(40, 40, 40)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_draw_color(180, 180, 180)

    pdf.cell(200, 10, txt="📚 BookMatch - My Favorite Books", ln=True, align="C")
    pdf.ln(10)

    for book in favorites:
        pdf.set_font("Arial", "B", size=12)
        pdf.cell(0, 10, book.get("title", "Untitled"), ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 8, f"Author: {book.get('author', 'Unknown')}", ln=True)
        pdf.cell(0, 8, f"Genre: {book.get('genre', 'N/A')}", ln=True)
        pdf.cell(0, 8, f"Rating: {book.get('average_rating', 'N/A')}", ln=True)
        pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1')

# --- Main App ---
def main():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="color: #6C63FF; margin-bottom: 0;">📚 BookMatch</h1>
            <p style="color: #6c757d;">Your AI Book Companion</p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("Personalize Your Experience")
        user_id = st.number_input("Your User ID", min_value=1, value=st.session_state.user_id)
        st.session_state.user_id = user_id
        st.write(f"Welcome, Reader #{user_id}!")

        st.subheader("Your Reading Preferences")
        genres = ["Fantasy", "Science Fiction", "Mystery", "Romance", "Historical Fiction", "Biography", "Self-Help", "Poetry"]
        selected_genres = st.multiselect("Favorite Genres", genres)
        reading_pace = st.select_slider("Reading Pace", options=["Casual", "Moderate", "Avid", "Bookworm"])

        st.markdown("---")
        st.subheader("Navigation")
        page = st.radio("", ["📊 Dashboard", "🔍 Discover Books", "❤️ My Favorites"])

        if st.session_state.favorites:
            st.markdown("---")
            st.subheader("Your Stats")
            st.write(f"📚 Books in favorites: {len(st.session_state.favorites)}")
            st.write(f"⭐ Average rating: {sum([book['average_rating'] for book in st.session_state.favorites])/len(st.session_state.favorites):.1f}")

        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #6c757d; font-size: 0.8rem;">
            <p>Made with ❤️ by BookMatch</p>
            <p>© 2025 BookMatch AI</p>
        </div>
        """, unsafe_allow_html=True)

    if page == "📊 Dashboard":
        if st.session_state.is_first_visit:
            st.markdown("""
            <div class="welcome-banner">
                <h1>Welcome to BookMatch!</h1>
                <p>Your personal AI-powered book recommendation engine</p>
            </div>
            """, unsafe_allow_html=True)
            st.session_state.is_first_visit = False

        st.subheader("Today's Book Insights")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Books Analyzed", "237")
        with col2:
            st.metric("Match Accuracy", "95%")
        with col3:
            st.metric("Updated", datetime.now().strftime('%b %d, %Y'))

        st.markdown("### Recommended For You")
        with st.spinner("Finding your perfect next read..."):
            book_id_param = st.session_state.selected_book_id
            recommendations = get_recommendations(st.session_state.user_id, book_id_param)

            if book_id_param:
                st.info("Showing books similar to your selection")
                st.session_state.selected_book_id = None

            display_books_grid(recommendations)

        st.markdown("### Popular This Week")
        popular_books = load_sample_data().sort_values('average_rating', ascending=False).head(6).to_dict('records')
        display_books_grid(popular_books)

        st.markdown("### New Releases")
        sample_books = load_sample_data()
        new_releases = sample_books[sample_books['published_date'] == '2023']
        new_books = new_releases.sample(min(3, len(new_releases))).to_dict('records') if not new_releases.empty else []
        display_books_grid(new_books, cols=3)

    elif page == "🔍 Discover Books":
        st.markdown("## Discover Your Next Favorite Book")
        query = st.text_input("Enter book title, author or keyword", placeholder="e.g., Harry Potter, Stephen King...")
        genres = ["All Genres", "Fantasy", "Science Fiction", "Mystery", "Romance", 
                  "Historical Fiction", "Biography", "Self-Help", "Poetry"]
        search_genre = st.selectbox("Filter by genre", genres)
        search_button = st.button("🔍 Search", type="primary")

        if query or search_button:
            with st.spinner("Searching our library..."):
                time.sleep(0.5)
                search_results = search_books(query)
                if search_genre != "All Genres" and search_results:
                    search_results = [book for book in search_results if book.get('genre', '') == search_genre]
                st.write(f"Found {len(search_results)} results for '{query}'")
                display_books_grid(search_results)
        else:
            st.markdown("### Featured Categories")
            genres = ["Fantasy", "Mystery", "Romance", "Sci-Fi", "Biography", "Self-Help"]
            genre_cols = st.columns(3)
            for i, genre in enumerate(genres):
                with genre_cols[i % 3]:
                    color = ["#6C63FF", "#FF6584", "#38B000", "#FF8A00", "#9C27B0", "#17A2B8"][i % 6]
                    st.markdown(f"""
                    <div style="background-color: {color}; color: white; padding: 2rem; 
                              border-radius: 10px; text-align: center; margin-bottom: 1rem;
                              box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: pointer;">
                        <h3>{genre}</h3>
                        <p>Explore {genre} Books</p>
                    </div>
                    """, unsafe_allow_html=True)

    elif page == "❤️ My Favorites":
        st.markdown("## My Favorite Books")
        if st.session_state.favorites:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Clear All", type="secondary"):
                    st.session_state.favorites = []
                    st.success("Favorites cleared!")
                    st.experimental_rerun()

            display_books_grid(st.session_state.favorites)

            st.markdown("### Export Options")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.download_button(
                    label="📄 Export as PDF",
                    data=generate_pdf(st.session_state.favorites),
                    file_name="bookmatch_favorites.pdf",
                    mime="application/pdf",
                ):
                    st.success("PDF downloaded!")
            with col2:
                st.markdown("📧 Email list (coming soon)")
            with col3:
                st.markdown("🔗 Share link (coming soon)")
        else:
            st.markdown("Your favorites list is empty. Start exploring and adding books!")

if __name__ == "__main__":
    main()
