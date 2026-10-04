import streamlit as st

from email_service import send_study_email


sender_email = st.secrets["EMAIL_SENDER"]
sender_password = st.secrets["EMAIL_APP_PASSWORD"]
sender_name = st.secrets["EMAIL_SENDER_NAME"]


st.title("📧 Snap & Study Email Test")

recipient = st.text_input(
    "Send test email to:"
)


if st.button("Send Test Email"):

    if not recipient:

        st.warning("Please enter an email address.")

    else:

        success, message = send_study_email(
            recipient_email=recipient,
            subject="📚 Snap & Study - Email Test",
            study_content="""
📚 Snap & Study

This is a test email.

If you received this message, the Snap & Study
email functionality is working correctly. ✅

Your AI-generated study explanations will
be sent using this email system.
            """,
            sender_email=sender_email,
            sender_password=sender_password,
            sender_name=sender_name,
        )

        if success:

            st.success(
                "✅ Test email sent successfully!"
            )

        else:

            st.error(
                f"❌ {message}"
            )