from __future__ import annotations
from typing import TYPE_CHECKING

from loguru import logger

import * as WoT from "wot-typescript-definitions";
import * as TD from "@node-wot/td-tools";
if TYPE_CHECKING:
    from .servient import Servient
from .exposed_thing import ExposedThing
from .consumed_thing import ConsumedThing
import Helpers from "./helpers";

class WoTImpl:
    srv: Servient
    DiscoveryMethod: typeof WoT.DiscoveryMethod
    
    def __init__(self, srv: Servient) -> None:
        self.srv = srv

    def discover(self, filter?: WoT.ThingFilter) -> WoT.ThingDiscovery:
        return new ThingDiscoveryImpl(filter)

    def consume(self, td: WoT.ThingDescription):
        return new Promise<WoT.ConsumedThing>((resolve, reject) => {
            try {
                const thing = TD.parseTD(JSON.stringify(td), true);
                const newThing: ConsumedThing = new ConsumedThing(this.srv, thing);

                logger.debug(
                    f'WoTImpl consuming TD {
                        newThing.id ? "'" + newThing.id + "'" : "without id"
                    } to instantiate ConsumedThing {newThing.title}'
                );
                resolve(newThing);
            } catch (err) {
                reject(new Error("Cannot consume TD because " + err.message));
            }
        });
    }

    '''
     * create a new Thing
     *
     * @param title title/identifier of the thing to be created
     *'''
    def produce(init: WoT.ExposedThingInit): Promise<WoT.ExposedThing> {
        return new Promise<WoT.ExposedThing>((resolve, reject) => {
            try {
                const validated = Helpers.validateExposedThingInit(init);

                if (!validated.valid) {
                    throw new Error("Thing Description JSON schema validation failed:\n" + validated.errors);
                }

                const newThing = new ExposedThing(this.srv, init);

                console.debug("[core/servient]", `WoTImpl producing new ExposedThing '${newThing.title}'`);

                if (this.srv.addThing(newThing)) {
                    resolve(newThing);
                } else {
                    throw new Error("Thing already exists: " + newThing.title);
                }
            } catch (err) {
                reject(new Error("Cannot produce ExposedThing because " + err.message));
            }
        });
    }
}

export enum DiscoveryMethod {
    /** does not provide any restriction */
    "any",
    /** for discovering Things defined in the same device */
    "local",
    /** for discovery based on a service provided by a directory or repository of Things  */
    "directory",
    /** for discovering Things in the device's network by using a supported multicast protocol  */
    "multicast",
}

class ThingDiscoveryImpl implements WoT.ThingDiscovery {
    filter?: WoT.ThingFilter;
    active: boolean;
    done: boolean;
    error?: Error;
    constructor(filter?: WoT.ThingFilter) {
        this.filter = filter || null;
        this.active = false;
        this.done = false;
        this.error = new Error("not implemented");
    }

    start(): void {
        this.active = true;
    }

    next(): Promise<WoT.ThingDescription> {
        return new Promise<WoT.ThingDescription>((resolve, reject) => {
            reject(this.error); // not implemented
        });
    }

    stop(): void {
        this.active = false;
        this.done = false;
    }
}

/** Instantiation of the WoT.DataType declaration */
export enum DataType {
    boolean = "boolean",
    number = "number",
    integer = "integer",
    string = "string",
    object = "object",
    array = "array",
    null = "null",
}