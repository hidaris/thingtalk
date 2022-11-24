"""This module provides a high-level interface for creating a Web Thing."""

# flake8: noqa
from .models.action import Action
from .models.event import Event
from .models.property import Property
from .app import app
from .models.containers import SingleThing, MultipleThings
from .models.thing import Thing
# from .domains.iot import Device
from .models.value import Value
