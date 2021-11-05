from __future__ import annotations
from typing import Any, Callable, NoReturn, Optional, Protocol, Union


type DeepPartial<T> = T extends object ? {
    [P in keyof T]?: T[P] extends Array<infer I>
    ? Array<DeepPartial<I>>
    : DeepPartial<T[P]>
} : T;


# Starts the discovery process that will provide ConsumedThing 
#
#  @param filter represents the constraints for discovering Things as key-value pairs
#
def discover(filter?: ThingFilter): ThingDiscovery;

#
# Accepts a ThingDescription and returns a ConsumedThing
#  @param td thing description

async def consume(td: ThingDescription) -> ConsumedThing: ...

# Accepts an init dictionary similar to a ThingDescription.
# It returns a ExposedThing

# @param ptd Partial thing description 

async def produce(init: ExposedThingInit) -> ExposedThing: ...


# Dictionary that represents the constraints for discovering Things as key-value pairs. 
class ThingFilter(Protocol):
    # The method field represents the discovery type that should be used in the discovery process. The possible values are defined by the DiscoveryMethod enumeration that can be extended by string values defined by solutions (with no guarantee of interoperability). 
    # method?: DiscoveryMethod | string; // default value "any", DOMString
        
    # The url field represents additional information for the discovery method, such as the URL of the target entity serving the discovery request, such as a Thing Directory or a Thing.
    url: Optional[str]

    # The query field represents a query string accepted by the implementation, for instance a SPARQL query. 
    query: Optional[str]

    # The fragment field represents a template object used for matching against discovered Things.
    fragment: Optional[object]


# The DiscoveryMethod enumeration represents the discovery type to be used
class DiscoveryMethod(str, Enum):
    # does not restrict
    ANY = "any"
    # for discovering Things defined in the same Servient
    LOCAL = "local"
    # for discovery based on a service provided by a Thing Directory
    DIRECTORY = "directory"
    # for discovering Things in the same/reachable network by using a supported multicast protocol
    MULTICAST = "multicast"


# The ThingDiscovery object is constructed given a filter and provides the properties and methods
# controlling the discovery process. 
class ThingDiscovery(Protocol):
    filter: Optional[ThingFilter]
    active: bool
    done: bool
    error: Optional[Exception]
        
    def start(self) -> None: ...
        
    async def next(self) -> ThingDescription: ...
    
    async def stop(self) -> None: ...



# WoT provides a unified representation for data exchange between Things, standardized in the Wot Things Description specification.
# In this version of the API, Thing Descriptions is expected to be a parsed JSON object.
ThingDescription = import("wot-thing-description-types").ThingDescription;
ExposedThingInit = DeepPartial<ThingDescription>

DataSchemaValue = Union[None, bool, int, str, object, list[DataSchemaValue]]
InteractionInput = Union[ReadableStream, DataSchemaValue]

class InteractionOutput(Protocol):
    data: Optional[ReadableStream]
    dataUsed: bool
    form: Optional[Form]
    schema: Optional[DataSchema]
    async def arrayBuffer(self) -> ArrayBuffer: ...
    async def value(self) -> DataSchemaValue: ...


class Subscription(Protocol):
    active: bool
    async def stop(self, options: Optional[InteractionOptions]) -> None: ...


# The ConsumedThing interface instance represents a client API to operate a Thing.
class ConsumedThing(Protocol):
    ''' Reads a Property value.
        Takes as arguments propertyName and optionally options.
        It returns a Promise that resolves with a Property value represented as an
        InteractionOutput object or rejects on error.
    '''
    async def readProperty(self, propertyName: str, options: Optional[InteractionOptions]) -> InteractionOutput: ...

    '''
         Reads all properties of the Thing with one or multiple requests.
        Takes options as optional argument.
        It returns a Promise that resolves with a PropertyMap object that
        maps keys from Property names to values.
    '''
    async def readAllProperties(self, options: Optional[InteractionOptions]) -> PropertyReadMap: ...

    '''
       Reads multiple Property values with one or multiple requests.
       Takes as arguments propertyNames and optionally options.
       It returns a Promise that resolves with a PropertyMap object that
       maps keys from propertyNames to values
    '''
    async def readMultipleProperties(self, propertyNames: list[str], options: Optional[InteractionOptions]) -> PropertyReadMap: ...

    '''
    Writes a single Property.
    Takes as arguments propertyName, value and optionally options.
    It returns a Promise that resolves on success and rejects on failure.
    '''         
    async def writeProperty(self, propertyName: str, value: InteractionInput, options: Optional[InteractionOptions]) -> None: ...

    '''
        Writes a multiple Property values with one request.
        Takes as arguments properties - as an object with keys being Property names
        and values as Property values - and optionally options.
        It returns a Promise that resolves on success and rejects on failure.
    '''
    async def writeMultipleProperties(self, valueMap: PropertyWriteMap, options: Optional[InteractionOptions]) -> None: ...

    '''
    Makes a request for invoking an Action and return the result.
    Takes as arguments actionName, optionally params and optionally options.
    It returns a Promise that resolves with the result of the Action represented
    as an InteractionOutput object, or rejects with an error.
    '''
    async def invokeAction(self, actionName: str, params: Optional[InteractionInput], options: Optional[InteractionOptions]) -> Union[NoReturn, InteractionOutput]: ...

    '''
    Makes a request for Property value change notifications.
    Takes as arguments propertyName, listener and optionally options.
    It returns a Promise that resolves on success and rejects on failure. 
    '''
    async def observeProperty(self, name: str, listener: WotListener, errorListener: Optional[ErrorListener], options: Optional[InteractionOptions]) -> Subscription: ...

    '''
    Makes a request for subscribing to Event notifications.
    Takes as arguments eventName, listener and optionally options.
    It returns a Promise to signal success or failure.
    '''
    async def subscribeEvent(self, name: str, listener: WotListener, errorListener: Optional[ErrorListener], options: Optional[InteractionOptions]) -> Subscription: ...

    '''
    Returns the the object that represents the Thing Description.
    '''
    def getThingDescription(self) -> ThingDescription: ...


