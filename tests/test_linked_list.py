from reloj.linked_list import DoublyCircularLinkedList


def test_ring_steps_forward_and_backward() -> None:
    ring = DoublyCircularLinkedList(range(4))

    assert ring.current_value == 0
    ring.step_forward()
    assert ring.current_value == 1

    ring.step_forward(3)
    assert ring.current_value == 0

    ring.step_backward()
    assert ring.current_value == 3

    ring.step_backward(2)
    assert ring.current_value == 1
