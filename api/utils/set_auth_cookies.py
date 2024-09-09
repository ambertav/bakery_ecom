def set_tokens_in_cookies(response, access_token, refresh_token):
    '''
    Sets the access and refresh tokens in cookies.

    Args :
        response (flask.Response) : response object to set the cookies on.
        access_token (str) : access token to set in the cookie.
        refresh_token (str) : refresh token to set in the cookie.
    '''

    response.set_cookie(
        'access_token',
        value = access_token,
        httponly = 'true',
        max_age = 15 * 60 if access_token else 0,
        samesite = 'None',
        secure = 'false'
    )

    response.set_cookie(
        'refresh_token',
        value = refresh_token,
        httponly = 'true',
        max_age = 7 * 24 * 60 * 60 if refresh_token else 0,
        samesite = 'None',
        secure = 'false'
    )

    return response
