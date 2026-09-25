import re
from unittest.mock import Mock, patch

import pytest
import requests

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


def test_poll_until_done_retries_after_5xx_then_returns_completed():
    server_error = Mock(status_code=503, text="Service Unavailable")
    completed = Mock(status_code=200)
    completed.json.return_value = {
        "status": "completed",
        "video": {"url": "https://cdn.example.com/output.mp4"},
    }

    with patch("higgsfield_client.requests.get", side_effect=[server_error, completed]) as mock_get, \
         patch("higgsfield_client.time.sleep") as mock_sleep:
        result = higgsfield_client._poll_until_done(STATUS_URL)

    assert result["video"]["url"] == "https://cdn.example.com/output.mp4"
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_poll_until_done_retries_after_connection_error_then_returns_completed():
    completed = Mock(status_code=200)
    completed.json.return_value = {
        "status": "completed",
        "video": {"url": "https://cdn.example.com/output.mp4"},
    }

    with patch(
        "higgsfield_client.requests.get",
        side_effect=[requests.ConnectionError("connection reset"), completed],
    ) as mock_get, \
         patch("higgsfield_client.time.sleep") as mock_sleep:
        result = higgsfield_client._poll_until_done(STATUS_URL)

    assert result["video"]["url"] == "https://cdn.example.com/output.mp4"
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_poll_until_done_retries_after_429_then_returns_completed():
    rate_limited = Mock(status_code=429, text="Too Many Requests")
    completed = Mock(status_code=200)
    completed.json.return_value = {
        "status": "completed",
        "video": {"url": "https://cdn.example.com/output.mp4"},
    }

    with patch("higgsfield_client.requests.get", side_effect=[rate_limited, completed]) as mock_get, \
         patch("higgsfield_client.time.sleep") as mock_sleep:
        result = higgsfield_client._poll_until_done(STATUS_URL)

    assert result["video"]["url"] == "https://cdn.example.com/output.mp4"
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_poll_until_done_raises_after_max_consecutive_failures():
    server_error = Mock(status_code=503, text="Service Unavailable")

    with patch("higgsfield_client.requests.get", return_value=server_error) as mock_get, \
         patch("higgsfield_client.time.sleep"):
        with pytest.raises(higgsfield_client.HiggsfieldError, match=re.escape(STATUS_URL)):
            higgsfield_client._poll_until_done(STATUS_URL)

    assert mock_get.call_count == higgsfield_client.MAX_CONSECUTIVE_POLL_FAILURES


def test_poll_until_done_raises_immediately_on_404():
    not_found = Mock(status_code=404, text="Not Found")

    with patch("higgsfield_client.requests.get", return_value=not_found) as mock_get, \
         patch("higgsfield_client.time.sleep"):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="404"):
            higgsfield_client._poll_until_done(STATUS_URL)

    assert mock_get.call_count == 1


def test_download_video_raises_on_404_with_url():
    video_url = "https://cdn.example.com/output.mp4"
    not_found = Mock(status_code=404, text="Not Found")

    with patch("higgsfield_client.requests.get", return_value=not_found):
        with pytest.raises(higgsfield_client.HiggsfieldError, match=re.escape(video_url)):
            higgsfield_client._download_video(video_url)


