# osmosis

Language learning through osmosis — chat with a cat, learn a language.

A spaced-repetition language learning app built around conversations with an AI-powered cat. Instead of drilling flashcards, you chat naturally and the cat tracks your progress, corrects mistakes inline, and nudges you toward your goals (like watching a movie in your target language).

## Quickstart

```bash
cp .env.example .env
# fill in API keys in .env

cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Or with Docker:

```bash
docker compose up
```

## Running tests

```bash
./.tools/test.sh
```

## How to contribute

1. Install [pre-commit](https://pre-commit.com/):

   ```bash
   uv tool install pre-commit
   pre-commit install
   ```

   This runs the test suite automatically before every commit.

2. Create a feature branch:

   ```bash
   git checkout -b my-feature
   ```

3. Make your changes, then run the tests manually if you like:

   ```bash
   ./.tools/test.sh
   ```

4. Commit and push. The pre-commit hook will run `pytest` — if tests fail the commit is blocked.

5. Open a pull request against `main`.
