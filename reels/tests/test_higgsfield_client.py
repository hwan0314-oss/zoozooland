from unittest.mock import Mock, patch

import pytest

import higgsfield_client


def test_upload_image_returns_public_url():
    upload_url_response = Mock(status_code=200)
    upload_url_response.json.return_value = {
        "public_url": "https://cdn.example.com/input/sample.jpeg",
        "upload_url": "https://storage.example.com/presigned-upload-url",
        "content_type": "image/jpeg",
        "upload_headers": {
            "Content-Type": "image/jpeg",
            "x-amz-tagging": "retention=temporary",
        },
    }
    put_response = Mock(status_code=200)

    with patch("higgsfield_client.requests.post", return_value=upload_url_response) as mock_post, \
         patch("higgsfield_client.requests.put", return_value=put_response) as mock_put:
        result = higgsfield_client.upload_image(b"fake-jpeg-bytes")

    assert result == "https://cdn.example.com/input/sample.jpeg"
    assert mock_post.call_args.args[0] == "https://api.higgsfield.ai/files/generate-upload-url"
    assert mock_post.call_args.kwargs["headers"] == {"Authorization": "Key test-key-id:test-key-secret"}
    assert mock_post.call_args.kwargs["json"] == {"content_type": "image/jpeg"}
    assert mock_put.call_args.args[0] == "https://storage.example.com/presigned-upload-url"
    assert mock_put.call_args.kwargs["data"] == b"fake-jpeg-bytes"
    assert mock_put.call_args.kwargs["headers"] == {
        "Content-Type": "image/jpeg",
        "x-amz-tagging": "retention=temporary",
    }


def test_upload_image_raises_on_upload_url_error():
    error_response = Mock(status_code=401, text='{"detail": "Invalid credentials"}')

    with patch("higgsfield_client.requests.post", return_value=error_response):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="401"):
            higgsfield_client.upload_image(b"fake-jpeg-bytes")
