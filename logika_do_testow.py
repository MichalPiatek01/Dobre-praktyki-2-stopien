import re
from collections import Counter


def is_palindrome(text: str) -> bool:
    cleaned = ''.join(char.lower() for char in text if char != ' ')
    return cleaned == cleaned[::-1]


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)


def count_vowels(text: str) -> int:
    vowels = "aeiouyó"
    text = text.lower()
    return sum(1 for char in text if char in vowels)


def calculate_discount(price: float, discount: float) -> float:
    if 0 > discount or discount > 1:
        raise ValueError
    return price - (price * discount)


def flatten_list(nested_list: list) -> list:
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def word_frequencies(text: str) -> dict:
    text = text.lower()
    words = re.findall(r'\b\w+\b', text)
    return dict(Counter(words))


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True
