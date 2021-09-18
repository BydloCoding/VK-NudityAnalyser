from typing import Iterable


class SetExtension(set):
    def __iadd__(self, other: Iterable):
        for element in other:
            self.add(element)
        return self
    def addAll(self, other):
        return self.__iadd__(other)