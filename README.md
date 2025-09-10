# revisor

<img src="revisor.png" alt="revisor logo" width="200"/>

Revises text from the clipboard using a large language model.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yurug/revisor.git
    cd revisor
    ```

2.  **Install dependencies:**
    -   `python3`
    -   `curl`
    -   For X11: `xclip`
    -   For Wayland: `wl-paste` and `wl-copy`
    -   For notification sounds (optional): `paplay` or `aplay`

    On Debian/Ubuntu, you can install them with:
    ```bash
    sudo apt-get update
    sudo apt-get install -y python3 curl xclip wl-clipboard libnotify-bin
    ```

3.  **Set up your API key:**
    You need to have an OpenAI API key. Set it as an environment variable:
    ```bash
    export OPENAI_API_KEY="your-api-key"
    ```
    It's recommended to add this line to your shell's startup file (e.g., `~/.bashrc`, `~/.zshrc`).

4.  **(Optional) Customize the prompt:**
    Create a file at `~/.revisor` with a custom system prompt.

    If this file doesn't exist, the following default prompt will be used:

    ```
    Revise the text for clarity and concision. Preserve meaning. Keep same language. Plain text only.
    ```

5. **(Recommended)** Install a keyboard shortcut in your environment.

   In practice, you should also create a keyboard shortcut to run `revisor.py` for quick access.

   For instance, I have added the following line to my `.config/i3/config` file:

   ```
   bindsym $mod+Shift+Control+r exec zsh -lc "~/.local/bin/revisor"
   ```

   (after having created a link to `revisor.py` from `~/.local/bin/revisor`.)


## Usage

1.  Copy some text to your clipboard.
2.  Use your keyboard shorcut or manually run the script:
    ```bash
    ./revisor.py
    ```
3.  The revised text will be pasted to your clipboard. Paste it!

## Inline prompt extensions

I've added the following to my `.revisor` file:

```
- If you see something between << ... >> remove it from the input but use it as an extension of this prompt.
```

It happens to be quite handy to give extra instructions specific to
your immediate need.


## Philosophy

This script follows the KISS principle: it does one specific thing and
aims to do it right, with no dependencies and clear
semantics. Contributions are welcome as long as they adhere to this
philosophy!

## License

MIT License
