from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os

app = Flask(__name__)

# ---- CONFIG (environment variables in Render) ----
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")      # your Twilio bot number, e.g. +12169995553
ALERT_NUMBER = os.environ.get("ALERT_NUMBER")        # your cell / intake line for alerts
CALENDAR_URL = os.environ.get("CALENDAR_URL")        # scheduling link, e.g. https://calendly.com/caslo_consult

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------- PHRASE LISTS ----------

# 1) Therapy attendance risk (haven’t been going)
THERAPY_NEGATIVE_PHRASES = [
    "haven't been in a while",
    "havent been in a while",
    "haven't been going",
    "havent been going",
    "havent been", 
    "haven't been",
    "haven't gone",
    "havent gone",
    "stopped going",
    "stopped coming",
    "stopped going to therapy",
    "stopped going therapy",
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
    "don't have transportation",
    "dont have transportation", 
    "don't have a ride", 
    "dont have ride", 
    "need a ride", 
    "don't have a way there", 
    "dont have a way there",
    "can't take off work", 
    "cant take off work", 
    "don't want to go anymore", 
    "dont want to go anymore", 
    "can i stop going", 
    "can i stop coming", 
    "doctor has not called me",
    "chiropractor hasnt called me",
    "chiropractor hasn't called me",
    "waiting for someone to call me back",
    "no one called me", 
    "no one has called me", 
    "i don't like my doctor", 
    "i don't like my chiropractor", 
    "i don't like my therapist", 
    "its too far", 
    "it's too far", 
    "i'm finished", 
    "im finished",
    "my last appointment was today", 
    "i had my last appointment",
    "im dont with therapy", 
    "i'm done with therapy", 
    "im done", 
    "i'm done", 
    "been avoiding going to therapy",
    "haven't been able to make it to therapy",
    "havent been able to make it to therapy",
    "i haven't been there in a while",
    "i havent been there in a while",
]

# 2) Therapy positive – they ARE attending
THERAPY_POSITIVE_PHRASES = [
    "i've been going to therapy",
    "ive been going to therapy",
    "i have been going to therapy",
    "i'm going to therapy regularly",
    "im going to therapy regularly",
    "i go to therapy regularly",
    "i've been going regularly",
    "ive been going regularly",
    "been attending therapy",
    "i keep going to therapy",
    "i'm still going to therapy",
    "im still going to therapy",
    "still going to therapy",
    "i've been in therapy", 
    "ive been in therapy",
    "i am in therapy",
    "i'm in therapy",
    "im in therapy",
    "still going to therapy", 
    "i've been going",
    "ive been going", 
    "i'm going",
    "im going", 
    "been consistent with my therapy",
    "have not missed any sessions",
    "kept my appointmnets",
    "have on track with therapy",
    "been going to my appointments",
    "i've been in therapy consistently",
    "ive been in therapy consistently",
]

# 3) Accident / catastrophic injury / PI-type phrases
ACCIDENT_PHRASES = [
    "car accident",
    "auto accident",
    "motorcycle accident",
    "truck accident",
    "hurt in an accident",
    "injured in an accident",
    "slip and fall",
    "18 wheeler",
    "police involved shooting",
    "police chase accident",
    "slipped and fell",
    "trip and fall",
    "slip and fall"
    "hit and run",
    "pedestrian accident",
    "ran me over",
    "got rear ended",
    "rear-ended",
    "t-boned",
    "crash",
    "wreck",
    "burn injury",
    "burned",
    "t bone",
    "t-bone",
    "hurt at work",
    "rollover",
    "roll over",
    "ambulance",
    "broken bone",
    "construction accident",
    "on the job injury", 
    "object in food",
    "screw in food",
    "metal in food",
    "broken tooth",

 # catastrophic injuries
    "electrocuted",
    "electrocution",
    "burn injury",
    "burned",
    "serious burn",
    "spinal cord injury",
    "paralyzed",
    "paralysis",
    "amputation",
    "lost my leg",
    "lost my arm",
    "traumatic brain injury",
    "tbi",
    "catastrophic injury",
    "brain injury",
    "coma",
    "concussion",
    "broken bone", 
    "bone fracture",
    "wrongful death",
    "my loved one died",
    "family member died",
    "fatal accident",
    "death",
    "killed",
    "birth defect",
    "died",

    # dissatisfaction with current attorney / timing
    "my attorney hasn't done anything",
    "my lawyer hasn't done anything",
    "my attorney has not done anything",
    "my lawyer has not done anything",
    "can i change lawyers",
    "switch lawyers",
    "switch attorneys",
    "is it too late to sue",
    "is it too late to file",
    "too late to file a claim",
    "too late to file a lawsuit",
    "statute of limitations",
    "do i still have a case",

    # needing a lawyer / unsure
    "i need a lawyer",
    "i need an attorney",
    "do i need a lawyer",
    "do i need an attorney",
    "don't know if i need a lawyer",
    "dont know if i need a lawyer",
    "not sure if i need a lawyer",

      # money / insurance / payout questions
    "how much money can i get",
    "how much will i get",
    "what is my case worth",
    "how fast will i get paid",
    "how quickly will i get paid",
    "i don't have insurance",
    "i dont have insurance",
    "other driver didn't have insurance",
    "other driver didnt have insurance",
    "uninsured driver",
    "underinsured driver",
]

