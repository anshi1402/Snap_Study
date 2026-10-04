import streamlit as st 
import json
from email_service import send_study_email 
from google import genai 
from google.genai import types

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, EMAIL_STUDY_NOTE_PROMPT, EMAIL_SUBJECT_PROMPT 

MODEL_NAME = "gemini-3.5-flash"
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
EMAIL_SENDER = st.secrets["EMAIL_SENDER"]
EMAIL_APP_PASSWORD = st.secrets["EMAIL_APP_PASSWORD"]
EMAIL_SENDER_NAME = st.secrets["EMAIL_SENDER_NAME"]

st.set_page_config(
    page_title="Snap & Study",
    page_icon="📚",
    layout="centered"
)

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)

gemini_client = get_gemini_client()


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role,kind,content):
    st.session_state.messages.append(
        {
            "role": role,
            "kind": kind,
            "content": content
        }
    )
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    try:
        response = (st.session_state.chat.send_message(parts))
        return response.text
    except Exception as error:
        return (
            "Sorry, something went wrong while "
            f"processing your request:\n\n{error}"
        )


def generate_complete_study_note():
    return ask_gemini([EMAIL_STUDY_NOTE_PROMPT])


def generate_email_subject(study_note):
    prompt = f"""{EMAIL_SUBJECT_PROMPT}
    Here is the study note:
    {study_note}"""
    return ask_gemini([prompt]).strip()


if "onboarded" not in st.session_state:
    st.title("📚 Snap & Study")
    st.caption("Snap it. Understand it. Learn it.")
    with st.form("onboarding_form"):
        name = st.text_input(
            "Your name",
            placeholder="Enter your name")
        email = st.text_input(
            "Your email address",
            placeholder="student@example.com",
            help=(
                "Your complete study explanations "
                "will be sent to this email."
            )
        )

        submitted = st.form_submit_button("Let's Learn 🚀")

    if submitted:
        if (not name.strip() or not email.strip()):
            st.warning(
                "Please fill in both your name "
                "and email address.")
        else:
            st.session_state.name = (
                name.strip()
            )
            st.session_state.student_email = (
                email.strip()
            )

            st.session_state.chat = (
                gemini_client.chats.create(
                    model=MODEL_NAME,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT
                    )
                )
            )
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()


header_col, button_col = st.columns([5, 2], vertical_alignment="center")
with header_col:
    st.title("📚 Snap & Study")

with button_col:
    send_disabled = (len(st.session_state.messages) <= 1)
    if st.button(
        "📧 Send Explanation",
        disabled=send_disabled,
        use_container_width=True):

        with st.spinner("🧠 Preparing your complete study note..."):
            study_note = (generate_complete_study_note())

        with st.spinner("📝 Preparing your email..."):
            email_subject = (generate_email_subject(study_note))

        with st.spinner("📧 Sending your study note..."):

            success, info = (
                send_study_email(
                    recipient_email=(
                        st.session_state.student_email
                    ),
                    subject=email_subject,
                    study_content=study_note,
                    sender_email=EMAIL_SENDER,
                    sender_password=EMAIL_APP_PASSWORD,
                    sender_name=EMAIL_SENDER_NAME,
                )
            )

        if success:
            st.success(
                "✅ Complete study explanation "
                "sent to your email!")
        else:
            st.error(f"❌ Couldn't send the email: {info}")
st.caption(
    f"👤 {st.session_state.name}  •  "
    f"📧 {st.session_state.student_email}"
)
if not st.session_state.messages:
    add_message(
        "assistant",
        "text",
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.name
        )
    )

else:
    for message in (st.session_state.messages):
        render_message(message)

user_input = st.chat_input(
    "Ask a question or upload a study image 📸",
    accept_file=True,
    file_type=["jpg","jpeg","png"]
)

if user_input:
    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )
    text = user_input.text
    parts = []
    if photo is not None:
        photo_bytes = (photo.getvalue())
        add_message("user","image",photo_bytes)
        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type
            )
        )
    if text:
        add_message("user","text",text)
        parts.append(text)

    elif photo is not None:
        parts.append(
            """
            Analyze this image carefully.

            Identify the question, concept, diagram,
            notes, or study material shown.

            Explain it clearly and step-by-step
            in simple student-friendly language.

            Include the final answer when applicable.
            """
        )

    with st.spinner("🤖 Understanding your question..."):
        answer = ask_gemini(parts)

    add_message("assistant","text",answer)