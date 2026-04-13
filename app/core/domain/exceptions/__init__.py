class BaseError(Exception):
    message = "Base error"

    def __init__(self, message=None, *args):
        self.message = message if message is not None else self.message
        super().__init__(self.message, *args)


class DomainError(BaseError):
    message = "Domain error"
