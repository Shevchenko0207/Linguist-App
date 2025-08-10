import os
import random
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, or_
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)

# -----------------------------------------------------------------------------
# Налаштування бази даних та конфігурація
# -----------------------------------------------------------------------------

engine = create_engine("sqlite:///linguist.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------------------------------------------------------------------
# Моделі бази даних
# -----------------------------------------------------------------------------


class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    decks = relationship("Deck", back_populates="user", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)


class Deck(Base):
    __tablename__ = "decks"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="decks")
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    tip = Column(String)
    user = relationship("User", back_populates="cards")
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=True)
    deck = relationship("Deck", back_populates="cards")

    def to_dict(self):
        """Перетворює об'єкт Card у словник для JSON-серіалізації."""
        return {
            'id': self.id,
            'word': self.word,
            'translation': self.translation,
            'tip': self.tip
        }


def setup_database():
    """Створення таблиць бази даних та додавання тестових даних, якщо їх немає."""
    Base.metadata.create_all(engine)
    with Session() as session:
        existing_user = session.query(User).filter_by(name="Alice").first()
        if not existing_user:
            user = User(
                name="Alice",
                email="alice@example.com",
                password=pwd_context.hash("password123"),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            deck = Deck(name="General Vocabulary", user_id=user.id)
            session.add(deck)
            session.commit()
            session.refresh(deck)

            card1 = Card(
                user_id=user.id,
                deck_id=deck.id,
                word="hello",
                translation="привіт",
                tip="Привітання",
            )
            card2 = Card(
                user_id=user.id,
                deck_id=deck.id,
                word="world",
                translation="світ",
                tip="Наша планета",
            )
            session.add(card1)
            session.add(card2)
            session.commit()


# -----------------------------------------------------------------------------
# CRUD-функції для User, Deck та Card
# -----------------------------------------------------------------------------


def user_create(name, email, password):
    """Створює нового користувача."""
    with Session() as session:
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            return None
        hashed_password = pwd_context.hash(password)
        new_user = User(name=name, email=email, password=hashed_password)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user


def user_get_by_id(user_id):
    """Отримує користувача за ID."""
    with Session() as session:
        return session.get(User, user_id)


def user_get_by_email(email):
    """Отримує користувача за email."""
    with Session() as session:
        return session.query(User).filter_by(email=email).first()


def user_update_name(user_id, name):
    """Оновлює ім'я користувача."""
    with Session() as session:
        user = session.get(User, user_id)
        if user:
            user.name = name
            session.commit()
            session.refresh(user)
            return user
        return None


def user_change_password(user_id, old_password, new_password):
    """Змінює пароль користувача."""
    with Session() as session:
        user = session.get(User, user_id)
        if user and user.verify_password(old_password):
            user.password = pwd_context.hash(new_password)
            session.commit()
            return True
        return False


def user_delete_by_id(user_id):
    """Видаляє користувача."""
    with Session() as session:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
        return False


def deck_create(name, user_id):
    """Створює нову колоду."""
    with Session() as session:
        new_deck = Deck(name=name, user_id=user_id)
        session.add(new_deck)
        session.commit()
        session.refresh(new_deck)
        return new_deck


def deck_get_by_id(deck_id):
    """Отримує колоду за ID."""
    with Session() as session:
        return session.get(Deck, deck_id)


def deck_update(deck_id, name):
    """Оновлює назву колоди."""
    with Session() as session:
        deck = session.get(Deck, deck_id)
        if deck:
            deck.name = name
            session.commit()
            session.refresh(deck)
            return deck
        return None


def deck_delete_by_id(deck_id):
    """Видаляє колоду."""
    with Session() as session:
        deck = session.get(Deck, deck_id)
        if deck:
            session.delete(deck)
            session.commit()
            return True
        return False


def card_create(user_id, word, translation, tip, deck_id=None):
    """Створює нову картку."""
    with Session() as session:
        new_card = Card(
            user_id=user_id,
            word=word,
            translation=translation,
            tip=tip,
            deck_id=deck_id,
        )
        session.add(new_card)
        session.commit()
        session.refresh(new_card)
        return new_card


def card_get_by_id(card_id):
    """Отримує картку за ID."""
    with Session() as session:
        return session.get(Card, card_id)


def card_filter(sub_word):
    """Фільтрує картки за словом, перекладом або підказкою."""
    with Session() as session:
        search_term = f"%{sub_word}%"
        return (
            session.query(Card)
            .filter(
                or_(
                    Card.word.ilike(search_term),
                    Card.translation.ilike(search_term),
                    Card.tip.ilike(search_term),
                )
            )
            .all()
        )


def card_update(card_id, word=None, translation=None, tip=None):
    """Оновлює інформацію про картку."""
    with Session() as session:
        card = session.get(Card, card_id)
        if card:
            if word is not None:
                card.word = word
            if translation is not None:
                card.translation = translation
            if tip is not None:
                card.tip = tip
            session.commit()
            session.refresh(card)
            return card
        return None


def card_delete_by_id(card_id):
    """Видаляє картку."""
    with Session() as session:
        card = session.get(Card, card_id)
        if card:
            session.delete(card)
            session.commit()
            return True
        return False


# -----------------------------------------------------------------------------
# Flask-застосунок та маршрути
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.context_processor
def inject_datetime():
    """Додає об'єкт datetime до всіх шаблонів."""
    return {'datetime': datetime}


@login_manager.user_loader
def load_user(user_id):
    with Session() as session:
        return session.get(User, int(user_id))


@app.route("/")
@login_required
def index():
    with Session() as session:
        user_decks = session.query(Deck).filter_by(user_id=current_user.id).all()
        return render_template("decks.html", decks=user_decks)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if user_get_by_email(email):
            flash("Користувач з таким email вже існує.", "danger")
            return redirect(url_for("register"))

        user = user_create(name, email, password)
        if user:
            login_user(user)
            flash("Ви успішно зареєструвалися та увійшли!", "success")
            return redirect(url_for("index"))
        else:
            flash("Помилка реєстрації. Спробуйте ще раз.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = user_get_by_email(email)

        if user and user.verify_password(password):
            login_user(user)
            flash("Ви успішно увійшли!", "success")
            return redirect(url_for("index"))
        else:
            flash("Неправильний email або пароль.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Ви вийшли з акаунта.", "success")
    return redirect(url_for("login"))


@app.route("/deck/<int:deck_id>")
@login_required
def show_cards_in_deck(deck_id):
    with Session() as session:
        deck = session.get(Deck, deck_id)
        if not deck or deck.user_id != current_user.id:
            flash("Колоду не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        return render_template("cards.html", deck=deck, cards=deck.cards)


@app.route("/add_card/<int:deck_id>", methods=["POST"])
@login_required
def add_card_to_deck(deck_id):
    word = request.form["word"]
    translation = request.form["translation"]
    tip = request.form.get("tip")

    with Session() as session:
        deck = session.get(Deck, deck_id)
        if not deck or deck.user_id != current_user.id:
            flash("Колоду не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        
        if word and translation:
            card_create(
                user_id=current_user.id,
                word=word,
                translation=translation,
                tip=tip,
                deck_id=deck_id,
            )
            flash("Картку додано успішно!", "success")
        else:
            flash("Помилка: слово та переклад є обов'язковими.", "danger")

    return redirect(url_for("show_cards_in_deck", deck_id=deck_id))


@app.route("/edit_card/<int:card_id>")
@login_required
def edit_card(card_id):
    with Session() as session:
        card = session.get(Card, card_id)
        if not card or card.user_id != current_user.id:
            flash("Картку не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        return render_template("edit_card.html", card=card)


@app.route("/update_card/<int:card_id>", methods=["POST"])
@login_required
def update_card(card_id):
    word = request.form.get("word")
    translation = request.form.get("translation")
    tip = request.form.get("tip")

    with Session() as session:
        card = session.get(Card, card_id)
        if not card or card.user_id != current_user.id:
            flash("Картку не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        
        card_update(card_id, word=word, translation=translation, tip=tip)
        flash("Картку оновлено успішно!", "success")
        return redirect(url_for("show_cards_in_deck", deck_id=card.deck_id))


@app.route("/delete_card/<int:card_id>", methods=["POST"])
@login_required
def delete_card(card_id):
    with Session() as session:
        card = session.get(Card, card_id)
        if not card or card.user_id != current_user.id:
            flash("Картку не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        
        deck_id = card.deck_id
        card_delete_by_id(card_id)
        flash("Картку видалено успішно!", "success")
        return redirect(url_for("show_cards_in_deck", deck_id=deck_id))


@app.route("/add_deck", methods=["POST"])
@login_required
def add_deck():
    deck_name = request.form.get("deck_name")
    if deck_name:
        deck_create(name=deck_name, user_id=current_user.id)
        flash("Колоду додано успішно!", "success")
    else:
        flash("Помилка: ім'я колоди не може бути порожнім.", "danger")
    return redirect(url_for("index"))


@app.route("/delete_deck/<int:deck_id>", methods=["POST"])
@login_required
def delete_deck(deck_id):
    with Session() as session:
        deck = session.get(Deck, deck_id)
        if not deck or deck.user_id != current_user.id:
            flash("Колоду не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        
        deck_delete_by_id(deck_id)
        flash("Колоду та всі картки в ній видалено успішно!", "success")
    return redirect(url_for("index"))


@app.route("/review/<int:deck_id>")
@login_required
def review_deck(deck_id):
    with Session() as session:
        deck = session.get(Deck, deck_id)
        if not deck or deck.user_id != current_user.id:
            flash("Колоду не знайдено або у вас немає доступу.", "danger")
            return redirect(url_for("index"))
        
        # Перетворюємо об'єкти Card на словники, щоб Jinja2 міг їх обробити
        cards = [card.to_dict() for card in deck.cards]
        random.shuffle(cards)  # Перемішуємо картки для практики
        return render_template("review.html", deck=deck, cards=cards)


if __name__ == "__main__":
    if not os.path.exists("linguist.db"):
        setup_database()
    app.run(debug=True)
