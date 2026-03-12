"""OpenAI function calling schemas for LLM tool use."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": (
                "Update the user's profile information. Use this when you learn "
                "new things about the user during conversation, such as their name, "
                "languages they speak, or the language they want to learn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The user's display name",
                    },
                    "known_languages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "ISO 639-1 codes of languages the user already speaks",
                    },
                    "target_language": {
                        "type": "string",
                        "description": "ISO 639-1 code of the language the user wants to learn",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "name_cat",
            "description": (
                "Set or change the cat's name. Use this when the user gives you "
                "(the cat) a name, or when you and the user agree on a name for you."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The cat's new name",
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rate_word",
            "description": (
                "Rate a word or grammar form the user just used in conversation. "
                "Call this whenever the user attempts to use a word or form in the "
                "target language. Rating guide: 4=Easy (used correctly without "
                "hesitation), 3=Good (minor error, right idea), 2=Hard (significant "
                "error, needed correction), 1=Again (completely wrong, needs re-learning)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {
                        "type": "string",
                        "description": "The word or grammar form in dictionary/base form",
                    },
                    "rating": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4],
                        "description": "py-fsrs rating: 1=Again, 2=Hard, 3=Good, 4=Easy",
                    },
                    "context": {
                        "type": "string",
                        "description": "Brief note on how the user used the word",
                    },
                },
                "required": ["word", "rating", "context"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_vocabulary_card",
            "description": (
                "Create a new vocabulary or grammar flashcard. Use this when "
                "introducing a new word or concept to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "front": {
                        "type": "string",
                        "description": "The word or phrase in the target language",
                    },
                    "back": {
                        "type": "string",
                        "description": "Translation or explanation in the user's known language",
                    },
                    "card_type": {
                        "type": "string",
                        "enum": ["vocabulary", "grammar", "phrase"],
                        "description": "Type of card",
                    },
                    "context_sentence": {
                        "type": "string",
                        "description": "An example sentence using the word",
                    },
                },
                "required": ["front", "back", "card_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_media",
            "description": (
                "Search for movies, series, or other media content. Use this when "
                "the user mentions wanting to watch or consume something in their "
                "target language."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "media_type": {
                        "type": "string",
                        "enum": ["movie", "series", "book", "other"],
                        "description": "Type of media to search for",
                    },
                },
                "required": ["query", "media_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": (
                "Create a language learning goal for the user. Use this when the "
                "user expresses a goal like wanting to watch a movie or read a book "
                "in the target language."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Goal title",
                    },
                    "media_type": {
                        "type": "string",
                        "enum": ["movie", "series", "book", "other"],
                        "description": "Type of media associated with the goal",
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
]
