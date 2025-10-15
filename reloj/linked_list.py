"""Doubly circular linked list primitive used by the chronograph engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


@dataclass
class Node(Generic[T]):
    """Node in a doubly circular linked list."""

    value: T
    next: Optional["Node[T]"] = None
    prev: Optional["Node[T]"] = None


class DoublyCircularLinkedList(Generic[T]):
    """Minimal doubly circular linked list with an addressable current node."""

    def __init__(self, values: Optional[Iterable[T]] = None) -> None:
        self._head: Optional[Node[T]] = None
        self._current: Optional[Node[T]] = None
        self._size = 0
        if values is not None:
            for value in values:
                self.append(value)
            self._current = self._head

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        if self._head is None:
            return iter(())
        node = self._head
        values: list[T] = []
        for _ in range(self._size):
            values.append(node.value)
            assert node.next is not None  # circular invariant
            node = node.next
        return iter(values)

    @property
    def current_node(self) -> Node[T]:
        if self._current is None:
            raise ValueError("The list is empty.")
        return self._current

    @property
    def current_value(self) -> T:
        return self.current_node.value

    def set_current(self, node: Node[T]) -> None:
        """Set the current pointer to an existing node."""
        if self._head is None:
            raise ValueError("The list is empty.")
        # Validate membership by traversing at most size nodes.
        walker = self._head
        for _ in range(self._size):
            if walker is node:
                self._current = node
                return
            assert walker.next is not None
            walker = walker.next
        raise ValueError("The provided node is not part of this list.")

    def append(self, value: T) -> Node[T]:
        """Add a new value to the ring and return its node."""
        node = Node(value=value)
        if self._head is None:
            node.next = node.prev = node
            self._head = self._current = node
        else:
            assert self._head.prev is not None
            tail = self._head.prev
            tail.next = node
            node.prev = tail
            node.next = self._head
            self._head.prev = node
        self._size += 1
        return node

    def step_forward(self, steps: int = 1) -> Node[T]:
        """Advance the current pointer clockwise on the ring."""
        if self._current is None:
            raise ValueError("The list is empty.")
        if self._size == 0:
            raise ValueError("The list is empty.")
        normalized = steps % self._size
        node = self._current
        for _ in range(normalized):
            assert node.next is not None
            node = node.next
        self._current = node
        return node

    def step_backward(self, steps: int = 1) -> Node[T]:
        """Move the current pointer counter-clockwise on the ring."""
        if self._current is None:
            raise ValueError("The list is empty.")
        if self._size == 0:
            raise ValueError("The list is empty.")
        normalized = steps % self._size
        node = self._current
        for _ in range(normalized):
            assert node.prev is not None
            node = node.prev
        self._current = node
        return node

    def find(self, predicate: Callable[[T], bool]) -> Optional[Node[T]]:
        """Return the first node matching predicate without altering current."""
        if self._head is None:
            return None
        node = self._head
        for _ in range(self._size):
            if predicate(node.value):
                return node
            assert node.next is not None
            node = node.next
        return None

    def is_empty(self) -> bool:
        return self._size == 0
