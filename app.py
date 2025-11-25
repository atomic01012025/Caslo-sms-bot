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
CALENDAR_URL = os.environ.get("CALENDAR_URL")        # scheduling link, e.g. https://calendly.com/caslo_consult

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# phrases that indicate "I haven’t been in a while" / not attending therapy regularly
NEGATIVE_ATTENDANCE_PHRASES = [
    "haven't been in a while",
    "havent been in a while",
    "haven't been going",
    "havent been going",
    "haven't gone",
    "havent gone",
    "stopped going to therapy",
    "stopped going therapy",
    "stopped going",
    "stopped coming",
    "haven't had a session",
    "havent had a session",
    "missed my last few",
    "missed my last couple",
    "missed my last",
    "missed",
    "cancel",
    "cancelled",
    "reschedule",
    "rescheduled",
    "need to reschedule",
    "need to set",
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
    "don't have transportation",
    "dont have transportation",
    "don't have a ride",
    "dont have a ride",
    "need a ride", 
    "don't have a way there", 
    "dont have a way there",
    "cant take off work",
    "can't take off work",
    "chiropractor hasnt called me back",
    "chiropractor hasn't called me back",
    "waiting for someone to call me back",
    "no one called me",
    "i haven't been there in a while",
    "i havent been there in a while",
]

# phrases that indicate ongoing / regular therapy attendance
POSITIVE_THERAPY_PHRASES = [
    "i've been going to therapy regularly",
    "ive been going to therapy regularly",
    "i have been going to therapy regularly",
    "i've been going regularly",
    "ive been going regularly",
    "i go to therapy every week",
    "i go to therapy each week",
    "i've been in therapy",
    "ive been in therapy",
    "i am in therapy",
    "i'm in therapy",
    "im in therapy",
    "still going to therapy",
    "still in therapy",
    "i've been going",
    "i'm going",
    "im going",
    "i'm going",
    "i've been keeping up with therapy",
]

def is_negative_attendance(text: str) -> bool:
    text = text.lower().strip()
    return any(phrase in text for phrase in NEGATIVE_ATTENDANCE_PHRASES)

def is_positive_therapy(text: str) -> bool:
    text = text.lower().strip()
    return any(phrase in text for phrase in POSITIVE_THERAPY_PHRASES)

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

    # 1️⃣ Negative attendance: "haven't been in a while" etc. → alert + follow-up message
    if is_negative_attendance(incoming_text):
        alert_msg = (
            f"Attendance alert: client {from_number} texted: \"{incoming_text}\". "
            "Suggested follow-up about therapy attendance."
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

        resp.message(
            "Thanks for checking in. Our team will be in touch shortly to make sure you have everything you need."
        )

    # 2️⃣ Positive therapy updates: "I've been going regularly" etc. → encouragement + Calendly link
    elif is_positive_therapy(incoming_text):
        resp.message(
            "Great! Thank you for the update. Keep us posted on your progress. "
            f"If you need anything from us, please schedule a meeting using the link: {CALENDAR_URL}"
        )

    # 3️⃣ Everything else → generic Calendly routing (no attorney-language for now)
    else:
        resp.message(
            "Thanks for reaching out. If you need anything from us, please schedule a meeting using the link: "
            f"{CALENDAR_URL}"
        )

    return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
  
   
