"Sentinel module that used in services to make db pretend as injected"

class _Injected:
    def __repr__(self) -> str:
        return "<Injected>"

    def __str__(self) -> str:
        return "<Injected>"
