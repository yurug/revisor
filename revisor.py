#!/usr/bin/env python3
"""
Revises text from the clipboard using a large language model.
"""
import os, sys, time, subprocess, json, datetime
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired

PROMPT_FILE = Path.home() / ".revisor"
LOG_FILE    = Path.home() / ".revisor.log"

MODEL   = os.getenv("REVISOR_MODEL", "gpt-5")
API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE= os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
ECHO    = os.getenv("REVISOR_ECHO", "0") == "1"  # also print revised text to stdout

def log(msg):
    """Appends a timestamped message to the log file ~/.revise.log."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def whereis(cmd):
    """Checks if a command exists in the user's PATH."""
    return subprocess.run(["bash","-lc", f"command -v {cmd} >/dev/null 2>&1"]).returncode == 0

def run(cmd, timeout=1.0, check=True, text=True, capture_output=True, stdin=None):
    """Executes a command, captures its output, and handles errors."""
    try:
        return subprocess.run(cmd, timeout=timeout, check=check, text=text,
                              capture_output=capture_output, input=stdin)
    except TimeoutExpired:
        log(f"TIMEOUT: {' '.join(cmd)}")
        raise
    except CalledProcessError as e:
        log(f"NONZERO EXIT {e.returncode}: {' '.join(cmd)} | stderr={e.stderr!r}")
        if check: raise
        return e

def read_prompt():
    """Reads the system prompt from ~/.revisor, or returns a default."""
    if PROMPT_FILE.exists():
        p = PROMPT_FILE.read_text(encoding="utf-8").strip()
        log(f"Prompt loaded ({len(p)} chars)")
        return p
    default = "Revise the text for clarity and concision. Preserve meaning. Keep same language. Plain text only."
    log("Prompt file missing; using default.")
    return default

def grab_primary_x11():
    """Captures text from the X11 primary selection (middle-click paste) using xclip."""
    if whereis("xclip"):
        try:
            out = run(["xclip","-selection","primary","-o"], timeout=0.3)
            text = out.stdout
            log(f"PRIMARY grabbed: len={len(text)}")
            return text
        except Exception:
            pass
    return ""

def grab_clipboard_x11():
    """Captures text from the X11 clipboard (Ctrl+C/V) using xclip."""
    if whereis("xclip"):
        try:
            out = run(["xclip","-selection","clipboard","-o"], timeout=0.3)
            text = out.stdout
            log(f"CLIPBOARD grabbed: len={len(text)}")
            return text
        except Exception:
            pass
    return ""

def x11_capture():
    """Captures text from X11, prioritizing primary selection then clipboard, using xclip."""
    # Order: PRIMARY → CLIPBOARD
    text = grab_primary_x11()
    if not text.strip():
        text = grab_clipboard_x11()
    log(f"Captured (X11) final len={len(text)}")
    return text

def wayland_capture():
    """Captures text from the Wayland clipboard or primary selection using wl-paste."""
    # Wayland: try clipboard/primary.
    text = ""
    if whereis("wl-paste"):
        for args in (["wl-paste","--no-newline"], ["wl-paste","--primary","--no-newline"]):
            try:
                out = run(args, timeout=0.3)
                if out.stdout.strip():
                    text = out.stdout
                    whereis_primary = "PRIMARY" if "--primary" in args else "CLIPBOARD"
                    log(f"Wayland {whereis_primary} grabbed len={len(text)}")
                    break
            except Exception:
                pass
    log(f"Captured (Wayland) final len={len(text)}")
    return text

