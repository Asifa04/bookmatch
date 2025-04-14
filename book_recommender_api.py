import pandas as pd
import numpy as np
from surprise import SVD, Dataset, Reader, accuracy
from surprise.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# -------------------- Data Loading and Preprocessing --------------------

def load_and_preprocess_data():
    """
    Load and preprocess the book dataset
    Using books.csv, ratings.csv, and users.csv
    """
    # Load datasets
    books_df = pd.read_csv('books.csv', sep=';')
    ratings_df = pd.read_csv('ratings.csv')
    users_df = pd.read_csv('users.csv')

    # Rename columns to match expected format
    books_df = books_df.rename(columns={
        "ISBN": "book_id",
        "Book-Title": "title",
        "Book-Author": "authors",
        "Year-Of-Publication": "published_date",
        "Image-URL-M": "image_url"
    })

    # Fill missing values and create content column
    books_df.fillna({
        'title': 'Unknown Title',
        'authors': 'Unknown Author',
        'published_date': 'N/A',
        'image_url': 'https://via.placeholder.com/150x225'
    }, inplace=True)

    books_df['content'] = books_df['title'] + ' ' + books_df['authors']

    return books_df, ratings_df, users_df

# -------------------- Content-Based Filtering --------------------

class ContentBasedRecommender:
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000
        )
        self.book_content_matrix = None
        self.books_df = None
        self.book_indices = None

    def fit(self, books_df):
        self.books_df = books_df
        self.book_content_matrix = self.tfidf_vectorizer.fit_transform(books_df['content'])
        self.book_indices = pd.Series(books_df.index, index=books_df['book_id']).drop_duplicates()

    def recommend(self, book_id, top_n=10):
        idx = self.book_indices[book_id]
        sim_scores = cosine_similarity(
            self.book_content_matrix[idx].reshape(1, -1),
            self.book_content_matrix
        ).flatten()
        sim_scores_indices = sim_scores.argsort()[::-1]
        sim_scores_indices = sim_scores_indices[sim_scores_indices != idx][:top_n]
        return self.books_df.iloc[sim_scores_indices]

# -------------------- Collaborative Filtering --------------------

class CollaborativeRecommender:
    def __init__(self):
        self.model = SVD(n_factors=100, n_epochs=20, random_state=42)
        self.reader = Reader(rating_scale=(1, 5))
        self.data = None
        self.book_mapping = None
        self.books_df = None

    def fit(self, ratings_df, books_df):
        self.books_df = books_df
        self.book_mapping = {idx: book_id for idx, book_id in enumerate(books_df['book_id'].unique())}
        self.data = Dataset.load_from_df(
            ratings_df[['user_id', 'book_id', 'rating']],
            self.reader
        )
        trainset, _ = train_test_split(self.data, test_size=0.2)
        self.model.fit(trainset)

    def recommend_for_user(self, user_id, rated_books, top_n=10):
        all_books = self.books_df['book_id'].unique()
        books_to_recommend = [book_id for book_id in all_books if book_id not in rated_books]
        predictions = [
            (book_id, self.model.predict(user_id, book_id).est)
            for book_id in books_to_recommend
        ]
        predictions.sort(key=lambda x: x[1], reverse=True)
        top_recommendations = [book_id for book_id, _ in predictions[:top_n]]
        return self.books_df[self.books_df['book_id'].isin(top_recommendations)]

# -------------------- Hybrid Recommender --------------------

class HybridRecommender:
    def __init__(self, content_weight=0.3, collaborative_weight=0.7):
        self.content_recommender = ContentBasedRecommender()
        self.collaborative_recommender = CollaborativeRecommender()
        self.content_weight = content_weight
        self.collaborative_weight = collaborative_weight
        self.books_df = None

    def fit(self, books_df, ratings_df):
        self.books_df = books_df
        self.content_recommender.fit(books_df)
        self.collaborative_recommender.fit(ratings_df, books_df)

    def recommend(self, user_id, book_id, rated_books, top_n=10):
        content_recs = self.content_recommender.recommend(book_id, top_n=top_n*2)
        collab_recs = self.collaborative_recommender.recommend_for_user(user_id, rated_books, top_n=top_n*2)
        content_scores = {row['book_id']: self.content_weight * (1 - i/len(content_recs))
                          for i, (_, row) in enumerate(content_recs.iterrows())}
        collab_scores = {row['book_id']: self.collaborative_weight * (1 - i/len(collab_recs))
                         for i, (_, row) in enumerate(collab_recs.iterrows())}
        all_recommended_books = set(content_scores.keys()) | set(collab_scores.keys())
        combined_scores = {
            book_id: content_scores.get(book_id, 0) + collab_scores.get(book_id, 0)
            for book_id in all_recommended_books
        }
        sorted_books = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        recommended_book_ids = [book_id for book_id, _ in sorted_books]
        return self.books_df[self.books_df['book_id'].isin(recommended_book_ids)]

# -------------------- FastAPI Implementation --------------------

app = FastAPI(title="Book Recommendation API", description="API for recommending books to users")

class BookRecommendationRequest(BaseModel):
    user_id: int
    book_id: Optional[str] = None
    num_recommendations: int = 10

class BookResponse(BaseModel):
    book_id: str
    title: str
    authors: str
    average_rating: Optional[float] = 0.0
    image_url: str

class RecommendationResponse(BaseModel):
    recommendations: List[BookResponse]

books_df = None
ratings_df = None
users_df = None
hybrid_recommender = None

@app.on_event("startup")
async def startup_event():
    global books_df, ratings_df, users_df, hybrid_recommender
    books_df, ratings_df, users_df = load_and_preprocess_data()
    hybrid_recommender = HybridRecommender()
    hybrid_recommender.fit(books_df, ratings_df)
    print("Models loaded and ready for recommendations!")

@app.get("/recommendations/", response_model=RecommendationResponse)
async def get_recommendations(user_id: int, book_id: Optional[str] = None, num_recommendations: int = 10):
    try:
        user_ratings = ratings_df[ratings_df['user_id'] == user_id]
        rated_books = user_ratings['book_id'].tolist()
        if book_id is None and rated_books:
            highest_rated = user_ratings.sort_values('rating', ascending=False).iloc[0]
            book_id = highest_rated['book_id']
        elif book_id is None:
            raise HTTPException(status_code=400, detail="No book_id provided and user has no ratings")
        recommendations = hybrid_recommender.recommend(
            user_id, book_id, rated_books, top_n=num_recommendations
        )
        result = recommendations[['book_id', 'title', 'authors', 'image_url']].copy()
        result['average_rating'] = 0.0  # Placeholder if not in your CSV
        return {"recommendations": result.to_dict('records')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@app.get("/books/search/")
async def search_books(query: str = Query(..., min_length=3)):
    try:
        results = books_df[
            books_df['title'].str.contains(query, case=False) | 
            books_df['authors'].str.contains(query, case=False)
        ]
        results['average_rating'] = 0.0  # Placeholder
        return {"results": results[['book_id', 'title', 'authors', 'average_rating', 'image_url']].to_dict('records')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching books: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("book_recommender_api:app", host="0.0.0.0", port=8000, reload=True)
