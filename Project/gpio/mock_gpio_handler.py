class MockSM16relind:
    def __init__(self, stack):
        self.stack = stack
        self.relay_states = [0] * 16

    def set_all(self, state):
        print(f"MockSM16relind set all relays to state {state}")
        self.relay_states = [state] * 16

    def set(self, relay, state):
        print(f"MockSM16relind relay {relay} set to state {state}")
        self.relay_states[relay - 1] = state

# Ensure the mock module is properly available as sm_16relind
sys.modules['sm_16relind'] = MockSM16relind
