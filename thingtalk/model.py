from tortoise.models import Model
from tortoise import fields


class Thing(Model):
    # Defining `id` field is optional, it will be defined automatically
    # if you haven't done it yourself
    # id = fields.IntField(pk=True)
    uid = fields.CharField(max_length=255, unique=True)
    title = fields.CharField(max_length=255)

    # Defining ``__str__`` is also optional, but gives you pretty
    # represent of model in debugger and interpreter
    def __str__(self):
        return self.name


# class Rule(Model):
#     name = fields.CharField(max_length=255)
#     description = fields.TextField()
