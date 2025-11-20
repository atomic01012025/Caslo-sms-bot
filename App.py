from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os

app = Flask(__name__)

# ---- CONFIG (use environment variables when deployed) ----
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")      # your Twilio bot number, e.g. +12169995553
ALERT_NUMBER = os.environ.get("ALERT_NUMBER")        # your cell / intake line for alerts
CALENDAR_URL = os.environ.get("CALENDAR_URL")        # scheduling link

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# phrases that indicate "I haven’t been in a while" around therapy
ATTENDANCE_PHRASES = [
    "haven't been in a while",
    "havent been in a while",
    "haven't been going",
    "havent been going",
    "haven't gone",
    "havent gone",
    "havent been",
    "haven't been",
    "stopped going",
    "stopped coming",
    "haven't had a session",
    "havent had a session",
    "missed my last few",
    "missed my last couple",
    "missed",
    "cancel",
    "cancelled",
    "haven't been to therapy",
    "havent been to therapy",
    "haven't seen my therapist",
    "havent seen my therapist",
    "took a break from therapy",
    "haven't scheduled therapy",
    "havent scheduled therapy",
    "haven't booked therapy",
    "havent booked therapy",
    "been avoiding going to therapy",
    "haven't been able to make it to therapy",
    "havent been able to make it to therapy",
    "dont have transportation",
    "don't have transportation",
    "don't have a ride",
    "dont have a ride",
    "cant take off work",
    "can't take off work",
    "don't have a way there",
    "dont have a way there",
    "i haven't been there in a while",
    "i havent been there in a while",
]

def is_attendance_flag(text: str) -> bool:
    text = text.lower().strip()
    return any(phrase in text for phrase in ATTENDANCE_PHRASES)

@app.route("/sms", methods=["POST"])
def sms_webhook():
    incoming_text = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "")

    resp = MessagingResponse()

    # Safety check: if core config is missing, be honest
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_NUMBER and CALENDAR_URL):
        resp.message(
            "Our firm is temporarily unable to process messages. "
            "Please call our office directly."
        )
        return Response(str(resp), mimetype="application/xml")

    if is_attendance_flag(incoming_text):
        # send YOU an alert
        alert_msg = (
            f"Attendance alert: client {from_number} texted: \"{incoming_text}\". "
            "Suggested follow-up."
        )
        if ALERT_NUMBER:
            try:
                client.messages.create(
                    body=alert_msg,
                    from_=TWILIO_NUMBER,
                    to=ALERT_NUMBER
                )
            except Exception as e:
                print("Alert error:", e)

        # reply to the client with your chosen CASLO message
        resp.message(
            "Thanks for checking in. Our team will be in touch shortly "
            "to make sure you have everything you need."
        )
    else:
        # default: route everything else to the calendar
        resp.message(
            "That’s something your attorney can go over with you directly.\n"
            f"You can schedule a time that works for you here: {CALENDAR_URL}"
        )

    return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
