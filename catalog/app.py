from flask import Flask, render_template, request, redirect, jsonify, \
            url_for, flash


from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Book, User

from flask import session as login_session
import random
import string
import urllib

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(PROJECT_ROOT, 'client_secrets.json')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'

CLIENT_ID = json.load(open(json_url))['web']['client_id']
APPLICATION_NAME = "Library App"


# Connect to Database and create database session
engine = create_engine('postgresql://catalog:<password>@localhost/library')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    categories = session.query(Category).order_by(asc(Category.name))
    return render_template('login.html', categories=categories, STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(json_url, scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # See if a user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;border-radius: 100px;\
            -webkit-border-radius: 100px;-moz-border-radius: 100px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    user = session.query(User).filter_by(email=email).first()
    if user is None:
        return None
    else:
        return user.id


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        flash('You are now logged out.')
        return redirect(url_for('showCategories'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Books in the Library
# Return all books for a given category
@app.route('/category/<int:category_id>/books/JSON')
def categoryBooksJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).first()
    if category is None:
        return "{None found}"
    books = session.query(Book).filter_by(
        category_id=category_id).all()
    return jsonify(Books=[b.serialize for b in books])


# Return a specific book in a given category
@app.route('/category/<int:category_id>/book/<int:book_id>/JSON')
def bookJSON(category_id, book_id):
    book = session.query(Book).filter_by(id=book_id).first()
    if book is None:
        return "{None found}"
    else:
        return jsonify(Book=book.serialize)


# Return all available book categories
@app.route('/categories/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(Categories=[c.serialize for c in categories])


# Return all the books that are currently in the database
@app.route('/library/JSON')
def libraryJSON():
    books = session.query(Book).all()
    return jsonify(Book=[b.serialize for b in books])


# Show all categories
@app.route('/')
@app.route('/category/')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return render_template('library.html', categories=categories)
    else:
        return render_template('library.html', categories=categories,
                               picture=login_session['picture'],
                               name=login_session['username'])


# Create a new category
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'].capitalize(),
            user_id=login_session['user_id'])
        session.add(newCategory)
        flash("New Category '%s' Successfully Created" % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template('newCategory.html', categories=categories,
                               name=login_session['username'],
                               picture=login_session['picture'])


# Edit a category
@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(asc(Category.name))
    editedCategory = session.query(
        Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        return redirect('/login')
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name'].capitalize()
            flash("Category '%s' successfully edited." % editedCategory.name)
            return redirect(url_for('showBooks', category_id=category_id))
    else:
        return render_template('editCategory.html', category=editedCategory,
                               categories=categories,
                               name=login_session['username'],
                               picture=login_session['picture'])


# Delete a category
@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(asc(Category.name))
    categoryToDelete = session.query(
        Category).filter_by(id=category_id).one()
    if categoryToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
            to delete this category. Please create your own category in order \
            to delete.');}</script><body onload='myFunction()''>"
    numbooks = session.query(Book).filter_by(
        category_id=category_id).count()
    if numbooks > 0:
        flash("Cannot delete category with books in it! "
              "Delete all books in '%s' category first."
              % categoryToDelete.name)
        return redirect(url_for('showBooks', category_id=category_id))
    if request.method == 'POST':
        session.delete(categoryToDelete)
        flash("Category '%s' successfully deleted." % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteCategory.html',
                               category=categoryToDelete,
                               categories=categories,
                               name=login_session['username'],
                               picture=login_session['picture'])


# Show books
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/books/')
def showBooks(category_id):
    categories = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    books = session.query(Book).filter_by(
        category_id=category_id).all()
    if 'username' not in login_session:
        return render_template('books.html', books=books, category=category,
                               creator=creator, categories=categories)
    else:
        return render_template('books.html', books=books, category=category,
                               creator=creator, categories=categories,
                               picture=login_session['picture'],
                               name=login_session['username'],
                               user=login_session['user_id'])


# Preview a book
@app.route('/category/<int:category_id>/books/<int:book_id>/')
def previewBook(category_id, book_id):
    categories = session.query(Category).order_by(asc(Category.name))
    book = session.query(Book).filter_by(id=book_id).first()
    if book is None:
        flash("There is no book with that ID.")
        return redirect(url_for('showCategories'))
    creator = getUserInfo(book.user_id)
    url = ("https://www.googleapis.com/books/v1/volumes?q=id:{0}"
           "&key=AIzaSyCUq7LzPk_JZ03hGnD30gtvGx3dfHdc6BY".format(book.isbn))
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result['items']:
        thebook = result['items'][0]
        if 'subtitle' in thebook['volumeInfo']:
            title = (thebook['volumeInfo']['title'] + ': ' +
                     thebook['volumeInfo']['subtitle'])
        else:
            title = thebook['volumeInfo']['title']
        cover = thebook['volumeInfo']['imageLinks']['thumbnail']
        if 'authors' in thebook['volumeInfo']:
            authors = thebook['volumeInfo']['authors']
        else:
            authors = 'No author available.'
        if 'description' in thebook['volumeInfo']:
            description = thebook['volumeInfo']['description']
        else:
            description = 'No Description available for this book.'
        if 'username' not in login_session:
            return render_template('previewBook.html', book=book,
                                   cover=cover,
                                   authors=authors, description=description,
                                   creator=creator, categories=categories)
        else:
            return render_template('previewBook.html', book=book,
                                   cover=cover,
                                   authors=authors, description=description,
                                   picture=login_session['picture'],
                                   name=login_session['username'],
                                   creator=creator, categories=categories)
    else:
        flash("Cannot retrieve the information for '%s'." % book.title)
        return redirect(url_for('showBooks', category_id=category_id))


# Search for a new book
@app.route('/search/', methods=['GET'])
def searchResults():
    if request.method == 'GET':
        entry = request.args.get('search')
    if entry is None:
        entry = ''
    categories = session.query(Category).order_by(asc(Category.name))
    url = ("https://www.googleapis.com/books/v1/volumes?q={0}"
           "&key="
           "AIzaSyCUq7LzPk_JZ03hGnD30gtvGx3dfHdc6BY".format(urllib.quote(entry, safe='')))
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if 'error' in result or result['totalItems'] < 1:
        books = []
    else:
        books = result['items']
    if 'username' not in login_session:
        return render_template('searchresults.html', books=books,
                               categories=categories, entry=entry)
    else:
        return render_template('searchresults.html', books=books,
                               picture=login_session['picture'],
                               name=login_session['username'],
                               categories=categories, entry=entry)


# Add a new book
@app.route('/book/<isbn>/new/', methods=['GET', 'POST'])
def newBook(isbn):
    categories = session.query(Category).order_by(asc(Category.name))
    if request.method == 'POST':
        newBook = Book(title=request.form['title'], isbn=request.form['isbn'],
                       category_id=request.form['category_id'],
                       user_id=login_session['user_id'])
        session.add(newBook)
        session.commit()
        flash("'%s' successfully added." % (newBook.title))
        return redirect(url_for('showBooks',
                        category_id=request.form['category_id']))
    else:
        url = ("https://www.googleapis.com/books/v1/volumes?q=isbn:{0}"
               "&key=AIzaSyCUq7LzPk_JZ03hGnD30gtvGx3dfHdc6BY".format(isbn))
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])
        if 'error' in result or result['totalItems'] < 1:
            flash('No Book was found with ISBN %s' % isbn)
            return redirect(url_for('showCategories'))
        else:
            thebook = result['items'][0]
            bookadded = session.query(Book).filter_by(isbn=isbn).first()
        if 'subtitle' in thebook['volumeInfo']:
            title = (thebook['volumeInfo']['title'] + ': ' +
                     thebook['volumeInfo']['subtitle'])
        else:
            title = thebook['volumeInfo']['title']
        if ('imageLinks' in thebook['volumeInfo']
                and 'thumbnail' in thebook['volumeInfo']['imageLinks']):
            cover = thebook['volumeInfo']['imageLinks']['thumbnail']
        else:
            cover = '#'
        if 'authors' in thebook['volumeInfo']:
            authors = thebook['volumeInfo']['authors']
        else:
            authors = ''
        if 'description' in thebook['volumeInfo']:
            description = thebook['volumeInfo']['description']
        else:
            description = 'No Description available for this book.'
        if 'username' not in login_session:
            return render_template('newbook.html', title=title, cover=cover,
                                   authors=authors, description=description,
                                   categories=categories,
                                   bookadded=bookadded, isbn=isbn)
        else:
            return render_template('newbook.html', title=title, cover=cover,
                                   authors=authors, description=description,
                                   picture=login_session['picture'],
                                   name=login_session['username'],
                                   categories=categories, bookadded=bookadded,
                                   isbn=isbn)


# Delete a book
@app.route('/book/<book_id>/delete/', methods=['GET', 'POST'])
def deleteBook(book_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(asc(Category.name))
    bookToDelete = session.query(
        Book).filter_by(id=book_id).one()
    if bookToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
            to delete this book. Please add your own books in order \
            to delete.');}</script><body onload='myFunction()''>"
    categories = session.query(Category).order_by(asc(Category.name))
    category_id = bookToDelete.category.id
    if request.method == 'POST':
        session.delete(bookToDelete)
        flash("'%s' successfully deleted." % bookToDelete.title)
        session.commit()
        return redirect(url_for('showBooks', category_id=category_id))
    else:
        return render_template('deleteBook.html', book=bookToDelete,
                               categories=categories,
                               name=login_session['username'],
                               picture=login_session['picture'])


if __name__ == '__main__':
    app.secret_key = 'JZ03hGnD30gtvGx3dfHdc6BY'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
