from __future__ import annotations

import json
from logging import warning
from typing import TYPE_CHECKING, Any, Optional

from loguru import logger 
import * as WoT from "wot-typescript-definitions";

import { Subject } from "rxjs/Subject";

import .td_tools.thing_description as TD

if TYPE_CHECKING:
    from servient import Servient

import Helpers from "./helpers";
import { InteractionOutput } from "./interaction-output";
import { Readable } from "stream";
import ProtocolHelpers from "./protocol-helpers";
import { ReadableStream as PolyfillStream } from "web-streams-polyfill/ponyfill/es2018";
import { Content } from "./core";

class ExposedThing extends TD.Thing implements WoT.ExposedThing:
    security: list[str]
    securityDefinitions: dict[str, TD.SecurityType]

    id: str
    title: str
    base: str
    forms: list[TD.Form]

    # A map of interactable Thing Properties with read()/write()/subscribe() functions
    properties: dict[str, TD.ThingProperty] 

    # A map of interactable Thing Actions with invoke() function
    actions: dict[str, TD.ThingAction] 

    # A map of interactable Thing Events with emit() function
    events: dict[str, TD.ThingEvent]

    def __init__(self, servient: Servient, thingModel: WoT.ExposedThingInit = {}):
        super().__init__()

        self.servient = servient
        
        self.subjectTD = Subject<WoT.ThingDescription>();

        # Deep clone the Thing Model
        # without functions or methods
        clonedModel = json.loads(json.dumps(thingModel));
        Object.assign(this, clonedModel);

        # unset "@type":"tm:ThingModel" ?
        # see https://github.com/eclipse/thingweb.node-wot/issues/426
        /* if (this["@type"]) {
            if (typeof this["@type"] === 'string' && this["@type"] === "tm:ThingModel") {
                delete this["@type"];
            } else if (Array.isArray(this["@type"])) {
                let arr: Array<any> = this["@type"];
                for (var i = 0; i < arr.length; i++) {
                    if (arr[i] === "tm:ThingModel") {
                        arr.splice(i, 1);
                        i--;
                    }
                }
            }
        } */
        # set default language
        self.addDefaultLanguage(this);
        # extend interactions
        self.extendInteractions();
    }

    # Note: copy from td-parser.ts
    def addDefaultLanguage(thing: ExposedThing) -> None:
        # add @language : "en" if no @language set
        if isinstance(thing["@context"], list):
            arrayContext = thing["@context"]
            languageSet = False
            for arrayEntry in arrayContext:
                if isinstance(arrayEntry, "object"):
                    if (arrayEntry["@language"] !== undefined):
                        languageSet = True

            if not languageSet:
                arrayContext.append({
                    "@language": TD.DEFAULT_CONTEXT_LANGUAGE,
                })

    def extendInteractions(self) -> None:
        for propertyName in self.properties:
            newProp = Helpers.extend(self.properties[propertyName], ExposedThingProperty(propertyName, this));
            self.properties[propertyName] = newProp;

        for actionName in self.actions:
            newAction = Helpers.extend(self.actions[actionName], ExposedThingAction(actionName, this));
            self.actions[actionName] = newAction
        
        for eventName in self.events:
            newEvent = Helpers.extend(self.events[eventName], ExposedThingEvent(eventName, this))
            self.events[eventName] = newEvent

    def getThingDescription(self) -> WoT.ThingDescription:
        return json.loads(TD.serializeTD(self))

    def emitEvent(self, name: str, data: Any) -> None:
        if self.events[name]:
            es: EventState = self.events[name].getState();
            for listener in es.listeners:
                listener.call(this, data);
        else:
            # NotFoundError
            raise Exception("NotFoundError for event '" + name + "'")

    # @inheritDoc
    def expose(self):
        logger.debug(f'ExposedThing {self.title} exposing all Interactions and TD')

        # let servient forward exposure to the servers
        self.servient.expose(self)
        # inform TD observers
        self.subjectTD.next(self.getThingDescription())

    # @inheritDoc
    def destroy(self):
        logger.debug(f'ExposedThing {self.title} destroying the thing and its interactions')

        self.servient.destroyThing(self.id)
        # inform TD observers that thing is gone
        self.subjectTD.next(None)

    # @inheritDoc
    def setPropertyReadHandler(self, propertyName: str, handler: WoT.PropertyReadHandler) -> WoT.ExposedThing:
        logger.debug(
            f'ExposedThing {self.title} setting read handler for {propertyName}'
        )

        if self.properties[propertyName]:
            # setting read handler for writeOnly not allowed
            if self.properties[propertyName].writeOnly:
                raise Exception(
                    f'ExposedThing {self.title} cannot set read handler for property {propertyName} due to writeOnly flag'
                )
            else:
                # in case of function instead of lambda, the handler is bound to a scope shared with the writeHandler in PropertyState
                ps: PropertyState = self.properties[propertyName].getState()
                ps.readHandler = handler.bind(ps.scope);
        else:
            raise Exception(f'ExposedThing {self.title} has no Property {propertyName}')

        return self


    def setPropertyWriteHandler(self, propertyName: str, handler: WoT.PropertyWriteHandler) -> WoT.ExposedThing:
        logger.debug(
            f'ExposedThing {self.title} setting write handler for {propertyName}'
        )
        if self.properties[propertyName]:
            # Note: setting write handler allowed for readOnly also (see https://github.com/eclipse/thingweb.node-wot/issues/165)
            # The reason is that it may make sense to define its own "reject"
            # in case of function instead of lambda, the handler is bound to a scope shared with the readHandler in PropertyState
            ps: PropertyState = self.properties[propertyName].getState()
            ps.writeHandler = handler.bind(ps.scope)
        else:
            raise Exception(f'ExposedThing {self.title} has no Property {propertyName}')

        return self


    def setPropertyObserveHandler(self, name: str, handler: WoT.PropertyReadHandler) -> WoT.ExposedThing:
        raise Exception("setPropertyObserveHandler not supported")

    def setPropertyUnobserveHandler(self, name: str, handler: WoT.PropertyReadHandler) -> WoT.ExposedThing:
        raise Exception("setPropertyUnobserveHandler not supported")

    def setActionHandler(self, actionName: str, handler: WoT.ActionHandler) -> WoT.ExposedThing:
        logger.debug(
            f'ExposedThing {self.title} setting action Handler for {actionName}'
        )

        if self.actions[actionName]:
            # in case of function instead of lambda, the handler is bound to a clean scope of the ActionState
            _as: ActionState = self.actions[actionName].getState()
            _as.handler = handler.bind(_as.scope)
        else:
            raise Exception(f'ExposedThing {self.title} has no Action {actionName}')

        return self

    def setEventSubscribeHandler(self, name: str, handler: WoT.EventSubscriptionHandler) -> WoT.ExposedThing:
        raise Exception("setEventSubscribeHandler not supported")

    def setEventUnsubscribeHandler(self, name: str, handler: WoT.EventSubscriptionHandler) -> WoT.ExposedThing:
        raise Exception("setEventUnsubscribeHandler not supported")


    def setEventHandler(self, name: str, handler: WoT.EventListenerHandler) -> WoT.ExposedThing:
        raise Exception("setEventHandler not supported")

    async def readProperty(self, propertyName: str, options: Optional[WoT.InteractionOptions]) -> InteractionOutput:
        if self.properties[propertyName]:
            # writeOnly check skipped so far, see https://github.com/eclipse/thingweb.node-wot/issues/333#issuecomment-724583234
            # if(this.properties[propertyName].writeOnly && this.properties[propertyName].writeOnly === true) {
            #    reject(new Error(`ExposedThing '${this.title}', property '${propertyName}' is writeOnly`));

            ps: PropertyState = self.properties[propertyName].getState();
            # call read handler (if any)
            if ps.readHandler:
                logger.debug(
                    f'ExposedThing {self.title} calls registered readHandler for Property {propertyName}'
                )
                customValue = ps.readHandler(options)
                body = ExposedThing.interactionInputToReadable(customValue)
                c: Content = { body: body, type: "application/json" }
                return InteractionOutput(c, undefined, self.properties[propertyName])
            else:
                logger.debug(
                    f'ExposedThing {self.title} gets internal value {ps.value} for Property {propertyName}'
                )
                body = ExposedThing.interactionInputToReadable(ps.value);
                return InteractionOutput(
                    { body, type: "application/json" },
                    undefined,
                    self.properties[propertyName]
                )
        else:
            raise Exception(f'ExposedThing {self.title}, no property found for {propertyName}')

    async _readProperties(self, propertyNames: list[str], options: Optional[WoT.InteractionOptions]) -> WoT.PropertyReadMap:
        # collect all single promises into array
        promises: Promise<InteractionOutput>[] = [];
        for (const propertyName of propertyNames) {
            promises.push(this.readProperty(propertyName, options));
        # wait for all promises to succeed and create response
        output = new Map<string, WoT.InteractionOutput>();
            Promise.all(promises)
                .then((result) => {
                    let index = 0;
                    for (const propertyName of propertyNames) {
                        output.set(propertyName, result[index]);
                        index++;
                    }
                    resolve(output);
                })
                .catch((err) => {
                    reject(
                        new Error(
                            `ConsumedThing '${this.title}', failed to read properties: ${propertyNames}.\n Error: ${err}`
                        )
                    );
                });
        });
    }

    async def readAllProperties(self, options: Optional[WoT.InteractionOptions]) -> WoT.PropertyReadMap:
        propertyNames: list[str] = []
        for propertyName in self.properties:
            propertyNames.append(propertyName)
        
        return await self._readProperties(propertyNames, options)

    async def readMultipleProperties(self, propertyNames: list[str], options: Optional[WoT.InteractionOptions]) -> WoT.PropertyReadMap:
        return self._readProperties(propertyNames, options)

    async def writeProperty(self, propertyName: str, value: WoT.InteractionInput, options: Optional[WoT.InteractionOptions]) -> None:
        # TODO: to be removed next api does not allow an ExposedThing to be also a ConsumeThing
        if self.properties[propertyName]:
            # readOnly check skipped so far, see https://github.com/eclipse/thingweb.node-wot/issues/333#issuecomment-724583234
            # if (this.properties[propertyName].readOnly && this.properties[propertyName].readOnly === true) {
            #    reject(new Error(`ExposedThing '${this.title}', property '${propertyName}' is readOnly`));

            ps: PropertyState = self.properties[propertyName].getState()

            # call write handler (if any)
            if ps.writeHandler:
                body = ExposedThing.interactionInputToReadable(value);
                content = { body: body, type: "application/json" };
                # be generous when no promise is returned
                promiseOrValueOrNil = ps.writeHandler(
                    InteractionOutput(content, {}, self.properties[propertyName]),
                    options
                )
                if promiseOrValueOrNil:
                    if callable(promiseOrValueOrNil.then):
                        try:
                            # promiseOrValueOrNil
                            #         .then((customValue) => {
                            logger.debug(
                                f'ExposedThing {self.title} write handler for Property {propertyName} sets custom value {customValue}'
                            )
                            # notify state change
                            # FIXME object comparison
                            if ps.value != value:
                                for listener in ps.listeners:
                                    listener.call(value)
                        except Exception as e:
                            logger.warning(
                                f'ExposedThing {self.title} write handler for Property {propertyName} rejected the write with error {e}'
                            )
                    else:
                        logger.warning(
                            f'ExposedThing {self.title} write handler for Property {propertyName} does not return promise'
                        )
                        if ps.value != promiseOrValueOrNil:
                            for listener in ps.listeners:
                                listener.call(promiseOrValueOrNil)
                else:
                    logger.warning(
                        f'ExposedThing {self.title} write handler for Property {propertyName} does not return custom value, using direct value {value}'
                    )
                    if ps.value != value:
                        for listener in ps.listeners:
                            listener.call(value)
            else:
                logger.debug(
                    f'ExposedThing {self.title} directly sets Property {propertyName} to value {value}'
                )
                # notify state change
                if ps.value != value:
                    for listener in ps.listeners:
                        listener.call(value)
        else:
            raise Exception(f'ExposedThing {self.title}, no property found for {propertyName}')

    async def writeMultipleProperties(self, valueMap: WoT.PropertyWriteMap, options: Optional[WoT.InteractionOptions]) -> None:
        # collect all single promises into array
        promises: Promise<void>[] = [];
        for (const propertyName in valueMap) {
                promises.push(this.writeProperty(propertyName, valueMap.get(propertyName), options));
            }
            // wait for all promises to succeed and create response
            Promise.all(promises)
                .then((result) => {
                    resolve();
                })
                .catch((err) => {
                    reject(
                        new Error(`ExposedThing '${this.title}', failed to write multiple properties. ${err.message}`)
                    );
                });
        });
    }

    async def invokeAction(
        self,
        actionName: str,
        parameter: Optional[WoT.InteractionInput],
        options: Optional[WoT.InteractionOptions]
    ) -> InteractionOutput:
        if self.actions[actionName]:
            logger.debug(f'ExposedThing {self.title} has Action state of {actionName}')

            _as: ActionState = self.actions[actionName].getState()
            if _as.handler:
                logger.debug(
                    f'ExposedThing {self.title} calls registered handler for Action {actionName}'
                )
                if parameter:
                    bodyInput = ExposedThing.interactionInputToReadable(parameter)

                cInput: Content = { body: bodyInput, type: "application/json" }
                result = await _as.handler(
                    InteractionOutput(cInput, undefined, self.actions[actionName].input),
                    options
                )

                if result:
                    bodyOutput = ExposedThing.interactionInputToReadable(result)

                cOutput: Content = { body: bodyOutput, type: "application/json" }
                return InteractionOutput(cOutput, undefined, self.actions[actionName].output)
            else:
                raise Exception(f'ExposedThing {self.title} has no handler for Action {actionName}')
        else:
            raise Exception(f'ExposedThing {self.title}, no action found for {actionName}')

    def observeProperty(self, name: str, listener: WoT.WotListener, options: Optional[WoT.InteractionOptions]) -> None:
        if self.properties[name]:
            ps: PropertyState = self.properties[name].getState()
            # let next = listener;
            # let error = null;
            # let complete = null;
            # let sub: Subject<Content> = this.properties[name].getState().subject;
            # sub.asObservable().subscribe(next, error, complete);
            ps.listeners.append(listener)
            logger.debug(f'ExposedThing {self.title} subscribes to property {name}')
        else:
            raise Exception(f'ExposedThing {self.title}, no property found for {name}')

    async def unobserveProperty(self, name: str) -> None:
        if self.properties[name]:
            # let sub: Subject<Content> = this.properties[name].getState().subject;
            # sub.unsubscribe();  // XXX causes loop issue (see browser counter example)
            logger.debug(
                f'ExposedThing {self.title} unsubscribes from property {name}'
            )
        else:
            raise Exception(f'ExposedThing {self.title}, no property found for {name}')

    async def subscribeEvent(self, name: str, listener: WoT.WotListener, options: Optional[WoT.InteractionOptions]) -> None:
        if self.events[name]:
            es: EventState = self.events[name].getState()
            # let next = listener;
            # let error = null;
            # let complete = null;
            # let sub: Subject<any> = this.events[name].getState().subject;
            # sub.asObservable().subscribe(next, error, complete);
            es.listeners.push(listener)
            # es.subject.asObservable().subscribe(listener, null, null);
            logger.debug(f'ExposedThing {self.title} subscribes to event {name}')
        else:
            raise Exception(f'ExposedThing {self.title}, no event found for {name}')

    async def unsubscribeEvent(self, name: str) -> None:
        if self.events[name]:
            # let sub: Subject<any> = this.events[name].getState().subject;
            # sub.unsubscribe(); // XXX causes loop issue (see browser counter example)
            logger.debug(f'ExposedThing {self.title} unsubscribes from event {name}')
        else:
            raise Exception(f'ExposedThing {self.title}, no event found for {name}')

    def interactionInputToReadable(self, input: WoT.InteractionInput) -> Readable:
        if ReadableStream and isinstance(input, ReadableStream):
            body = ProtocolHelpers.toNodeStream(input)
        elif isinstance(input, PolyfillStream):
            body = ProtocolHelpers.toNodeStream(input)
        else:
            body = Readable.from(Buffer.from(input.toString(), "utf-8"))
        
        return body