# --------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------

def text_matches_any(message_text: str, phrase_list) -> bool:
    text = message_text.lower().strip()
    return any(phrase in text for phrase in phrase_list)

# --------------------------------------------------------------------
# MAIN WEBHOOK
# --------------------------------------------------------------------

@app.route("/sms", methods=["POST"])
def sms_webhook():
    """Main Twilio webhook for incoming SMS."""
    incoming_text = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "")

    resp = MessagingResponse()

    # If critical config is missing, fail gracefully for the client.
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_NUMBER and CALENDAR_URL):
        resp.message(
            "Our firm is temporarily unable to process messages. "
            "Please call our office directly."
        )
        return Response(str(resp), mimetype="application/xml")

    # ----------------------------------------------------------------
    # 1) Therapy attendance risk (hasn't been going)
    # ----------------------------------------------------------------
    if text_matches_any(incoming_text, THERAPY_NEGATIVE_PHRASES):
        # Internal alert to you / your intake line
        if ALERT_NUMBER:
            alert_msg = (
                f"Therapy attendance alert:\n"
                f"From: {from_number}\n"
                f"Message: \"{incoming_text}\""
            )
            try:
                twilio_client.messages.create(
                    body=alert_msg,
                    from_=TWILIO_NUMBER,
                    to=ALERT_NUMBER
                )
            except Exception as e:
                print("Error sending therapy attendance alert:", e)
                  # Client-facing response
        resp.message(
            "Thanks for checking in. Our team will be in touch shortly to make sure you have everything you need."
        )
        return Response(str(resp), mimetype="application/xml")

    # ----------------------------------------------------------------
    # 2) Therapy positive / attending regularly
    # ----------------------------------------------------------------
    if text_matches_any(incoming_text, THERAPY_POSITIVE_PHRASES):
        resp.message(
            "Great! Thank you for the update. Keep us posted on your progress. "
            f"If you need anything from us, please schedule a meeting using this link: {CALENDAR_URL}"
        )
        return Response(str(resp), mimetype="application/xml")

    # ----------------------------------------------------------------
    # 3) Injury / accident / catastrophic injury / “need a lawyer”
    # ----------------------------------------------------------------
    if text_matches_any(incoming_text, INJURY_LEAD_PHRASES):
        # Internal alert for potential new case
        if ALERT_NUMBER:
            alert_msg = (
                "New potential injury lead:\n"
                f"From: {from_number}\n"
                f"Message: \"{incoming_text}\""
            )
            try:
                twilio_client.messages.create(
                    body=alert_msg,
                    from_=TWILIO_NUMBER,
                    to=ALERT_NUMBER
                )
            except Exception as e:
                print("Error sending injury lead alert:", e)

        # Client-facing response (as in your screenshot)
        resp.message(
            "Thank you for reaching out about your situation. Our firm may be able to help, "
            "and the best next step is to speak with an attorney directly.\n\n"
            f"Please use this link to schedule a consultation: {CALENDAR_URL}"
        )
        return Response(str(resp), mimetype="application/xml")

    # ----------------------------------------------------------------
    # 4) Default: everything else → generic attorney + calendar
    # ----------------------------------------------------------------
    resp.message(
        "That’s something your attorney can go over with you directly.\n"
        f"You can schedule a time that works for you here: {CALENDAR_URL}"
    )
    return Response(str(resp), mimetype="application/xml")


if __name__ == "__main__":
    # Local testing; in production Render runs this via gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=False)
                
