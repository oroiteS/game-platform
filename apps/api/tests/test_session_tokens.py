from app.platform.services.session_tokens import (
    generate_session_token,
    hash_token,
    verify_token,
)


def test_session_token_hash_verifies_original_token():
    token = generate_session_token()
    token_hash = hash_token(token)

    assert verify_token(token, token_hash)
    assert not verify_token(f"{token}-wrong", token_hash)
    assert token != token_hash
