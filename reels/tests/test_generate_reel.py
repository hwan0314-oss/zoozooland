from unittest.mock import patch

import generate_reel


def test_photo_command_saves_video_and_sends_it(tmp_path, capsys):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch(
             "generate_reel.generate_video_from_image", return_value=b"fake-video-bytes"
         ) as mock_generate, \
         patch("generate_reel.send_video_for_approval", return_value=99) as mock_send:
        exit_code = generate_reel.main(["photo", "alpaca.jpg", "알파카 아침 산책", "--duration", "8"])

    assert exit_code == 0
    mock_generate.assert_called_once_with("alpaca.jpg", "알파카 아침 산책", duration=8)
    saved = list(tmp_path.glob("reel_*.mp4"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"fake-video-bytes"
    mock_send.assert_called_once_with(b"fake-video-bytes", filename=saved[0].name)
    assert "message_id=99" in capsys.readouterr().out


def test_text_command_passes_duration_and_aspect_ratio(tmp_path):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch(
             "generate_reel.generate_video_from_text", return_value=b"fake-video-bytes"
         ) as mock_generate, \
         patch("generate_reel.send_video_for_approval", return_value=100):
        exit_code = generate_reel.main(
            ["text", "알파카 아침 산책", "--duration", "9", "--aspect-ratio", "9:16"]
        )

    assert exit_code == 0
    mock_generate.assert_called_once_with("알파카 아침 산책", duration=9, aspect_ratio="9:16")


def test_generation_failure_skips_saving_and_sending(tmp_path, capsys):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch(
             "generate_reel.generate_video_from_image",
             side_effect=generate_reel.HiggsfieldError("Insufficient credits"),
         ), \
         patch("generate_reel.send_video_for_approval") as mock_send:
        exit_code = generate_reel.main(["photo", "alpaca.jpg", "알파카 아침 산책"])

    assert exit_code == 1
    mock_send.assert_not_called()
    assert list(tmp_path.iterdir()) == []
    assert "Insufficient credits" in capsys.readouterr().err


def test_telegram_failure_keeps_saved_video_and_reports_path(tmp_path, capsys):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch("generate_reel.generate_video_from_text", return_value=b"fake-video-bytes"), \
         patch(
             "generate_reel.send_video_for_approval",
             side_effect=generate_reel.TelegramSendError("텔레그램 로그인이 필요합니다."),
         ):
        exit_code = generate_reel.main(["text", "알파카 아침 산책"])

    assert exit_code == 1
    saved = list(tmp_path.glob("reel_*.mp4"))
    assert len(saved) == 1
    assert str(saved[0]) in capsys.readouterr().err