def test_download_video_raises_on_connection_error_with_url():
    video_url = "https://cdn.example.com/output.mp4"

    with patch("higgsfield_client.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(higgsfield_client.HiggsfieldError, match=re.escape(video_url)):
            higgsfield_client._download_video(video_url)


def test_submit_and_download_raises_on_connection_error_without_retry():
    with patch(
        "higgsfield_client.requests.post",
        side_effect=requests.ConnectionError("boom"),
    ) as mock_post:
        with pytest.raises(higgsfield_client.HiggsfieldError, match=re.escape("console.higgsfield.ai")):
            higgsfield_client._submit_and_download(
                higgsfield_client.KLING_TEXT_TO_VIDEO_ENDPOINT, {"prompt": "test"}
            )

    assert mock_post.call_count == 1


def test_submit_and_download_prints_request_id_and_status_url(capsys):
    download_response = Mock(status_code=200, content=b"fake-video-bytes")

    with patch("higgsfield_client.requests.post", return_value=_submit_response("r1")), \
         patch(
             "higgsfield_client.requests.get",
             side_effect=[_completed_response("https://cdn.example.com/output.mp4"), download_response],
         ):
        higgsfield_client._submit_and_download(
            higgsfield_client.KLING_TEXT_TO_VIDEO_ENDPOINT, {"prompt": "test"}
        )

    err = capsys.readouterr().err
    assert "r1" in err
    assert "https://api.higgsfield.ai/requests/r1/status" in err


def _submit_response(request_id: str) -> Mock:
    response = Mock(status_code=200)
    response.json.return_value = {
        "status": "queued",
        "request_id": request_id,
        "status_url": f"https://api.higgsfield.ai/requests/{request_id}/status",
    }
    return response


def _completed_response(video_url: str) -> Mock:
    response = Mock(status_code=200)
    response.json.return_value = {"status": "completed", "video": {"url": video_url}}
    return response


def test_generate_video_from_image_uploads_cropped_photo_and_returns_video():
    upload_url_response = Mock(status_code=200)
    upload_url_response.json.return_value = {
        "public_url": "https://cdn.example.com/input/cropped.jpeg",
        "upload_url": "https://storage.example.com/presigned",
        "upload_headers": {"Content-Type": "image/jpeg"},
    }
    download_response = Mock(status_code=200, content=b"fake-video-bytes")

    with patch("higgsfield_client.crop_to_vertical", return_value=b"cropped-jpeg") as mock_crop, \
         patch(
             "higgsfield_client.requests.post",
             side_effect=[upload_url_response, _submit_response("r1")],
         ) as mock_post, \
         patch("higgsfield_client.requests.put", return_value=Mock(status_code=200)) as mock_put, \
         patch(
             "higgsfield_client.requests.get",
             side_effect=[_completed_response("https://cdn.example.com/output.mp4"), download_response],
         ) as mock_get:
        result = higgsfield_client.generate_video_from_image(
            "alpaca.jpg", "알파카가 건초를 먹는 모습", duration=8
        )

    assert result == b"fake-video-bytes"
    mock_crop.assert_called_once_with("alpaca.jpg")
    assert mock_put.call_args.kwargs["data"] == b"cropped-jpeg"
    submit_call = mock_post.call_args_list[1]
    assert submit_call.args[0] == "https://api.higgsfield.ai/kling-video/v3.0/std/image-to-video"
    assert submit_call.kwargs["json"] == {
        "prompt": "알파카가 건초를 먹는 모습",
        "image_url": "https://cdn.example.com/input/cropped.jpeg",
        "duration": 8,
    }
    assert mock_get.call_args_list[0].args[0] == "https://api.higgsfield.ai/requests/r1/status"
    assert mock_get.call_args_list[1].args[0] == "https://cdn.example.com/output.mp4"


def test_generate_video_from_text_returns_video():
    download_response = Mock(status_code=200, content=b"fake-video-bytes-2")

    with patch("higgsfield_client.requests.post", return_value=_submit_response("r2")) as mock_post, \
         patch(
             "higgsfield_client.requests.get",
             side_effect=[_completed_response("https://cdn.example.com/output2.mp4"), download_response],
         ):
        result = higgsfield_client.generate_video_from_text(
            "알파카 아침 산책", duration=10, aspect_ratio="9:16"
        )

    assert result == b"fake-video-bytes-2"
    assert mock_post.call_args.args[0] == "https://api.higgsfield.ai/kling-video/v3.0/std/text-to-video"
    assert mock_post.call_args.kwargs["json"] == {
        "prompt": "알파카 아침 산책",
        "duration": 10,
        "aspect_ratio": "9:16",
    }


def test_generate_video_raises_when_submission_rejected():
    rejected = Mock(status_code=403, text='{"detail": "Insufficient credits"}')

    with patch("higgsfield_client.requests.post", return_value=rejected):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="403"):
            higgsfield_client.generate_video_from_text("알파카 아침 산책")
