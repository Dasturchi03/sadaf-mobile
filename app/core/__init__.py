"""Signature"""

from app.core.app import app


try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    with open(".signature", "r", encoding="utf-8") as f:
        print(Fore.CYAN + f.read() + Style.RESET_ALL)
except: pass


def get_project_ui_html(project_name: str = "CPython"):
    HTML = """
<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
<title>""" + project_name + """</title>
  <style>
    :root {
      --speed: 6s;
      --bg-size: 300% 100%;
      --font-size-clamp: clamp(3rem, 12vw, 12rem);
    }

    body {
      margin: 0;
      min-height: 100dvh;
      display: grid;
      place-items: center;
      background: #0b0f14;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji";
    }

    .wrap {
      text-align: center;
      padding: 2rem;
    }

    .rgb-text {
      font-weight: 900;
      line-height: 0.9;
      letter-spacing: 0.02em;
      font-size: var(--font-size-clamp);
      margin: 0;
      background: linear-gradient(90deg,
        #ff0033 0%,
        #ff8800 14%,
        #ffee00 28%,
        #00ff66 42%,
        #00ddff 57%,
        #3366ff 71%,
        #aa33ff 85%,
        #ff0033 100%
      );
      background-size: var(--bg-size);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      animation: wave var(--speed) linear infinite;
      display: inline-block;
      filter: drop-shadow(0 0 12px rgba(0, 255, 200, 0.35)) drop-shadow(0 0 24px rgba(170, 50, 255, 0.25));
      text-transform: uppercase;
    }

    .sub {
      margin-top: 1rem;
      color: #8aa0b6;
      font-weight: 500;
      letter-spacing: 0.08em;
    }

    @keyframes wave {
      0%   { background-position: 0% 50%; }
      100% { background-position: 200% 50%; }
    }

    @media (max-width: 420px) {
      .rgb-text { letter-spacing: 0.01em; }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <h1 class="rgb-text" spellcheck="false">""" + project_name.upper() + """</h1>
    <!-- <div class="sub">@Dasturchi_03</div> -->
  </main>

  <script>
  </script>
</body>
</html>

"""

    return HTML
