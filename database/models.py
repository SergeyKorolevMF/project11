from tortoise import fields, models
import uuid

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
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "people"
        unique_together = (
            ("user", "name"),
        )  # Чтобы не создавать дубликатов имен у одного менеджера

    def __str__(self):
        return self.name

class MeetingNote(models.Model):
    id = fields.UUIDField(pk=True)
    person = fields.ForeignKeyField("models.Person", related_name="notes")
    raw_text = fields.TextField()
    
    # Опциональные поля (аналитика)
    stress_level = fields.IntField(null=True)
    rat_of_week = fields.TextField(null=True)
    shark_of_week = fields.TextField(null=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "meeting_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.person_id} at {self.created_at}"
