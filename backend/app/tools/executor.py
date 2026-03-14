import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Cat, _utcnow
from app.services import srs_service, goal_service, cat_service, goal_import_service


class ToolExecutor:
    def __init__(self, db: AsyncSession, plugin_handlers: dict | None = None):
        self.db = db
        self.registry = {
            "update_user_profile": self._update_user_profile,
            "name_cat": self._name_cat,
            "rate_word": self._rate_word,
            "create_vocabulary_card": self._create_vocabulary_card,
            "search_media": self._search_media,
            "create_goal": self._create_goal,
            "load_goal_vocabulary": self._load_goal_vocabulary,
        }
        # Plugin handlers: async fn(user, db, **kwargs) -> dict
        self._plugin_handlers = plugin_handlers or {}

    async def execute(self, tool_calls: list[dict], user: User) -> list[dict]:
        results = []
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            handler = self.registry.get(fn_name)
            plugin_handler = self._plugin_handlers.get(fn_name)
            if handler is not None:
                result = await handler(user, **args)
            elif plugin_handler is not None:
                result = await plugin_handler(user=user, db=self.db, **args)
            else:
                result = {"error": f"Unknown tool: {fn_name}"}
            results.append(
                {
                    "tool_call_id": tc["id"],
                    "role": "tool",
                    "content": json.dumps(result),
                }
            )
        return results

    async def _name_cat(self, user: User, name: str) -> dict:
        cat = await cat_service.get_active_cat(self.db, user)
        if cat is None:
            return {"error": "No active cat yet — set a target language first"}
        cat.name = name
        await self.db.commit()
        await self.db.refresh(cat)
        return {"status": "named", "cat_name": cat.name}

    async def _update_user_profile(self, user: User, **kwargs) -> dict:
        if "name" in kwargs:
            user.name = kwargs["name"]
        if "known_languages" in kwargs:
            user.known_languages = json.dumps(kwargs["known_languages"])
        if "target_language" in kwargs:
            user.target_language = kwargs["target_language"]
        user.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return {
            "status": "updated",
            "name": user.name,
            "target_language": user.target_language,
        }

    async def _rate_word(
        self, user: User, word: str, rating: int, context: str
    ) -> dict:
        card = await srs_service.find_or_create_card(
            self.db,
            user_id=user.id,
            word=word,
            language=user.target_language or "unknown",
            back=context,
            source="chat",
        )
        updated = await srs_service.review_card(
            self.db, card.id, rating, source="chat_agentic"
        )
        return {
            "card_id": updated.id,
            "word": word,
            "rating": rating,
            "next_review": updated.fsrs_due,
            "status": "reviewed",
        }

    async def _create_vocabulary_card(
        self,
        user: User,
        front: str,
        back: str,
        card_type: str = "vocabulary",
        context_sentence: str | None = None,
    ) -> dict:
        card = await srs_service.find_or_create_card(
            self.db,
            user_id=user.id,
            word=front,
            language=user.target_language or "unknown",
            back=back,
            card_type=card_type,
            context_sentence=context_sentence,
            source="chat",
        )
        return {
            "card_id": card.id,
            "front": card.front,
            "back": card.back,
            "status": "created",
        }

    async def _search_media(
        self, user: User, query: str, media_type: str
    ) -> dict:
        # Stub — returns placeholder results
        return {
            "query": query,
            "media_type": media_type,
            "results": [],
            "message": "Media search not yet implemented",
        }

    async def _create_goal(
        self, user: User, title: str, media_type: str | None = None
    ) -> dict:
        goal = await goal_service.create_goal(
            self.db,
            user_id=user.id,
            title=title,
            language=user.target_language or "unknown",
            media_type=media_type,
        )
        return {"goal_id": goal.id, "title": goal.title, "status": "created"}

    async def _load_goal_vocabulary(
        self,
        user: User,
        goal_id: str,
        season: int | None = None,
        episode: int | None = None,
    ) -> dict:
        if not goal_service.subdl_configured():
            return {"error": "Subtitle search is not configured (missing SUBDL_API_KEY)"}
        goal = await goal_service.get_goal(self.db, goal_id)
        if goal is None or goal.user_id != user.id:
            return {"error": f"Goal {goal_id} not found"}
        try:
            result = await goal_import_service.auto_import(
                self.db, goal, season=season, episode=episode
            )
        except ValueError as e:
            return {"error": str(e)}
        return {
            "status": "imported",
            "goal_id": goal_id,
            "subtitle": result.get("subtitle_name", ""),
            "total_words": result["total_words"],
            "new_cards": result["new_cards"],
            "existing_cards": result["existing_cards"],
        }
