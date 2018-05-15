from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import User, Category, Base, Book

engine = create_engine('sqlite:///library.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create dummy user
User1 = User(name="Book Worm", email="lovebooks@example.com",
             picture='https://upload.wikimedia.org/wikipedia/commons/7/7c/Profile_avatar_placeholder_large.png')
session.add(User1)
session.commit()


# Fiction Books
category1 = Category(user_id=1, name="Fiction")

session.add(category1)
session.commit()

book1 = Book(user_id=1, title="A Game of Thrones: A Song of Ice and Fire: Book One", 
                isbn="9780553897845", google_id="5NomkK4EV68C", category=category1)

session.add(book1)
session.commit()

# Children Books
category2 = Category(user_id=1, name="Children")

session.add(category2)
session.commit()

book2 = Book(user_id=1, title="One Fish Two Fish Red Fish Blue Fish", 
                isbn="9780385372008", google_id="067xAwAAQBAJ", category=category2)

session.add(book2)
session.commit()

# Inspirational Books
category3 = Category(user_id=1, name="Inspirational")

session.add(category3)
session.commit()

book3 = Book(user_id=1, title="The Subtle Art of Not Giving a F*ck: A Counterintuitive Approach to Living a Good Life", 
                isbn="9780062457738", google_id="yng_CwAAQBAJ", category=category3)

session.add(book3)
session.commit()

# Programming Books
category4 = Category(user_id=1, name="Programming")

session.add(category4)
session.commit()

book4 = Book(user_id=1, title="Test-Driven Development with Python: Obey the Testing Goat: Using Django, Selenium, and JavaScript", 
                isbn="9781491958674", google_id="3igvDwAAQBAJ", category=category4)

session.add(book4)
session.commit()

# Biography Books
category5 = Category(user_id=1, name="Biography")

session.add(category5)
session.commit()

book5 = Book(user_id=1, title="Elon Musk: Tesla, SpaceX, and the Quest for a Fantastic Future", 
                isbn="9780062301260", google_id="Yd99BAAAQBAJ", category=category5)

session.add(book5)
session.commit()

# Business Books
category6 = Category(user_id=1, name="Business")

session.add(category6)
session.commit()

book6 = Book(user_id=1, title="Scrum: The Art of Doing Twice the Work in Half the Time", 
                isbn="9780385346467", google_id="93tIAwAAQBAJ", category=category6)

session.add(book6)
session.commit()

print "added books!"
