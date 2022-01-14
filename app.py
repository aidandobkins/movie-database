from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
from flask_paginate import Pagination, get_page_parameter
from flask_bootstrap import Bootstrap
import json
from tabulate import tabulate
from flask_jsglue import JSGlue
import random

'''Read data from Json File'''
f = open('static/movies.json', encoding="utf8")
Movies = json.loads(f.read())

# Initialize
app = Flask(__name__)
bootstrap = Bootstrap(app)
jsglue = JSGlue(app)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'mysecretkey'

# Enter your database connection details below

conn = sqlite3.connect('CRUDdb.sqlite', check_same_thread=False)


# mysql = MySQL()

# app.config['MYSQL_DATABASE_HOST'] = "localhost"
# app.config['MYSQL_DATABASE_PORT'] = 3308
# app.config['MYSQL_DATABASE_USER'] = 'root'
# app.config['MYSQL_DATABASE_PASSWORD'] = ''
# app.config['MYSQL_DATABASE_DB'] = 'flaskcrud'

# # Intialize MySQL
# mysql.init_app(app)


@app.route('/', methods=['GET', 'POST'])
def login():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return redirect(url_for('movies'))

    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if user exists using MySQL
        # conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        # Fetch one record and return result
        user = cursor.fetchone()
        print(user)
        # If user exists in users table in out database
        if user and check_password_hash(user[4], password):
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = user[0]
            session['username'] = user[3]
            session['email'] = user[2]
            # Redirect to home page
            return redirect(url_for('movies'))
        else:
            # user doesnt exist or username/password incorrect
            msg = 'Incorrect username/password! :/'

    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        last = request.form['last_name']
        first = request.form['first_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hash = generate_password_hash(password)

        # Check if user exists using MySQL
        # conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        # If user exists show error and validation checks
        if user:
            msg = 'Username/user already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # user doesnt exists and the form data is valid, now insert new user into users table
            cursor.execute('INSERT INTO users (firstname, lastname, email, username, password) VALUES (?, ?, ?, ?, ?)',
                           (first, last, email, username, hash,))
            conn.commit()
            msg = 'You have successfully registered!'
            return render_template('index.html')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


@app.route('/movies', methods=['GET', 'POST'])
def movies():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        # Get form data
        sort = request.form.get("sort")
        layout = request.form.get("page_layout")
        keyword = request.form.get("search")

        # Check if there is filter data specified by a user else use default filters
        # Redirect to movie function with filters
        if layout or keyword:
            return redirect(url_for('movie', key=sort, layout=layout, query=keyword))
        else:
            return redirect(url_for('movie', key="latest", layout=10, query=""))

    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


def search(query):
    # Initialize a search list
    search_results = []
    if query:  # If there is query specified by a user, perform the search logic
        # each_movie is the dictionary that contains information of each movie
        for each_movie in Movies:
            # Loop through each key in a each_movie dictionary
            for each_key in each_movie:
                # First, search the title and year
                if each_key == "title" or each_key == "year":
                    # Convert strings to lower case using casefold(), and then check if they contain the query
                    # using the find function (if index >= 0, the title or year contains the query)
                    if str(each_movie[each_key]).casefold().find(query.casefold()) >= 0:
                        # Add movie to the search list using the list append method
                        search_results.append(each_movie)
                # Second, search the cast or genres
                elif each_key == "cast" or each_key == "genres":
                    # Continue the logic only if there is at least one element in the cast or genres array
                    if len(each_movie[each_key]) > 0:
                        # Loop through each element of the cast or genres array
                        for each_string in each_movie[each_key]:
                            # Check if an element of cast or genres array contains the query
                            # Always use casefold() for searching
                            if str(each_string).casefold().find(query.casefold()) >= 0:
                                # Add the movie to the search list if the cast of genres contains the query
                                search_results.append(each_movie)
    return search_results

@app.route('/profile')
def profile():
    if 'loggedin' in session:
        userlist= []
        userlist.append(session['username'])
        userlist.append(session['email'])
        
        cursor = conn.cursor()
        cursor.execute('SELECT genres FROM watched WHERE username = ? AND rowid = 2' , (session['username'],))
        r = str(cursor.fetchone())
        r = r.replace("(", "")
        r = r.replace(")", "")
        r = r.replace("'", "")
        r = r.split(",")
        r = r[0]
        if r[0] == ' ':
            r = r[1:]
        for i in range(26791):
            cursor.execute('SELECT genres FROM movies WHERE rowid = ?', (i,))
            e = str(cursor.fetchone())
            print(e)
            print(r)
            if r in e:
                cursor.execute('SELECT title FROM movies WHERE rowid = ?', (i,))
                rec = cursor.fetchone()
                break
        return render_template('profile.html', user=userlist, recommend = rec)
        
    return redirect(url_for('login'))

@app.route('/movie')
def movie():
    if 'loggedin' in session:
        # Use the get_page_parameter of flask-paginate extension to navigate to that page number
        page = request.args.get(get_page_parameter(), type=int, default=1)

        # Get parameters (key, layout and query) from the url
        value = request.args.get('key')
        layout = request.args.get('layout')
        query = request.args.get('query')

        search_results = search(query)
        # Insert keywords into database
        cursor = conn.cursor()

        if query:
            genres_string = ""
            for each_movie in search_results:
                for each_key in each_movie:
                    if each_key == "title":
                        gen = str(each_movie["genres"]).replace("'", "")
                        cursor.execute('INSERT INTO searched (username, keywords, title, genres) VALUES (?, ?, ?, ?)',
                                       (session['username'], query, each_movie[each_key], gen))
            conn.commit()

        # Sort Movies according to the sort option
        if value == 'latest':
            sorted_list = sorted(Movies, key=lambda sort: sort['year'], reverse=True)
        elif value == 'oldest':
            sorted_list = sorted(Movies, key=lambda sort: sort['year'])
        else:
            sorted_list = sorted(Movies, key=lambda sort: sort['title'])

        # Compute the starting index for each page; index = 0 on page 1, index = 10 on page 2, etc.
        # The layout parameter in the url will be a string; Convert it to an integer to use it in an expression
        index = (page - 1) * int(layout)

        # If there is a query from a user
        if query:
            # Pagination: Extract the list of movies to be displayed on the current page using the index
            # Pagination: Display movies from 1 to 10 on page 1, movies from 10 to 20 on page 2, etc
            list_per_page = search_results[index:index + int(layout)]
            pagination = Pagination(page=page, per_page=int(layout), css_framework='bootstrap4',
                                    total=len(search_results),
                                    record_name='Movies')
        # If no query, then apply the sort and layout filters
        else:
            list_per_page = sorted_list[index:index + int(layout)]
            pagination = Pagination(page=page, per_page=int(layout), css_framework='bootstrap4', total=len(sorted_list),
                                    record_name='Movies')
        # Render the html page to display movies along with the pagination
        return render_template('movies.html', movies=list_per_page, pagination=pagination)

    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/history')
def history():
    # Check if user is loggedin
    listed = []
    finalgenre = []
    if 'loggedin' in session:
        # We need all the user info for the user so we can display it on the profile page
        # conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT keywords) FROM searched WHERE username = ?', (session['username'],))
        # user = cursor.fetchone()
        number_of_keywords = cursor.fetchone()[0]
        user_list = [session['username'], number_of_keywords]
        
        searches = cursor.execute('SELECT DISTINCT keywords FROM searched WHERE username = ?', (session['username'],))
        for i in searches:
            j = str(i[0])
            listed.append(str(j))
        
        for i in listed:
            genres = []
            gencount = []
            finalgen = []
            for j in range(42):
                gencount.append(1)
            tempgen = []
            searchg = cursor.execute('SELECT DISTINCT genres FROM searched WHERE username = ? AND keywords = ?', (session['username'], i))
            
            for g in searchg:
                genre = str(g[0])
                genre = genre.replace("[","")
                genre = genre.replace("]","")
                genre = genre.replace("'","")
                tempgen.append(genre)
                
            for gen in tempgen:
                a = gen.split(", ")
                for j in a:
                    if j not in genres:
                        genres.append(j)
                    else:
                        gencount[genres.index(j)] = gencount[genres.index(j)] + 1
                
            for k in range(len(genres)):
                temptext = str(genres[k]) + ": " + str(gencount[k])
                finalgen.append(temptext)
            finalgenre.append(finalgen)
            
        finallist = [list(z) for z in zip(listed, finalgenre)]
            
        searchlist = tabulate(finallist, tablefmt='html')
        searchlist = searchlist.replace("<table>", "")
        searchlist = searchlist.replace("</table>", "")
        searchlist = searchlist.replace("<tbody>", "")
        searchlist = searchlist.replace("</tbody>", "")
        #searchlist = searchlist.replace("<tr>", "")
        #searchlist = searchlist.replace("</tr>", "")
        
        # Show the history page with user statistics
        return render_template('history.html', ulist=user_list, search=searchlist)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route("/passval", methods=['POST'])
def passval():
    movie = request.form['title']
    movie = str(movie)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT genres FROM movies WHERE title = ?', (movie,))
    genres = str(cursor.fetchone())
    genres = genres.replace("[", "")
    genres = genres.replace("]", "")
    genres = genres.replace("'", "")
    genres = genres.replace("(", "")
    genres = genres.replace(")", "")
    genres = genres.replace('"', "")
    cursor.execute('INSERT OR IGNORE INTO watched (username, title, genres) VALUES (?, ?, ?)', (session['username'], movie, genres,))
    conn.commit()
    return redirect(url_for('movies'))


if __name__ == "__main__":
    app.debug = True
    app.run()
