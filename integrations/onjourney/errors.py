class IntegrationError(Exception):
    pass


class BookingValidationError(IntegrationError):
    pass


class OperationConflict(IntegrationError):
    pass


class PaymentSequenceError(IntegrationError):
    pass
