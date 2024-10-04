from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, NoResultFound
from flask_bcrypt import Bcrypt  # Import Flask-Bcrypt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm.exc import NoResultFound
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Email

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login1.db'  # Changed to use SQLite as per your original config
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Creating the SQLAlchemy db instance
db = SQLAlchemy(app)

# Defining a model for the login_page table
class LoginPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

# Database for contacts
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired()])

# Creating the database and the table
with app.app_context():
    db.create_all()

# Movie recommendation setup
df2 = pd.read_csv('./model/tmdb.csv')
tfidf = TfidfVectorizer(stop_words='english', analyzer='word')
tfidf_matrix = tfidf.fit_transform(df2['soup'])
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
df2 = df2.reset_index()
indices = pd.Series(df2.index, index=df2['title']).drop_duplicates()
all_titles = [df2['title'][i] for i in range(len(df2['title']))]

def get_recommendations(title):
    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]
    movie_indices = [i[0] for i in sim_scores]
    return_df = pd.DataFrame(columns=['Title', 'Homepage', 'ReleaseDate'])
    return_df['Title'] = df2['title'].iloc[movie_indices]
    return_df['Homepage'] = df2['homepage'].iloc[movie_indices]
    return_df['ReleaseDate'] = df2['release_date'].iloc[movie_indices]
    return return_df, sim_scores

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/service')
def service():
    return render_template('service.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')  # Use Flask-Bcrypt
        new_user = LoginPage(email=email, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! You can now sign in.")
            return redirect(url_for('signin'))
        except IntegrityError:
            db.session.rollback()
            flash("Email already exists!")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}")
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = LoginPage.query.filter_by(email=email).one()
            if bcrypt.check_password_hash(user.password, password):  # Use Flask-Bcrypt
                session['logged_in'] = True
                flash("Login successful!")
                return redirect(url_for('main'))
            else:
                flash("Incorrect password!")
        except NoResultFound:
            flash("User does not exist!")
        except Exception as e:
            flash(f"Error: {str(e)}")
    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.")
    return redirect(url_for('main'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data

        # Save the data to the database
        new_contact = Contact(name=name, email=email, message=message)
        db.session.add(new_contact)
        db.session.commit()

        flash("Message sent successfully!")
        return redirect(url_for('main'))

    return render_template('contact.html', form=form)

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'POST':
        m_name = " ".join(request.form['movie_name'].split())
        if m_name not in all_titles:
            return render_template('team.html', name=m_name)
        else:
            result_final, sim_scores = get_recommendations(m_name)
            names = result_final['Title'].tolist()
            homepages = result_final['Homepage'].tolist()
            release_dates = result_final['ReleaseDate'].tolist()
            sim_scores = [score[1] for score in sim_scores]  # Extract similarity scores
            return render_template('services.html', movie_names=names, movie_homepage=homepages, search_name=m_name, movie_releaseDate=release_dates, movie_simScore=sim_scores)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8080, debug=True)
