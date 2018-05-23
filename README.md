# Item Catalog Application

This is a [Udacity FSND](https://www.udacity.com/course/full-stack-web-developer-nanodegree--nd004) project.

## About

This is a RESTful web application utilizing the Flask framework and the SQLAlchemy ORM toolkit. The catalog consists of books in different categories that have been added to the database. The Google Books API is used to display additional information about the books. Users can also search for books by entering title or ISBN. Google OAuth2 Sign-In is used to offer further CRUD functionality like creating and editing new categories, as well as adding books that have been found using the search feature of the app. The user is able to delete books and categories they have added.

### Dependencies

To run the application locally you would need:
* [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
* [Vagrant](https://www.vagrantup.com/downloads.html)
* [Git](https://git-scm.com/downloads) - in case you are running Windows, Git Bash can be used for running the Vagrant machine.

### Installation

After cloning the repo, `$ cd` to where the `Vagrantfile` is located and
```sh
$ vagrant up
```
After the virtual environment is successfully provisioned: 
```sh
$ vagrant ssh
```
Inside the virtual environment:
```sh
$ cd /vagrant/catalog
```
Create and populate the app's database with:
```sh
$ python database_setup.py
$ python init_database.py
```
Run the application:
```sh
$ python app.py
```
Access the application locally in your web browser using [http://localhost:8000](http://localhost:8000)

### JSON Endpoints
The application offers the following JSON endpoints:
* /library/JSON - Returns all the books that are currently in the database
* /categories/JSON - Returns all available book categories
* /category/<int:category_id>/books/JSON - Returns all the books for a given category
* /category/<int:category_id>/book/<int:book_id>/JSON - Returns a specific book in a specific category


