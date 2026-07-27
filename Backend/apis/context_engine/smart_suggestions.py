# smart_suggestions.py
from difflib import get_close_matches
from .taxonomy_loader import TAXONOMY


def get_suggestions(user_input):

    suggestions = {}

    text = user_input.lower()

    for field, values in TAXONOMY.items():

        matches = []

        for value in values:

            if text in value.lower():
                matches.append(value)

        fuzzy = get_close_matches(
            user_input,
            values,
            n=5,
            cutoff=0.3
        )

        combined = list(set(matches + fuzzy))

        if combined:
            suggestions[field] = combined[:5]

    return suggestions