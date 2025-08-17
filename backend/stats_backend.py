# backend/stats_backend.py
import re
from collections import Counter
from flask import jsonify
from pymongo import MongoClient
from nltk.tokenize import sent_tokenize
import string

def get_stats_data(training_data_collection):
    """
    Sammelt alle Statistiken aus der Datenbank.
    """
    all_texts = list(training_data_collection.find({}, {'_id': 0, 'text': 1, 'label': 1}))

    if not all_texts:
        return {
            "total_words": 0, "total_chars": 0, "total_sentences": 0,
            "human": {"word_count": 0, "char_count": 0, "frequent_words": []},
            "ki": {"word_count": 0, "char_count": 0, "frequent_words": []},
            "total_frequent_words": []
        }

    # Bereinigung und Tokenisierung
    def clean_text(text):
        text = text.lower()
        text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
        return text

    all_human_texts = " ".join([d['text'] for d in all_texts if d['label'] == 'menschlich'])
    all_ki_texts = " ".join([d['text'] for d in all_texts if d['label'] == 'ki'])
    all_combined_texts = all_human_texts + " " + all_ki_texts

    # Wortzählung
    human_words = clean_text(all_human_texts).split()
    ki_words = clean_text(all_ki_texts).split()
    all_words = human_words + ki_words

    human_word_count = len(human_words)
    ki_word_count = len(ki_words)
    total_words = len(all_words)

    # Buchstabenzählung
    human_char_count = sum(len(word) for word in human_words)
    ki_char_count = sum(len(word) for word in ki_words)
    total_chars = human_char_count + ki_char_count

    # Satz-Zählung (verwendet das ursprüngliche, unbereinigte Textdokument)
    total_sentences = len(sent_tokenize(all_combined_texts))

    # Häufigste Wörter
    human_frequent_words = Counter(human_words).most_common(50)
    ki_frequent_words = Counter(ki_words).most_common(50)
    total_frequent_words = Counter(all_words).most_common(50)

    stats = {
        "total_words": total_words,
        "total_chars": total_chars,
        "total_sentences": total_sentences,
        "human": {
            "word_count": human_word_count,
            "char_count": human_char_count,
            "frequent_words": human_frequent_words
        },
        "ki": {
            "word_count": ki_word_count,
            "char_count": ki_char_count,
            "frequent_words": ki_frequent_words
        },
        "total_frequent_words": total_frequent_words
    }

    return jsonify(stats)