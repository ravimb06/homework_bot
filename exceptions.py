class EndpointRequestError(Exception):
    pass


class EndpointError(Exception):
    pass


class ResponseIsNotDict(Exception):
    pass


class TokensNoneError(ValueError):
    pass
