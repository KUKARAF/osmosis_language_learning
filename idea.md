language learning app called osmosis (learning through osmosis) that focuses on language learning techniques that allow the users to learn through things they like to do anyways. the core of the app should be built around spaced repetion via py-fsrs that stores users words, grammar forms and other important language learning topics and has a llm mark each topic as seen and mark it as easy diffucult etc as the user simply interacts with our tamagocho like character a well traveled cat that chats with the user for food scraps.


## UI
we want a non standard interface that doesnt focus on forms and buttons e.g. signup forms (the bare minimum is ok) instead we want the user to feel like he just stumbled on a cat that offers him/her a deal that can not be refused. Meaning the main interface should be via chat (with the llm taking agentic actions on the users behalf) and or showing the user form elements that are rendered inline with the chat.


## first interaction
in the getting to know the user stage we should ask hin her about important reasons for his/her learning goals the language the user is trying to learn, any other languages the users speaks already (can we used to explain stuff with examples from already known languages) name etc and the llm should agenticly store that under the user class (can be changed later in the settings)

#### Elements:
- Main chat window
	- the main way to interact with the application
	- streaming responses are a must for natural conversation feel
- Flashcard section
	- dedicated review area where users see a flashcard and self-select easy/hard/etc
	- option to ask the cat about a card clippy-style ("hey cat, what does this mean?")
	- the SRS also works passively in chat: when the user correctly uses a word the cat notices and notes it down e.g. "oh you seem to have used dog correctly *writes something down in a dirty old notebook*"
- lessons
	- glorified wrapper for the spaced repetion system
- goals
	- things the user wants to get to
		- e.g. watch "sorda" movie in spanish
		- this should search the internet and import the srt into the spaced repetition system and the lessons
		- a notification should be sent once the user is ready for the goal
	- progress visibility is focused on goals, specifically movies/series for now

## Grooming & Streaks
the user has to groom the cat at least once a day (a tamagotchi-style button press) to maintain a streak. grooming is separate from feeding — feeding is buying more tokens with money (see payment system).

## Cat states
- **happy**: well fed, chatty
- **hangry**: not groomed for 1 day. grumpy, short responses, complains
- **hospitalized**: not groomed for 3 days. gruesome scenario like "your cat tried to eat a fish shaped plastic toy". user needs to nurse it back to health
- death is too permanent. the cat always recovers but the scenarios get more dramatic the longer you neglect it

## Cat visual representation
placeholder / emoji-based for v0.1.xx. revisit with proper art later.

## Multiple languages
each target language gets its own unique cat. users switch between cats in their profile.

