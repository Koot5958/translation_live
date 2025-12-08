def get_html_subt(prev_subt, subt, line_scroll):
    if line_scroll:
        html = f"""
            <style>
                @keyframes shrinkSpace {{
                    0%   {{ height: calc(17px * 1.4); opacity: 1; }}
                    100% {{ height: 0; opacity: 0; }}
                }}
                .trans-box {{
                    max-width: 90%;
                    margin: auto;
                    padding: 10px;
                    color: black;
                    font-size: 17px;
                    line-height: 1.4;
                    text-align: center;
                }}
                .space-line {{
                    height: calc(17px * 1.4);
                    animation: shrinkSpace 0.3s ease-out forwards;
                }}
            </style>
        """
    else:
        html = f"""
            <style>
                .trans-box {{
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
        <div class="trans-box">
            <div class="space-line"></div>
            <div style="display:block;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{" ".join(prev_subt)}</span></div>
            <div style="display:block;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{" ".join(subt)}</span></div>
        </div>
    """