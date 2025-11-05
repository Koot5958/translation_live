

def _display_models_output(box, transcript=True, prev_text=None, curr_text=None):
    if not curr_text:
        curr_text = f"Waiting for {"transcription" if transcript else "translation"}..."
    if not prev_text:
        prev_text = '...'
    box.markdown(
        f"""
            <div style="font-size:1.1em;">
                <h2>{"Transcript" if transcript else "Translation"}</h2>
            </div>
            <p style="color:gray; opacity:0.6; margin-bottom:0.2em;">{prev_text}</p>
            <p style="background-color:#1E90FF22; padding:4px 8px; border-radius:6px;">{curr_text}</p>
        """,
        unsafe_allow_html=True,
    )


def update_boxes(transc_box, transl_box, prev_transc, transc, prev_transl, transl):
    _display_models_output(transc_box, transcript=True, prev_text=prev_transc, curr_text=transc)
    _display_models_output(transl_box, transcript=False, prev_text=prev_transl, curr_text=transl)