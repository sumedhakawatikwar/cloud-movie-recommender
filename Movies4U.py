import streamlit as st
import redis
import jsonpickle
import os
import hashlib
import json
import traceback
import SessionState
import requests

st.set_page_config(layout="wide")

# Background styling
st.markdown("""
<style>
body {
background-image: url("https://oldschoolgrappling.com/wp-content/uploads/2018/08/Background-opera-speeddials-community-web-simple-backgrounds.jpg");
background-size: cover;
}
</style>
""", unsafe_allow_html=True)

# Redis connection
redisHost = os.getenv("REDIS_HOST", "localhost")
restHost = os.getenv("REST", "localhost:5000")
addr = f"http://{restHost}"

genDb = redis.StrictRedis(host=redisHost, db=0, decode_responses=True)
loginDb = redis.StrictRedis(host=redisHost, db=1, decode_responses=True)
activeUserRatingDb = redis.StrictRedis(host=redisHost, db=2, decode_responses=True)
movieDb = redis.StrictRedis(host=redisHost, db=3, decode_responses=True)
userMovieDb = redis.StrictRedis(host=redisHost, db=4, decode_responses=True)
userReccDb = redis.StrictRedis(host=redisHost, db=5, decode_responses=True)

def make_hashes(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

@st.cache_data
def getSessionState():
    return SessionState.get(
        logout=False,
        show_movie_count=0,
        show_reco_count=0,
        rec_dict={},
        options=[],
        api_call=False
    )

def render_movie_list(user_id, start_index, rec_dict):
    cols = st.columns(6)
    ind = 0
    total_movies = 24
    movie_dict = json.loads(movieDb.get("movie_dict"))
    user_movie_list = json.loads(userMovieDb.get(user_id))

    for i in range(total_movies // 6 + 1):
        for j in range(6):
            if start_index + ind >= len(user_movie_list):
                return rec_dict
            movieId = str(user_movie_list[start_index + ind][0])
            genre = user_movie_list[start_index + ind][1]
            movieName = movie_dict[movieId][0]
            movieImg = movie_dict[movieId][1]
            year = movie_dict[movieId][3]

            cols[j].image(movieImg, width=100)
            cols[j].text(movieName[:10] + ".." if len(movieName) > 10 else movieName)
            cols[j].markdown(f"{year}")
            rating = cols[j].slider(f"Rating", 0.0, 5.0, 0.0, step=0.5, key=f"{user_id}-{movieId}")
            if rating > 0.0:
                rec_dict[movieId] = [str(rating), genre]
            ind += 1
    return rec_dict

def main():
    global latest_user_id
    st.title("🎬 Cloud Movie Recommender System")

    menu = ["Home", "Login", "SignUp"]
    choice = st.sidebar.selectbox("Menu", menu)

    session_state = getSessionState()

    if choice == "Home":
        st.subheader("Home")
        st.image("https://i.pinimg.com/originals/af/21/0f/af210fbb1e24644723dbe71312595034.jpg", use_container_width=True)
        session_state.show_movie_count = 0
        session_state.show_reco_count = 0
        session_state.rec_dict = {}
        session_state.options = []
        session_state.api_call = False

    elif choice == "SignUp":
        st.subheader("Create New Account")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')
        if st.button("Signup"):
            if loginDb.exists(new_user):
                st.warning("User already exists.")
            else:
                try:
                    latest_user_id = genDb.get("latest_user_id")
                    if latest_user_id is None:
                        latest_user_id = 0
                        genDb.set("latest_user_id", latest_user_id)
                    latest_user_id = int(latest_user_id) + 1
                    loginDb.rpush(new_user, make_hashes(new_password), str(latest_user_id))
                    genDb.set("latest_user_id", latest_user_id)
                    genDb.set(str(latest_user_id), jsonpickle.dumps({}))
                    st.success("Account created. Go to login.")
                except Exception as e:
                    st.error(f"Error signing up: {str(e)}")

    elif choice == "Login":
        st.subheader("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type='password')
        login_checkbox = st.sidebar.checkbox("Login")

        if login_checkbox:
            stored_hash = loginDb.lindex(username, 0)
            if stored_hash and check_hashes(password, stored_hash):
                st.success(f"Logged In as {username}")
                login_userid = loginDb.lindex(username, 1)
                task = st.selectbox("Task", ["Rated Movies", "Movie Recommendations", "Rate Movies"])

                if task == "Rated Movies":
                    if activeUserRatingDb.exists(login_userid):
                        rec_dict = json.loads(activeUserRatingDb.get(login_userid))
                        movie_dict = json.loads(movieDb.get("movie_dict"))
                        cols = st.columns(5)
                        i = 0
                        for movie_id, (rating, genre) in rec_dict.items():
                            if movie_id in movie_dict:
                                title, poster_url, genres, year = movie_dict[movie_id]
                                with cols[i % 5]:
                                    st.image(poster_url, width=120)
                                    st.text(title[:15] + ".." if len(title) > 15 else title)
                                    st.markdown(f"{title}  \n*({genres})*")
                                    st.markdown(f"**{year}**")
                                    st.markdown(f"My rating: **{rating}**")
                                i += 1
                    else:
                        st.info("No rated movies yet.")

                elif task == "Movie Recommendations":
                    st.warning("This feature requires backend running.")

                elif task == "Rate Movies":
                    genres = [genDb.lindex("genres", i) for i in range(genDb.llen("genres"))]
                    options = st.multiselect("Choose atleast 5 Genres", genres)
                    if st.button("Submit Genres"):
                        if len(options) < 5:
                            st.error("Please select at least 5 genres.")
                        else:
                            res = requests.post(f"{addr}/compute/movies/{login_userid}", data=jsonpickle.encode(options))
                            if res.status_code == 200:
                                st.success("Movies loaded. Start rating!")
                                session_state.rec_dict = {}
                                session_state.show_movie_count = 0
                            else:
                                st.error(f"API Error: {res.text}")
                    if userMovieDb.exists(login_userid):
                        session_state.rec_dict = render_movie_list(login_userid, session_state.show_movie_count, session_state.rec_dict)

                        if st.button("Show More"):
                            session_state.show_movie_count += 24
                        if st.button("Back"):
                            session_state.show_movie_count = max(0, session_state.show_movie_count - 24)
                        if st.button("Save Ratings"):
                            activeUserRatingDb.set(login_userid, json.dumps(session_state.rec_dict))
                            st.success("Ratings saved successfully.")
            else:
                st.error("Invalid login credentials")

if __name__ == "__main__":
    try:
        latest_user_id = genDb.get("latest_user_id")
        if latest_user_id is None:
            latest_user_id = 0
            genDb.set("latest_user_id", latest_user_id)
        latest_user_id = int(latest_user_id)
        main()
    except Exception as e:
        st.error(f"Startup error: {str(e)}")