class PropertyState {
    public value: WoT.DataSchemaValue;
    // public subject: Subject<Content>;
    public scope: unknown;

    public readHandler: WoT.PropertyReadHandler;
    public writeHandler: WoT.PropertyWriteHandler;

    listeners: WoT.WotListener[];

    constructor(value: WoT.DataSchemaValue = null) {
        this.value = value;
        this.listeners = [];
        // this.subject = new Subject<Content>();
        this.scope = {};
        this.writeHandler = null;
        this.readHandler = null;
    }
}

class ActionState {
    public scope: unknown;
    public handler: WoT.ActionHandler;

    constructor() {
        this.scope = {};
        this.handler = null;
    }
}

class EventState {
    // public subject: Subject<any>;
    listeners: WoT.WotListener[];

    constructor() {
        // this.subject = new Subject<any>();
        this.listeners = [];
    }
}
class ExposedThingProperty extends TD.ThingProperty implements TD.ThingProperty, TD.BaseSchema {
    // functions for wrapping internal state
    getName: () => string;
    getThing: () => ExposedThing;
    getState: () => PropertyState;

    constructor(name: string, thing: ExposedThing) {
        super();

        // wrap internal state into functions to not be stringified in TD
        this.getName = () => {
            return name;
        };
        this.getThing = () => {
            return thing;
        };
        this.getState = new (class {
            state: PropertyState = new PropertyState();
            getInternalState = () => {
                return this.state;
            };
        })().getInternalState;

        // apply defaults
        this.readOnly = false;
        this.writeOnly = false;
        this.observable = false;
    }
}

class ExposedThingAction extends TD.ThingAction implements TD.ThingAction {
    // functions for wrapping internal state
    getName: () => string;
    getThing: () => ExposedThing;
    getState: () => ActionState;

    constructor(name: string, thing: ExposedThing) {
        super();

        // wrap internal state into functions to not be stringified
        this.getName = () => {
            return name;
        };
        this.getThing = () => {
            return thing;
        };
        this.getState = new (class {
            state: ActionState = new ActionState();
            getInternalState = () => {
                return this.state;
            };
        })().getInternalState;
    }
}

class ExposedThingEvent extends TD.ThingEvent implements TD.ThingEvent {
    // functions for wrapping internal state
    getName: () => string;
    getThing: () => ExposedThing;
    getState: () => EventState;

    constructor(name: string, thing: ExposedThing) {
        super();

        // wrap internal state into functions to not be stringified
        this.getName = () => {
            return name;
        };
        this.getThing = () => {
            return thing;
        };
        this.getState = new (class {
            state: EventState = new EventState();
            getInternalState = () => {
                return this.state;
            };
        })().getInternalState;
    }
}