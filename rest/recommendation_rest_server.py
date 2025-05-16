from flask import Flask, request, jsonify
import redis
import pandas as pd
import json
import jsonpickle
import os

app = Flask(__name__)

# Connect to Redis
redis_host = os.getenv("REDIS_HOST", "redis-server")
genDb = redis.StrictRedis(host=redis_host, db=0, decode_responses=True)
movieDb = redis.StrictRedis(host=redis_host, db=3, decode_responses=True)
userMovieDb = redis.StrictRedis(host=redis_host, db=4, decode_responses=True)
activeUserRatingDb = redis.StrictRedis(host=redis_host, db=2, decode_responses=True)

# TMDB API Key
TMDB_API_KEY = "b2b681d6a769060466aa702ea410b90c"

# Load movies.csv
movies_df = pd.read_csv("dataset/movies.csv")
movies_df[['title', 'year']] = movies_df['title'].str.extract(r'^(.*)\s+\((\d{4})\)$')
movies_df['year'] = movies_df['year'].fillna('N/A')
movies_df['genres'] = movies_df['genres'].fillna('')
movies_df = movies_df[movies_df['genres'] != '(no genres listed)']

# Initialize genres into Redis
def init_genres():
    if not genDb.exists("genres"):
        genres_set = set()
        for g_list in movies_df['genres']:
            genres_set.update(g_list.split('|'))
        genres = sorted(list(genres_set))
        for genre in genres:
            genDb.rpush("genres", genre)
        print(f"[INIT] Loaded genres into Redis: {genres}")
    else:
        print("[INIT] Genres already present in Redis.")

@app.route('/')
def index():
    return "🎬 Movie Recommender REST API is running!"

@app.route('/compute/movies/<user_id>', methods=['POST'])
def compute_movies(user_id):
    try:
        selected_genres = json.loads(request.data)
        filtered_movies = []

        for genre in selected_genres:
            genre_movies = movies_df[movies_df['genres'].str.contains(genre, case=False, na=False)]
            for _, row in genre_movies.iterrows():
                filtered_movies.append([int(row['movieId']), genre])

        unique_movies = []
        seen_ids = set()
        for movie in filtered_movies:
            if movie[0] not in seen_ids:
                seen_ids.add(movie[0])
                unique_movies.append(movie)

        top_movies = unique_movies[:100]
        userMovieDb.set(user_id, json.dumps(top_movies))

        if not movieDb.exists("movie_dict"):
            movie_dict = {}
            for _, row in movies_df.iterrows():
                movie_dict[str(int(row['movieId']))] = [
                    row['title'],
                    "https://picsum.photos/200/300",
                    row['genres'],
                    row['year']
                ]
            movieDb.set("movie_dict", json.dumps(movie_dict))

        return jsonify({"status": "OK"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 🔥 NEW: Recommend movies route
@app.route('/recommend/<user_id>', methods=['GET'])
def recommend_movies(user_id):
    try:
        if not movieDb.exists("movie_dict") or not activeUserRatingDb.exists(user_id):
            return jsonify([])

        movie_dict = json.loads(movieDb.get("movie_dict"))
        rated_movies = json.loads(activeUserRatingDb.get(user_id))

        user_genres = set(genre for _, genre in rated_movies.values())
        recommendations = []

        for movie_id, details in movie_dict.items():
            if movie_id in rated_movies:
                continue
            title, poster_url, genres, year = details
            genre_set = set(genres.split('|'))
            match_score = len(genre_set.intersection(user_genres)) / len(user_genres)
            if match_score > 0:
                recommendations.append({
                    "movie_id": movie_id,
                    "title": title,
                    "poster": poster_url,
                    "genres": genres,
                    "year": year,
                    "match": f"{int(match_score * 100)}%"
                })

        sorted_recommendations = sorted(recommendations, key=lambda x: -int(x['match'].strip('%')))
        return jsonify(sorted_recommendations[:100])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    init_genres()
    app.run(host='0.0.0.0', port=5000)
