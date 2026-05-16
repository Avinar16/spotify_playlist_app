class DomainException(Exception):
    """Base domain exception"""
    pass


class UserAlreadyExistsException(DomainException):
    """User with email already exists"""
    pass


class UserNotFoundException(DomainException):
    """User not found"""
    pass


class InvalidCredentialsException(DomainException):
    """Invalid email or password"""
    pass


class PlaylistNotFoundException(DomainException):
    """Playlist not found"""
    pass


class AccessDeniedException(DomainException):
    """Access denied to playlist"""
    pass


class SpotifyException(DomainException):
    """Spotify API error"""
    pass


class AuthenticationError(DomainException):
    """Authentication error"""
    pass


class SpotifyTokenExpiredError(AuthenticationError):
    """Spotify access token expired - requires re-authorization"""
    pass


class ValidationError(DomainException):
    """Validation error"""
    pass
