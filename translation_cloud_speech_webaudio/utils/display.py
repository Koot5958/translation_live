from .parameters import MAX_LEN, REFRESH_RATE_SLOW
from .lang_list import LANGUAGE_USES_SPACE


def join_text(text, lang):
    return " ".join(text) if LANGUAGE_USES_SPACE[lang] else "".join(text)


def split_text(text, lang):
    return text.split(" ") if LANGUAGE_USES_SPACE[lang] else text.split("")


def format_subt(text, prev_subt):
    new_line = False

    if len(text) <= MAX_LEN:
        subt = text
        prev_subt = []
    else:
        subt = text[(len(text) // MAX_LEN) * MAX_LEN :]
        start_subt = len(text) - len(subt)

        new_prev_subt = text[: start_subt]
        new_prev_subt = new_prev_subt[-MAX_LEN :]
        if prev_subt != new_prev_subt:
            prev_subt = new_prev_subt
            new_line = True

    return new_line, prev_subt, subt


def get_html_subt(prev_subt, subt, line_scroll, subt_type):
    if line_scroll:
        html = f"""
            <style>
                @keyframes shrinkSpace {{
                    0%   {{ height: calc(17px * 1.4); opacity: 1; }}
                    100% {{ height: 0; opacity: 0; }}
                }}
                .trans-box-{subt_type} {{
                    max-width: 90%;
                    margin: auto;
                    padding: 10px;
                    color: black;
                    font-size: 17px;
                    line-height: 1.4;
                    text-align: center;
                }}
                .space-line-{subt_type} {{
                    height: calc(17px * 1.4);
                    animation: shrinkSpace {REFRESH_RATE_SLOW}s ease-out forwards;
                }}
            </style>
        """
    else:
        html = f"""
            <style>
                .trans-box-{subt_type} {{
                    max-width: 90%;
                    margin: auto;
                    padding: 10px;
                    color: black;
                    font-size: 17px;
                    line-height: 1.4;
                    text-align: center;
                }}
            </style>
        """
    return html + f"""
        <div class="trans-box-{subt_type}">
            <div class="space-line-{subt_type}"></div>
            <div style="display:block; text-align: left;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{prev_subt}</span></div>
            <div style="display:block; text-align: left;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{subt}</span></div>
        </div>
    """