class MockGPIO:
    BOARD = 'BOARD'
    OUT = 'OUT'

    @staticmethod
    def setmode(mode):
        print(f"GPIO setmode({mode})")

    @staticmethod
    def setup(pin, mode):
        print(f"GPIO setup({pin}, {mode})")

    @staticmethod
    def output(pin, state):
        print(f"GPIO output({pin}, {state})")

    @staticmethod
    def cleanup():
        print("GPIO cleanup()")
