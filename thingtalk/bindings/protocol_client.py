from __future__ import annotations
from typing import Protocol, overload


class ProtocolClient(Protocol):
    def read_resource(form: Form):
        pass

    def write_resource(form: Form):
        pass
    
    @overload
    def invoke_resource(form: Form): ...

    @overload
    def invoke_resource(form: Form, content: Content): ...

    def invoke_resource(form: Form, content: Content | None = None):
        if not content:
            return involke_resource(form, None)