## Error correction & SRS mapping
the cat corrects the user inline in chat every time the user says something incorrectly or makes a mistake. the prompt should encourage corrections that dont disturb the flow of conversation (e.g. naturally weaving the correct form into the cat's response rather than stopping to lecture).

the LLM decides py-fsrs ratings agentically during conversation:
- **EASY**: word/form used correctly in a sentence without errors
- **GOOD/MEDIUM**: small errors but the right idea, cat gently models the correct form
- **HARD/AGAIN**: used incorrectly, cat corrects explicitly and notes it down

## Languages
supported languages for now: Russian, Polish, Spanish, English, German, Portuguese (and anything else that would be easy to add).

## Chat language behavior
the cat finds out what language the user wants to learn and what languages they already know (stores this agentically in user profile). the cat speaks in the target language by default, only falling back to known languages to explain grammar or when the user is clearly lost. fallback decreases as the user progresses.

## Content approach
no initial content seeding needed. the user chitchats with the cat but the focus should lean towards movies, series and other media so we can prepare the user for consuming media in their target language.

## Cat personality & prompt management
see [soul.md](soul.md) for the cat's personality, voice, and behavior spec. all prompts are managed via jinja templates.

## LLM providers
- **OpenRouter**: general chat, complex reasoning, agentic actions
- **Groq**: quick interactions where low latency matters

## Rate limiting
all users have a tokens/day limit (not visible to the user). when exceeded the cat won't talk anymore and becomes sleepy ("*yawns* i think i need a nap... come back tomorrow").

## Payment system

payment system should focus on healthcare for the cat and catfood. after a few messages the user chooses between 2 paths:

### Path 1: Stay in the city (individual / capitalist / prepaid)
the user buys token packs upfront — framed as "catfood" and "vet visits":
- **catfood (feeding)**: bundles of tokens the user buys in advance with real money. each chat message, flashcard review, etc. consumes tokens from the pack. when the pack runs out, the cat is hungry and won't talk until the user buys more food.
- **vet visits**: hospitalization events (from neglecting grooming) cost a one-time token fee to resolve.
- **BYOK option**: power users can bring their own API keys (OpenRouter/Groq) and only pay platform fee.
- the user always sees this in cat terms ("buy a can of tuna", "premium salmon feast") never in raw token numbers.
- payment provider: whatever is easiest to integrate first (Stripe likely), can add local providers later.

### Path 2: Move to the hippie commune (community / communism / subscription)
monthly subscription where the price decays as more people join the commune.

**pricing formula:**
```
price_per_user = max(1 PLN, commune_avg_llm_cost + premium * decay^(num_members - 1))
```

- `commune_avg_llm_cost`: last month's total commune LLM spend / num_members — the honest cost floor that never decays
- `premium * decay^(n-1)`: markup that shrinks as people join — this is the viral incentive (e.g. premium=25 PLN, decay=0.88)
- floor: 1 PLN / user / month minimum

**example with premium=25, decay=0.88, avg_llm_cost=5 PLN:**

| Members | Price/user | Total revenue | Total LLM cost | Margin |
|---------|------------|---------------|-----------------|--------|
| 1       | 30.00      | 30            | 5               | 25.00  |
| 5       | 20.01      | 100           | 25              | 75.00  |
| 10      | 13.15      | 131           | 50              | 81.50  |
| 20      | 7.40       | 148           | 100             | 48.00  |
| 30      | 5.71       | 171           | 150             | 21.30  |
| 50+     | ~5.00      | 250           | 250             | ~0     |

**safety mechanisms:**
1. price never drops below `max(1 PLN, avg_llm_cost)` — never sell below cost
2. per-user tokens/day limit — cat gets sleepy, keeps avg_llm_cost bounded
3. commune budget ceiling — if total LLM spend exceeds `total_revenue * threshold`, the whole commune's cat gets tired earlier
4. LLM cost uses rolling 3-month average to smooth spikes and prevent join-burn-leave abuse

**future features (not v0.1):**
- leaderboards and bets (who has the fatter cat)
- commune naming / identity
- invite bonuses (extra tokens for a week for both inviter and invitee)
- "your commune saved X PLN this month because Y joined" notifications

see [commune_payment.md](commune_payment.md) for extended brainstorm.

## Authentication
oidc pkce to authentik at auth.osmosis.page

## Versioning
MAJOR_RELEASE.minor_release.SHORTSHA where major and minor are arbitrarily decided and SHORTSHA is applied on every commit.

## Architecture
### backend:
fastapi + sqlite (we will migrate to postgres later as needed) available at /api
### frontend
super simple static html frontend that interacts with backend under /api
### mobile application
apk built using rust

see [architecture.md](architecture.md) for data model and detailed architecture.

## Deployment
- hosted on server, built and pushed to GHCR via GitHub Actions (Docker)
- deployed using docker compose
- `docker-compose.yaml` (prod) and `dev.docker-compose.yaml` (dev)
- secrets stored in `.env`
- public details like the URL (app.osmosis.page) hardcoded in docker-compose

## Notifications
internal notification stack per user stored in sqlite, shown in the frontend. later we want to use Google's notification service for the Android app (see [todo.md](todo.md)).
