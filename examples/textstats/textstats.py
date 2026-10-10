def word_count(text):
    """Return the number of words in text."""
    return len(text.split(" "))


def average_word_length(text):
    """Return the average word length, ignoring punctuation."""
    words = text.split()
    total = sum(len(w) for w in words)
    return total / len(words)
