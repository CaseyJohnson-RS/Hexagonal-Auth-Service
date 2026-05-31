from . import ApplicationError


class ConcurrencyError(ApplicationError):
    message = "Concurrency error"
