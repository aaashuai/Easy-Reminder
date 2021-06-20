from typing import Any, Text, overload


class BaseExtractor:
    @overload
    def parse(self, text: Text) -> Any:
        ...

    @overload
    def parse(self, text: Text, *args: Any) -> Any:
        ...

    def parse(self, text: Text, *args: Any) -> Any:
        raise NotImplementedError