def ask_llm(system_prompt, user_text):
    """Sends text to a large language model for revision and returns the result."""
    in_len = len(user_text)
    log_text = user_text[:500]
    if in_len > 500:
        log_text += "..."
    log(f"LLM request: model={MODEL}, in_len={in_len}, text={log_text!r}")
    headers = [
        "Content-Type: application/json",
        f"Authorization: Bearer {API_KEY}"
    ]
    body = {
        "model": MODEL,
        "input": [
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_text}
        ]
    }
    try:
        json_body = json.dumps(body)
        curl_cmd = f'curl -sS -X POST "{API_BASE}/responses" -H "{headers[0]}" -H "{headers[1]}" -d @-'
        out = run(["bash", "-lc", curl_cmd], timeout=60.0, stdin=json_body)
        data = json.loads(out.stdout)
        log(f"LLM response keys={list(data.keys())}")

        if isinstance(data.get("text"), str) and data["text"].strip():
            text = data["text"].strip()
            log(f"LLM text len={len(text)} (from .text)")
            return text

        # Responses format
        if "output" in data and isinstance(data["output"], list):
            chunks = []
            for item in data["output"]:
                for blk in item.get("content", []):
                    if blk.get("type") == "output_text":
                        chunks.append(blk.get("text", ""))
            text = ("\n".join(chunks)).strip()
            log(f"LLM text len={len(text)} (/responses)")
            return text
        # Chat Completions fallback
        if "choices" in data and data["choices"]:
            text = data["choices"][0]["message"]["content"].strip()
            log(f"LLM text len={len(text)} (/chat)")
            return text
        log(f"LLM response parse failed. Full response: {json.dumps(data)}")
    except Exception as e:
        log(f"LLM error: {e}")
    return ""


def play_notification_sound():
    """Plays a notification sound using paplay or aplay."""
    player = "paplay" if whereis("paplay") else "aplay" if whereis("aplay") else None
    if not player:
        return
    sound_files = [
        "/usr/share/sounds/freedesktop/stereo/message.oga",
        "/usr/share/sounds/freedesktop/stereo/complete.oga",
    ]
    for sound_file in sound_files:
        if Path(sound_file).exists():
            try:
                subprocess.Popen([player, sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass


def paste_x11(text):
    """Pastes text to the X11 clipboard using xclip."""
    # Load text to CLIPBOARD.
    log(f"Paste (X11) len={len(text)}")
    if whereis("xclip"):
        p = subprocess.Popen(["xclip","-selection","clipboard","-in"], stdin=subprocess.PIPE, text=True)
        p.communicate(text)
    else:
        log("xclip missing; cannot set clipboard")

def paste_wayland(text):
    """Pastes text to the Wayland clipboard using wl-copy."""
    log(f"Paste (Wayland) len={len(text)}")
    if whereis("wl-copy"):
        p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
        p.communicate(text)

def capture():
    """Captures text from clipboard, trying Wayland then X11."""
    session = os.getenv("XDG_SESSION_TYPE","").lower()
    if session == "wayland" and whereis("wl-paste"):
        return wayland_capture()
    return x11_capture()

def paste(text):
    """Pastes text to clipboard, trying Wayland then X11."""
    session = os.getenv("XDG_SESSION_TYPE","").lower()
    if session == "wayland" and whereis("wl-copy"):
        paste_wayland(text)
    else:
        paste_x11(text)

def main():
    """Main entry point: captures text, sends to LLM, and pastes the revision."""
    if not API_KEY:
        log("ERROR: OPENAI_API_KEY not set."); sys.exit(1)
    session = os.getenv("XDG_SESSION_TYPE","").lower()
    display = os.getenv("DISPLAY", "")
    log(f"Start: session={session}, DISPLAY={display!r}, model={MODEL}")

    sys_prompt = read_prompt()
    src = capture()

    if not src.strip():
        log("No source text captured; abort."); sys.exit(0)

    revised = ask_llm(sys_prompt, src)
    play_notification_sound()

    if not revised.strip():
        log("LLM returned empty; fallback to source.")
        revised = src

    if ECHO:
        print(revised)

    paste(revised)
    log("Done.")

if __name__ == "__main__":
    """Handles script execution and graceful shutdown."""
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted by user (SIGINT).")
        sys.exit(130)
