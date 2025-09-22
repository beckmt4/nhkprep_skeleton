class NHKPrepError(Exception):
    """Base exception for nhkprep."""


class ProbeError(NHKPrepError):
    pass


class ToolNotFoundError(NHKPrepError):
    pass


class RemuxError(NHKPrepError):
    pass
