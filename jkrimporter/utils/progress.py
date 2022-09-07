class Progress:
    def __init__(self, size: int):
        self.size = size
        self.current = 0
        self.print_step = int(self.size / 1000)

    def print(self) -> None:
        p = self.current / self.size * 100 if self.size > 0 else 100
        print(f"{p:6.2f}% [{self.current}/{self.size}]", end="\r")

    def tick(self) -> None:
        if self.print_step == 0 or self.current % self.print_step == 0:
            self.print()

        self.current += 1

    def complete(self) -> None:
        self.current = self.size
        self.print()

    def reset(self) -> None:
        self.current = 0
