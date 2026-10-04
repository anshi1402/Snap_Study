import time

import streamlit as st
from google import genai
from google.genai import types

from email_service import send_study_email
from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    EMAIL_STUDY_NOTE_PROMPT,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Snap & Study",
    page_icon="📚",
    layout="centered",
)


# ============================================================
# SECRETS
# ============================================================

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

EMAIL_SENDER = st.secrets["EMAIL_SENDER"]

EMAIL_APP_PASSWORD = st.secrets["EMAIL_APP_PASSWORD"]

EMAIL_SENDER_NAME = st.secrets["EMAIL_SENDER_NAME"]


# ============================================================
# GEMINI MODEL
# ============================================================

MODEL_NAME = "gemini-3.5-flash"


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_gemini_client():
    return genai.Client(
        api_key=GEMINI_API_KEY
    )


gemini_client = get_gemini_client()


# ============================================================
# MESSAGE RENDERING
# ============================================================

def render_message(message):
    with st.chat_message(message["role"]):

        if message["kind"] == "text":
            st.write(message["content"])

        elif message["kind"] == "image":
            st.image(message["content"])


# ============================================================
# ADD MESSAGE
# ============================================================

def add_message(role, kind, content):
    st.session_state.messages.append(
        {
            "role": role,
            "kind": kind,
            "content": content,
        }
    )

    render_message(
        st.session_state.messages[-1]
    )


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(parts, retries=3):
    last_error = None

    for attempt in range(retries):

        try:
            response = st.session_state.chat.send_message(
                parts
            )

            if response and response.text:
                return response.text

            raise Exception(
                "Gemini returned an empty response."
            )

        except Exception as error:

            last_error = error

            error_text = str(error)

            # Retry temporary Gemini service errors
            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            ):

                if attempt < retries - 1:

                    # Exponential backoff:
                    # 2 seconds, then 4 seconds
                    time.sleep(2 ** attempt)

                    continue

            break

    raise RuntimeError(
        f"Gemini request failed after "
        f"{retries} attempts: {last_error}"
    )


# ============================================================
# GENERATE COMPLETE STUDY NOTE
# ============================================================

def generate_complete_study_note():
    return ask_gemini(
        [EMAIL_STUDY_NOTE_PROMPT]
    )


# ============================================================
# ONBOARDING
# ============================================================

if "onboarded" not in st.session_state:

    st.title("📚 Snap & Study")

    st.caption(
        "Snap it. Understand it. Learn it."
    )

    with st.form("onboarding_form"):

        name = st.text_input(
            "Your name",
            placeholder="Enter your name",
        )

        email = st.text_input(
            "Your email address",
            placeholder="student@example.com",
            help=(
                "Your complete study explanations "
                "will be sent to this email."
            ),
        )

        submitted = st.form_submit_button(
            "Let's Learn 🚀"
        )

    if submitted:

        if (
            not name.strip()
            or not email.strip()
        ):

            st.warning(
                "Please fill in both your name "
                "and email address."
            )

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
                    ),
                )
            )

            st.session_state.messages = []

            st.session_state.onboarded = True

            st.rerun()

    # Stop ONLY during onboarding.
    # This is intentional.
    st.stop()


# ============================================================
# MAIN HEADER
# ============================================================

header_col, button_col = st.columns(
    [5, 2],
    vertical_alignment="center",
)


# ============================================================
# TITLE
# ============================================================

with header_col:

    st.title("📚 Snap & Study")


# ============================================================
# SEND EXPLANATION BUTTON
# ============================================================

