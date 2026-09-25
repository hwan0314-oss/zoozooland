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


STATUS_URL = "https://api.higgsfield.ai/requests/r1/status"


def test_poll_until_done_returns_completed_result():
    queued = Mock(status_code=200)
    queued.json.return_value = {"status": "queued", "request_id": "r1"}
    completed = Mock(status_code=200)
    completed.json.return_value = {
        "status": "completed",
        "request_id": "r1",
        "video": {"url": "https://cdn.example.com/output.mp4"},
    }

    with patch("higgsfield_client.requests.get", side_effect=[queued, completed]) as mock_get, \
         patch("higgsfield_client.time.sleep") as mock_sleep:
        result = higgsfield_client._poll_until_done(STATUS_URL)

    assert result["video"]["url"] == "https://cdn.example.com/output.mp4"
    assert mock_get.call_count == 2
    assert mock_get.call_args.args[0] == STATUS_URL
    mock_sleep.assert_called_once()


def test_poll_until_done_raises_on_failed_status():
    failed = Mock(status_code=200)
    failed.json.return_value = {"status": "failed", "request_id": "r1", "error": "Generation failed"}

    with patch("higgsfield_client.requests.get", return_value=failed):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="Generation failed"):
            higgsfield_client._poll_until_done(STATUS_URL)


def test_poll_until_done_raises_on_timeout():
    queued = Mock(status_code=200)
    queued.json.return_value = {"status": "queued", "request_id": "r1"}

    with patch("higgsfield_client.requests.get", return_value=queued), \
         patch("higgsfield_client.time.sleep"), \
         patch("higgsfield_client.time.monotonic", side_effect=[0, 1000]):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="타임아웃"):
            higgsfield_client._poll_until_done(STATUS_URL, timeout_seconds=5.0)
