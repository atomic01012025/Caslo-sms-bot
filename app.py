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
CALENDAR_URL = os.environ.get("CALENDAR_URL")        # scheduling link (Calendly, etc.)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# 1️⃣ Phrases that suggest they are NOT attending therapy (our original “red flags”)
NEGATIVE_THERAPY_PHRASES = [
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
    "reschedule",
    "rescheduled",
    "need to reschedule",
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
    "need a ride",
    "don't have a way there",
    "dont have a way there",
    "can't take off work",
    "cant take off work",
    "i haven't been there in a while",
    "i havent been there in a while",
]

# 2️⃣ Phrases that suggest they ARE attending therapy
POSITIVE_THERAPY_PHRASES = [
    "i've been going to therapy",
    "ive been going to therapy",
    "i have been going to therapy",
    "i've been in therapy",
    "ive been in therapy",
    "i have been in therapy",
    "i'm going to therapy",
    "im going to therapy",
    "i am going to therapy",
    "i've been attending therapy",
    "ive been attending therapy",
    "still going to therapy",
    "still in therapy",
    "i go to therapy regularly",
    "i've been making my therapy appointments",
    "ive been making my therapy appointments",
]

# 3️⃣ Phrases indicating catastrophic / serious injuries (15 including electrocution)
CATASTROPHIC_INJURY_PHRASES = [
    "catastrophic injury",
    "catastrophic injuries",
    "electrocution",
    "electrocuted",
    "severe burn",
    "third degree burn",
    "third-degree burn",
    "spinal cord injury",
    "spinal cord damage",
    "paralyzed",
    "paralysis",
    "traumatic brain injury",
    "tbi",
    "brain injury",
    "amputation",
    "lost my leg",
    "lost my arm",
    "lost a limb",
]

def text_matches_any(text: str, phrases: list[str]) -> bool:
    t = text.lower().strip()
    return any(phrase in t for phrase in phrases)

def is_negative_therapy(text: str) -> bool:
    return text_matches_any(text, NEGATIVE_THERAPY_PHRASES)

def is_positive_therapy(text: str) -> bool:
    return text_matches_any(text, POSITIVE_THERAPY_PHRASES)

def is_catastrophic_injury(text: str) -> bool:
    return text_matches_any(text, CATASTROPHIC_INJURY_PHRASES)

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

    # 1️⃣ They are NOT attending therapy → alert + follow-up message
    if is_negative_therapy(incoming_text):
        alert_msg = (
            f"Therapy attendance alert: client {from_number} texted: \"{incoming_text}\". "
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

        resp.message(
            "Thanks for checking in. Our team will be in touch shortly to make sure you have everything you need."
        )

    # 2️⃣ They ARE attending therapy → send your “Great! Thank you…” message
    elif is_positive_therapy(incoming_text):
        resp.message(
            "Great! Thank you for the update. Keep us posted on your progress. "
            f"If you need anything from us, please schedule a meeting using the link: {CALENDAR_URL}"
        )

    # 3️⃣ Catastrophic / serious injury keywords → light PI routing for now
    elif is_catastrophic_injury(incoming_text):
        # Optional: also alert the firm about this lead
        if ALERT_NUMBER:
            lead_alert = (
                f"Catastrophic injury lead: client {from_number} texted: \"{incoming_text}\"."
            )
            try:
                client.messages.create(
                    body=lead_alert,
                    from_=TWILIO_NUMBER,
                    to=ALERT_NUMBER
                )
            except Exception as e:
                print("Lead alert error:", e)

        resp.message(
            "Thank you for reaching out about your injuries. Our firm may be able to help. "
            f"The fastest way to get started is to schedule a consultation here: {CALENDAR_URL}"
        )

    # 4️⃣ Everything else → generic route to calendar (safe default for now)
    else:
        resp.message(
            "That’s something your attorney can go over with you directly.\n"
            f"You can schedule a time that works for you here: {CALENDAR_URL}"
        )

    return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
   