class InteractionOptions(Protocol):
    formIndex: Optional[int]
    uriVariables: Optional[object]
    data: Optional[Any]

PropertyReadMap = dict[str, InteractionOutput]
PropertyWriteMap = dict[str, InteractionInput]

WotListener = Callable[[InteractionOutput], None]
ErrorListener = Callable[[Exception], None]

class InteractionData(Protocol):
    data: Optional[ReadableStream]
    dataUsed: bool
    form: Optional[Form]
    schema: Optional[DataSchema]
    
    async def arrayBuffer(self) -> ArrayBuffer: ...
    async def value(self) -> Any: ...

Form = dict[str, Any]
DataSchema = dict[str, Any]

    
# The ExposedThing interface is the server API to operate the Thing that allows defining request handlers, Property, Action, and Event interactions.
class ExposedThing(Protocol):
    # Start serving external requests for the Thing, so that WoT Interactions using Properties, Actions and Events will be possible.
    async def expose(self) -> None: ...

    # Stop serving external requests for the Thing and destroy the object. Note that eventual unregistering should be done before invoking this method.
    async def destroy(self) -> None: ...

    '''
    Takes name as string argument and handler as argument of type PropertyReadHandler.
    Sets the handler function for reading the specified Property matched by name.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setPropertyReadHandler(self, name: str, handler: PropertyReadHandler) -> ExposedThing: ...

    '''
    Takes name as string argument and handler as argument of type PropertyWriteHandler.
    Sets the handler function for writing the specified Property matched by name.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''         
    def setPropertyWriteHandler(self, name: str, handler: PropertyWriteHandler) -> ExposedThing: ...

    '''
    Takes as arguments name and handler.
    Sets the service handler that defines what to do when a request is received for
    observing the specified Property matched by name.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setPropertyObserveHandler(self, name: str, handler: PropertyReadHandler) -> ExposedThing: ...

    '''
    Takes as arguments name and handler.
    Sets the service handler that defines what to do when a request is received for
    unobserving the specified Property matched by name. 
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setPropertyUnobserveHandler(self, name: str, handler: PropertyReadHandler) -> ExposedThing: ...

    '''
    Takes name as string argument and handler as argument of type ActionHandler.
    Sets the handler function for the specified Action matched by name.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setActionHandler(self, name: str, handler: ActionHandler) -> ExposedThing: ...

    '''
    Takes as arguments name and handler.
    Sets the handler function that defines what to do when a subscription request
    is received for the specified Event matched by name.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setEventSubscribeHandler(self, name: str, handler: EventSubscriptionHandler) -> ExposedThing: ...

    '''
    Takes as arguments name and handler.
    Sets the handler function that defines what to do when the specified Event
    matched by name is unsubscribed from.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setEventUnsubscribeHandler(self, name: str, handler: EventSubscriptionHandler) -> ExposedThing: ...

    '''
    Takes as arguments name and eventHandler.
    Sets the event handler function for the specified Event matched by name.
    Throws on error.
    Returns a reference to the same object for supporting chaining.
    '''
    def setEventHandler(self, name: str, handler: EventListenerHandler) -> ExposedThing: ...

    '''
    Takes as arguments name denoting an Event name and data.
    Triggers emitting the Event with the given data. 
    '''
    def emitEvent(self, name: str, data: InteractionInput) -> None: ...

    '''
    Returns the the object that represents the Thing Description.
    '''
    def getThingDescription(self) -> ThingDescription: ...


PropertyReadHandler = (options?: InteractionOptions) => Promise<InteractionInput>;

PropertyWriteHandler = (value: InteractionOutput, options?: InteractionOptions) => Promise<void>;

ActionHandler = (params: InteractionOutput, options?: InteractionOptions) => Promise<undefined | InteractionInput>;

EventSubscriptionHandler = (options?: InteractionOptions) => Promise<void>;

EventListenerHandler = () => Promise<InteractionInput>;