with button_col:

    send_disabled = (
        len(st.session_state.messages) <= 1
    )

    if st.button(
        "📧 Send Explanation",
        disabled=send_disabled,
        use_container_width=True,
    ):

        # ----------------------------------------------------
        # GENERATE STUDY NOTE
        # ----------------------------------------------------

        try:

            with st.spinner(
                "🧠 Preparing your complete study note..."
            ):

                study_note = (
                    generate_complete_study_note()
                )

        except Exception as error:

            error_text = str(error)

            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            ):

                st.error(
                    "🤖 Gemini is temporarily "
                    "experiencing high demand. "
                    "Please wait a few seconds "
                    "and try again."
                )

            else:

                st.error(
                    "❌ Could not generate the "
                    f"study note: {error_text}"
                )

        else:

            # ------------------------------------------------
            # EMAIL SUBJECT
            # ------------------------------------------------

            email_subject = (
                "📚 Snap & Study - "
                f"Study Notes for "
                f"{st.session_state.name}"
            )

            # ------------------------------------------------
            # SEND EMAIL
            # ------------------------------------------------

            try:

                with st.spinner(
                    "📧 Sending your study note..."
                ):

                    success, info = (
                        send_study_email(
                            recipient_email=(
                                st.session_state
                                .student_email
                            ),
                            subject=email_subject,
                            study_content=study_note,
                            sender_email=EMAIL_SENDER,
                            sender_password=(
                                EMAIL_APP_PASSWORD
                            ),
                            sender_name=(
                                EMAIL_SENDER_NAME
                            ),
                        )
                    )

                # --------------------------------------------
                # EMAIL SUCCESS
                # --------------------------------------------

                if success:

                    st.success(
                        "✅ Complete study "
                        "explanation sent to "
                        "your email!"
                    )

                # --------------------------------------------
                # EMAIL FAILURE
                # --------------------------------------------

                else:

                    st.error(
                        "❌ Couldn't send the email: "
                        f"{info}"
                    )

            except Exception as error:

                st.error(
                    "❌ An unexpected error "
                    "occurred while sending "
                    f"the email: {error}"
                )


# ============================================================
# USER INFORMATION
# ============================================================

st.caption(
    f"👤 {st.session_state.name}  •  "
    f"📧 {st.session_state.student_email}"
)


# ============================================================
# WELCOME MESSAGE / CHAT HISTORY
# ============================================================

if not st.session_state.messages:

    add_message(
        "assistant",
        "text",
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.name
        ),
    )

else:

    for message in st.session_state.messages:

        render_message(message)


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Ask a question or upload a study image 📸",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png",
    ],
)


# ============================================================
# PROCESS USER INPUT
# ============================================================

if user_input:

    # --------------------------------------------------------
    # GET IMAGE
    # --------------------------------------------------------

    if user_input.files:

        photo = user_input.files[0]

    else:

        photo = None


    # --------------------------------------------------------
    # GET TEXT
    # --------------------------------------------------------

    text = user_input.text


    # --------------------------------------------------------
    # GEMINI PARTS
    # --------------------------------------------------------

    parts = []


    # --------------------------------------------------------
    # PROCESS IMAGE
    # --------------------------------------------------------

    if photo is not None:

        photo_bytes = photo.getvalue()

        # Display image in chat
        add_message(
            "user",
            "image",
            photo_bytes,
        )

        # Send image to Gemini
        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type,
            )
        )


    # --------------------------------------------------------
    # PROCESS TEXT
    # --------------------------------------------------------

    if text:

        add_message(
            "user",
            "text",
            text,
        )

        parts.append(text)


    # --------------------------------------------------------
    # IMAGE WITHOUT TEXT
    # --------------------------------------------------------

    elif photo is not None:

        parts.append(
            """
            Analyze this image carefully.

            Identify the question, concept, diagram,
            notes, textbook content, or study material
            shown in the image.

            Explain the content clearly and step-by-step
            using simple student-friendly language.

            Break difficult concepts into smaller parts.

            If there is a question, solve it and provide
            the final answer.

            If there is a diagram, explain every important
            component and how the components are related.

            If there are notes or textbook pages, explain
            all important points without leaving out
            important information.
            """
        )


    # --------------------------------------------------------
    # ASK GEMINI
    # --------------------------------------------------------

    if parts:

        try:

            with st.spinner(
                "🤖 Understanding your question..."
            ):

                answer = ask_gemini(parts)

            add_message(
                "assistant",
                "text",
                answer,
            )

        except Exception as error:

            error_text = str(error)

            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            ):

                st.error(
                    "🤖 Gemini is temporarily busy. "
                    "Please wait a few seconds and "
                    "try sending your question again."
                )

            else:

                st.error(
                    "❌ Something went wrong: "
                    f"{error_text}"
                )