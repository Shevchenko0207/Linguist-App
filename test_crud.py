import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, or_
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext
import shutil

# ---
# NOTE: The models and functions from your app.py are replicated here for a standalone test script.
# In a real-world scenario, you would structure your project to import these directly.
# ---

engine = create_engine("sqlite:///linguist_test.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -----------------------------------------------------------------------------
# Database Models (replicated from app.py)
# -----------------------------------------------------------------------------
class User(Base):
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


def setup_database():
    """Створює таблиці в тестовій базі даних."""
    Base.metadata.create_all(engine)


# -----------------------------------------------------------------------------
# CRUD Functions (replicated from app.py, with slight modifications for session management)
# -----------------------------------------------------------------------------
def user_create(name, email, password):
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


def user_get_by_email(email):
    with Session() as session:
        return session.query(User).filter_by(email=email).first()


def deck_create(name, user_id):
    with Session() as session:
        new_deck = Deck(name=name, user_id=user_id)
        session.add(new_deck)
        session.commit()
        session.refresh(new_deck)
        return new_deck


def deck_get_by_id(deck_id):
    with Session() as session:
        return session.get(Deck, deck_id)


def deck_delete_by_id(deck_id):
    with Session() as session:
        deck = session.get(Deck, deck_id)
        if deck:
            session.delete(deck)
            session.commit()
            return True
        return False


def card_create(user_id, word, translation, tip, deck_id=None):
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


def card_update(card_id, word=None, translation=None, tip=None):
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
    with Session() as session:
        card = session.get(Card, card_id)
        if card:
            session.delete(card)
            session.commit()
            return True
        return False


# -----------------------------------------------------------------------------
# Main Test Script
# -----------------------------------------------------------------------------
def run_tests():
    db_file = "linguist_test.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    print("Починаємо тестування CRUD операцій...")
    setup_database()

    try:
        # Тест 1: Створення користувача
        print("Тест 1: Створення користувача...")
        user = user_create("TestUser", "test@example.com", "testpassword")
        assert user is not None, "Помилка: Користувача не було створено."
        assert user.name == "TestUser", "Помилка: Неправильне ім'я користувача."
        print("✅ Тест 1 пройшов успішно.")

        # Тест 2: Створення колоди для користувача
        print("\nТест 2: Створення колоди...")
        deck = deck_create("Test Deck", user.id)
        assert deck is not None, "Помилка: Колоду не було створено."
        assert deck.name == "Test Deck", "Помилка: Неправильна назва колоди."
        assert deck.user_id == user.id, "Помилка: Неправильний user_id для колоди."
        print("✅ Тест 2 пройшов успішно.")

        # Тест 3: Створення картки в колоді
        print("\nТест 3: Створення картки...")
        card = card_create(user.id, "word", "translation", "tip", deck.id)
        assert card is not None, "Помилка: Картку не було створено."
        assert card.word == "word", "Помилка: Неправильне слово картки."
        assert (
            card.deck_id == deck.id
        ), "Помилка: Картка не належить до правильної колоди."
        print("✅ Тест 3 пройшов успішно.")

        # Тест 4: Оновлення картки
        print("\nТест 4: Оновлення картки...")
        updated_card = card_update(card.id, word="updated_word")
        assert updated_card is not None, "Помилка: Картку не оновлено."
        assert (
            updated_card.word == "updated_word"
        ), "Помилка: Оновлене слово не збереглося."
        print("✅ Тест 4 пройшов успішно.")

        # Тест 5: Видалення картки
        print("\nТест 5: Видалення картки...")
        delete_success = card_delete_by_id(card.id)
        assert delete_success is True, "Помилка: Картку не видалено."
        with Session() as session:
            deleted_card = session.get(Card, card.id)
            assert deleted_card is None, "Помилка: Картка все ще існує після видалення."
        print("✅ Тест 5 пройшов успішно.")

        # Тест 6: Видалення колоди (перевірка каскадного видалення)
        print("\nТест 6: Видалення колоди...")
        delete_deck_success = deck_delete_by_id(deck.id)
        assert delete_deck_success is True, "Помилка: Колоду не видалено."
        with Session() as session:
            deleted_deck = session.get(Deck, deck.id)
            assert deleted_deck is None, "Помилка: Колода все ще існує після видалення."
            # Перевіряємо, чи були видалені картки в цій колоді
            deleted_card_in_deck = session.get(Card, card.id)
            assert (
                deleted_card_in_deck is None
            ), "Помилка: Картка не була видалена каскадно."
        print("✅ Тест 6 пройшов успішно.")

    except AssertionError as e:
        print(f"\n❌ Тест провалився: {e}")
    finally:
        # Очищення: закриваємо сесію та видаляємо тестову базу даних
        print("\nОчищення тестової бази даних...")
        engine.dispose()
        os.remove(db_file)
        print("Тестування завершено.")


if __name__ == "__main__":
    run_tests()
