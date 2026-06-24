import httpx
from app.core.exceptions import AuthenticationError


async def refresh_spotify_token(user, spotify_client, user_repository) -> str:
    if not user.refresh_token:
        raise AuthenticationError("Spotify session expired")

    try:
        token_data = await spotify_client.refresh_access_token(user.refresh_token)
    except httpx.HTTPStatusError:
        raise AuthenticationError("Spotify session expired")

    new_access_token = token_data["access_token"]
    new_refresh_token = token_data.get("refresh_token", user.refresh_token)

    await user_repository.update_spotify_tokens(
        user_id=user.id,
        spotify_id=user.spotify_id,
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )

    return new_access_token
