from importlib.metadata import version

from sentinel_auth.roles import RoleClient
from sentinel_auth.types import AuthenticatedUser, WorkspaceContext

__version__ = version("sentinel-auth-sdk")
__all__ = ["AuthenticatedUser", "RoleClient", "WorkspaceContext", "__version__"]
