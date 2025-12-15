from tortoise import fields, models


class User(models.Model):
    id = fields.BigIntField(pk=True)  # Telegram user ID
    username = fields.CharField(max_length=255, null=True)
    full_name = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def __str__(self):
        return self.username or str(self.id)



class Person(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="people")
    name = fields.CharField(max_length=255)

    # AICODE-NOTE: Промпт для анализа заметок по этому человеку.
    # Если не задан, используется дефолтный.
    custom_prompt = fields.TextField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "people"
        unique_together = (
            ("user", "name"),
        )

    def __str__(self):
        return self.name



class PromptTemplate(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="prompt_templates",
    )
    name = fields.CharField(max_length=255)
    text = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prompt_templates"
        unique_together = (
            ("user", "name"),
        )

    def __str__(self):
        return self.name



class MeetingNote(models.Model):
    id = fields.UUIDField(pk=True)
    person = fields.ForeignKeyField("models.Person", related_name="notes")
    raw_text = fields.TextField()

    # Результат анализа AI (JSON)
    # Структура: { "mood": 5, "summary": "...", "action_items": [], "tags": [] }
    ai_summary = fields.JSONField(null=True)

    # Опциональные поля оставляем как "кэш" или для быстрого доступа,
    # хотя они могут дублироваться в JSON
    stress_level = fields.IntField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "meeting_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.person_id} at {self.created_at}"
