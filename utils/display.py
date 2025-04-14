import streamlit as st

# Display book in a modern card
def display_book_card(book, index=0, show_buttons=True):
    with st.container():
        st.markdown(f"""
        <div class="book-card">
            <img src="{book['image_url']}" alt="{book['title']}" class="book-img">
            <div class="book-title">{book['title'][:30] + '...' if len(book['title']) > 30 else book['title']}</div>
            <div class="book-author">by {book['authors'][:25] + '...' if len(book['authors']) > 25 else book['authors']}</div>
            <div class="book-rating">{'⭐' * int(book['average_rating'])} {book['average_rating']}</div>
            
            {'<span class="badge badge-new">New</span>' if 'published_date' in book and book['published_date'] == '2023' else ''}
            {'<span class="badge badge-popular">Popular</span>' if 'average_rating' in book and book['average_rating'] >= 4.5 else ''}
        </div>
        """, unsafe_allow_html=True)
        
        if show_buttons:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❤️", key=f"fav_{book['book_id']}_{index}"):
                    if 'favorites' not in st.session_state:
                        st.session_state.favorites = []
                    if book not in st.session_state.favorites:
                        st.session_state.favorites.append(book)
                        st.success("Added to favorites!")
            with col2:
                if st.button("Similar", key=f"sim_{book['book_id']}_{index}"):
                    st.session_state.selected_book_id = book['book_id']
                    st.experimental_rerun()

# Display books in a modern grid
def display_books_grid(books, cols=3):
    if not books:
        st.info("No books found.")
        return
        
    # Create rows
    for i in range(0, len(books), cols):
        cols_list = st.columns(cols)
        row_books = books[i:min(i+cols, len(books))]
        
        for j, book in enumerate(row_books):
            with cols_list[j]:
                display_book_card(book, index=i+j)