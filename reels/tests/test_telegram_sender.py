from unittest.mock import AsyncMock, Mock, patch

import pytest

import telegram_sender


def _mock_client(mock_client_cls, authorized=True, entity_side_effect=None):
    client = mock_client_cls.return_value
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_user_authorized = AsyncMock(return_value=authorized)
    client.get_input_entity = AsyncMock(side_effect=entity_side_effect or ["channel-entity"])
    client.get_dialogs = AsyncMock()
    client.send_file = AsyncMock(return_value=Mock(id=42))
    return client


def test_send_video_posts_to_approval_channel_as_user():
    with patch("telegram_sender.TelegramClient") as mock_client_cls:
        client = _mock_client(mock_client_cls)
        result = telegram_sender.send_video_for_approval(b"fake-video-bytes", filename="test.mp4")

    assert result == 42
    mock_client_cls.assert_called_once_with(str(telegram_sender.SESSION_PATH), 12345, "test-api-hash")
    client.get_input_entity.assert_awaited_once_with(-1001234567890)
    entity, video = client.send_file.call_args.args
    assert entity == "channel-entity"
    assert video.getvalue() == b"fake-video-bytes"
    assert video.name == "test.mp4"
    assert client.send_file.call_args.kwargs == {"supports_streaming": True}
    client.disconnect.assert_awaited_once()


def test_send_video_requires_login():
    with patch("telegram_sender.TelegramClient") as mock_client_cls:
        client = _mock_client(mock_client_cls, authorized=False)
        with pytest.raises(telegram_sender.TelegramSendError, match="로그인"):
            telegram_sender.send_video_for_approval(b"fake-video-bytes")

    client.send_file.assert_not_awaited()
    client.disconnect.assert_awaited_once()


def test_send_video_loads_dialogs_when_channel_not_cached():
    with patch("telegram_sender.TelegramClient") as mock_client_cls:
        client = _mock_client(
            mock_client_cls,
            entity_side_effect=[ValueError("Could not find the input entity"), "channel-entity"],
        )
        telegram_sender.send_video_for_approval(b"fake-video-bytes")

    client.get_dialogs.assert_awaited_once()
    assert client.send_file.call_args.args[0] == "channel-entity"
