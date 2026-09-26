from __future__ import annotations

from mneme.contracts import GenerationRequest
from mneme.hosts.local_llama import LocalLlamaHost, _extract_output, _render_prompt


def test_local_host_fingerprint_declares_local_weights() -> None:
    host = LocalLlamaHost("/models/gemma.gguf", runtime_version="0.5.0-dev")
    fingerprint = host.fingerprint().to_dict()
    assert fingerprint["provider"] == "local-msi"
    assert "local_weights" in fingerprint["capabilities"]
    assert "seed_control" in fingerprint["capabilities"]
    assert fingerprint["quantization"] == "UD-Q2_K_XL"
    assert fingerprint["execution"]["reasoning"] == "off"


def test_prompt_rendering_keeps_message_order_and_system_boundary() -> None:
    request = GenerationRequest(
        messages=(
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ),
        system="system",
    )
    prompt = _render_prompt(request)
    assert prompt.index("first") < prompt.index("second")
    assert prompt.startswith("System instructions:\nsystem")


def test_cli_banner_and_footer_are_removed_without_rewriting_content() -> None:
    prompt = "say hello"
    stdout = f"banner\n> {prompt}\nHello, world!\n[ Prompt: 1.0 t/s | Generation: 2.0 t/s ]\n"
    assert _extract_output(stdout, prompt) == "Hello, world!"


def test_truncated_prompt_echo_is_removed_before_response() -> None:
    stdout = "banner\n> System instructions: ... (truncated)\nA complete answer.\n"
    assert _extract_output(stdout, "unused prompt") == "A complete answer."


def test_seed_is_forwarded_to_llama_cli(monkeypatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command

        class Result:
            returncode = 0
            stdout = "answer"
            stderr = ""

        return Result()

    monkeypatch.setattr("mneme.hosts.local_llama.subprocess.run", fake_run)
    host = LocalLlamaHost("/models/gemma.gguf")
    host.generate(GenerationRequest(({"role": "user", "content": "hello"},), seed=17))
    command = captured["command"]
    assert "--seed" in command
    assert command[command.index("--seed") + 1] == "17"
