class MockSM16relind:
    def __init__(self, stack):
        self.stack = stack
        print(f"MockSM16relind initialized with stack {stack}")

    def set(self, relay, state):
        print(f"MockSM16relind set relay {relay} to state {state}")

    def set_all(self, state):
        print(f"MockSM16relind set all relays to state {state}")
