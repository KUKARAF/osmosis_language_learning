# Grammar Learning Plan

## Approach: LLM-generated, conversation-driven, dynamically quizzed

Grammar cards are created by the cat when the user makes a mistake or asks for
help. They store a **rule/pattern**, not a specific word. At quiz time, Groq
generates a **fresh random word** each time so the card never goes stale.

No spaCy. No pre-import step. No static answers to memorise.

---

## Key distinction from vocabulary cards

| | Vocabulary | Grammar |
|---|---|---|
| **Stored** | the word | the rule |
| **Quiz front** | the word | LLM-generated random word applying the rule |
| **Quiz back** | static translation | LLM-generated answer (JSON) |
| **Changes each review?** | no | yes — different word every time |

A conjugation card for "pretérito indefinido, -ar verbs" might quiz you on
`hablar` today, `caminar` tomorrow, `trabajar` next week — all from the same card.

---

## Card storage

Grammar cards use the existing `SRSCard` model. The fields carry different content:

| field | vocabulary | grammar |
|---|---|---|
| `card_type` | `"vocabulary"` | `"conjugation"` / `"pattern"` / `"gender"` |
| `front` | the lemma | human-readable rule name shown during load |
| `back` | translation | **JSON template** — instructions for the quiz generator |
| `context_sentence` | subtitle line | the sentence that triggered the card (user's mistake or show line) |

The `back` field for grammar cards is a JSON string the backend sends to Groq
to generate the quiz. It is never shown directly to the user.

### Example stored `back` values

**conjugation:**
```json
{
  "rule": "pretérito indefinido",
  "scope": "-ar verbs",
  "language": "es",
  "persons": ["yo", "tú", "él/ella", "nosotros", "vosotros", "ellos/ellas"]
}
```

**pattern:**
```json
{
  "rule": "ser vs estar",
  "scope": "temporary states",
  "language": "es",
  "native_language": "en"
}
```

**gender:**
```json
{
  "rule": "noun gender",
  "scope": "-ión nouns",
  "language": "es",
  "native_language": "en"
}
```

---

## Quiz generation at review time

When the user flips a grammar card, the frontend calls:

```
POST /srs/cards/{id}/generate-quiz
```

The backend reads `card.back` (the JSON template), sends a structured prompt to
Groq (Llama 3.3-70b), and returns a **quiz JSON object**. The frontend renders
this — never the raw `back` string.

### Response shapes

**conjugation:**
```json
{
  "type": "conjugation",
  "prompt": "Conjuga 'hablar' en pretérito indefinido",
  "word": "hablar",
  "answer": {
    "yo": "hablé",
    "tú": "hablaste",
    "él/ella": "habló",
    "nosotros": "hablamos",
    "vosotros": "hablasteis",
    "ellos/ellas": "hablaron"
  },
  "example": "Ayer hablé con mi madre durante una hora."
}
```

**pattern:**
```json
{
  "type": "pattern",
  "prompt": "Which verb — ser or estar?  'Hoy ___ muy cansado.'",
  "answer": "estoy",
  "rule": "estar for temporary states",
  "example": "Hoy estoy muy cansado. (temporary → estar)"
}
```

**gender:**
```json
{
  "type": "gender",
  "prompt": "¿el o la?  → 'canción'",
  "answer": "la canción (f)",
  "rule": "-ión nouns are almost always feminine",
  "example": "Me encanta esa canción."
}
```

The Groq prompt instructs the model to pick a **random common word** that fits
the rule and return strict JSON — no prose. A low temperature (0.3–0.4) keeps
the answer reliable while keeping the word random.

---

## When grammar cards get created

### 1. User makes a grammar mistake (primary trigger)

The cat detects an error in the user's target-language output, corrects it
warmly, and calls `create_grammar_card`. The JSON template in `back` captures
the rule; `context_sentence` captures the user's actual mistake.

> User: "yo soy cansado hoy"
> Cat: "casi — usa *estar* para estados temporales: 'estoy cansado'." → card:
> - `front`: `ser vs estar — estados temporales`
> - `back`: `{"rule":"ser vs estar","scope":"temporary states","language":"es",...}`
> - `context_sentence`: `"yo soy cansado hoy" → estoy cansado`

### 2. User asks for grammar help explicitly

"I keep mixing up por and para."
Cat explains → calls `create_grammar_card` with a `pattern` template.

### 3. User asks why a line in the show worked a certain way

"Why 'hubiera' and not 'tenía'?"
Cat explains → card created for the construction.

---

## Implementation

### Step 1 — `create_grammar_card` tool

```python
{
    "name": "create_grammar_card",
    "description": "Create a grammar flashcard. The back is a JSON template that drives dynamic quiz generation at review time.",
    "parameters": {
        "card_type": {
            "type": "string",
            "enum": ["conjugation", "pattern", "gender"]
        },
        "front": "Human-readable rule name shown on the card face, e.g. 'pretérito indefinido (-ar)'",
        "back": "JSON string — quiz generation template. Must include: rule, scope, language. For pattern/gender also include native_language.",
        "context_sentence": "The sentence that triggered this card — user's mistake or show line.",
        "language": "ISO 639-1 target language code"
    }
}
```

Handler: `srs_service.find_or_create_card` with `card_type` forwarded.
The `back` field is stored verbatim — it is the JSON template.

### Step 2 — `POST /srs/cards/{id}/generate-quiz` endpoint

```python
async def generate_grammar_quiz(card: SRSCard, user: User) -> dict:
    template = json.loads(card.back)
    prompt = build_quiz_prompt(template, card.card_type)
    response = await llm_service.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        provider="groq",
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    return json.loads(response)
```

Prompts are type-specific. Example for conjugation:
> "Pick a random common Spanish -ar verb (not hablar). Return ONLY valid JSON
> with keys: type, prompt, word, answer (object with persons as keys), example.
> Rule: pretérito indefinido."

### Step 3 — System prompt for the cat

**On mistakes:**
> When the user writes in {{ target_language }} and makes a grammar mistake,
> correct them warmly (one sentence), explain the rule briefly, and call
> `create_grammar_card`. The `back` must be valid JSON with at minimum:
> `rule`, `scope`, `language`. One card per mistake.

**On questions:**
> When the user asks about a grammar rule, explain it, then call
> `create_grammar_card` if it is worth drilling. Use judgement.

### Step 4 — Frontend grammar card rendering

On flip of a grammar card (`card.card_type !== 'vocabulary'`):
1. Call `POST /srs/cards/{id}/generate-quiz` instead of `generate-back`
2. Parse the JSON response
3. Render based on `type`:
   - `conjugation`: show `prompt`, on flip show answer as person→form table
   - `pattern` / `gender`: show `prompt`, on flip show `answer` + `rule` + `example`

The card-type label (small chip) shows `conjugation` / `pattern` / `gender`
so the user knows what kind of drill they're doing.

---

## What stays the same

- **FSRS queue** — grammar cards scheduled alongside vocabulary.
- **Deduplication** — `front` uniqueness per user+language. Cat can't create
  two cards for the same rule.
- **Edit form** — user can correct the stored template if the cat got it wrong.
- **Delete** — works as-is.

---

## What we're NOT doing

- Static back content for grammar cards — always dynamically generated.
- Auto-extraction from SRT — stays vocabulary-only.
- Fill-in-the-blank UI — later.
- Curriculum sequencing — the cat decides what's relevant.
