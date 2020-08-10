"""An observable, settable value interface."""

from pyee import AsyncIOEventEmitter as EventEmitter


class Value(EventEmitter):
    """
    A property value.
    This is used for communicating between the Thing representation and the
    actual physical thing implementation.
    Notifies all observers when the underlying value changes through an
    external update (command to turn the light off) or if the underlying sensor
    reports a new value.
    """

    def __init__(self, initial_value, value_forwarder=None):
        """
        Initialize the object.
        initial_value -- the initial value
        value_forwarder -- the method that updates the actual value on the
                           thing
        """
        EventEmitter.__init__(self)
        self.last_value = initial_value
        self.value_forwarder = value_forwarder

    async def set(self, value, with_action=True):
        """
        Set a new value for this thing.
        value -- value to set
        with_action -- do property action
        """
        if self.value_forwarder is not None:
            self.value_forwarder(value)

        await self.notify_of_external_update(value, with_action=with_action)

    async def get(self):
        """Return the last known value from the underlying thing."""
        return self.last_value

    async def notify_of_external_update(self, value, with_action=True):
        """
        Notify observers of a new value.
        value -- new value
        """
        if value is not None:
            self.last_value = value
            if with_action:
                self.emit('update', value)
            else:
                self.emit('sync', value)
