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
    "slipped and fell",
    "trip and fall",
    "hit and run",
    "pedestrian accident",
    "ran me over",
    "got rear ended",
    "rear-ended",
    "t-boned",
    "crash",
    "wreck",
    "electrocuted",
    "electrocution",
    "burn injury",
    "burned",
    "catastrophic injury",
    "brain injury",
    "spinal cord injury",
    "paralyzed",
    "paralysis",
    "wrongful death",
    "killed",
    "died from",
    "no insurance",
    "don't have insurance",
    "dont have insurance",
    "my attorney hasn’t done anything",
    "my attorney hasn't done anything",
    "my lawyer hasn’t done anything",
    "my lawyer hasn't done anything",
    "need a lawyer",
    "need an attorney",
    "do i need a lawyer",
    "do i need an attorney",
    "how much money can i get",
    "how much is my case worth",
    "is it too late to file",
    "is it too late to sue",
]

def contains_any(text: str, phrases) -> bool:
    t = text.lower().strip()
    return any(p in t for p in phrases)

# ---------- MAIN WEBHOOK ----------

@app.route("/sms", methods=["POST"])
def sms_webhook():
    incoming_text = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "")

    resp = MessagingResponse()

    # Safety check: config present?
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_NUMBER and CALENDAR_URL):
        resp.message(
            "Our firm is temporarily unable to process messages. "
            "Please call our office directly."
        )
        return Response(str(resp), mimetype="application/xml")

    # ----- Branch 1: Therapy – attendance risk (haven’t been going) -----
    if contains_any(incoming_text, THERAPY_NEGATIVE_PHRASES):
        # Alert you / your team
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

        # Client response
        resp.message(
            "Thanks for checking in. Our team will be in touch shortly to make sure you have everything you need."
        )

    # ----- Branch 2: Therapy – positive attendance (they ARE going) -----
    elif contains_any(incoming_text, THERAPY_POSITIVE_PHRASES):
        resp.message(
            "Great! Thank you for the update. Keep us posted on your progress. "
            f"If you need anything from us, please schedule a meeting using the link: {CALENDAR_URL}"
        )

    # ----- Branch 3: Accident / catastrophic injury / PI lead -----
    elif contains_any(incoming_text, ACCIDENT_PHRASES):
        resp.message(
            "Thank you for reaching out about your situation. Our firm may be able to help, "
            "and the best next step is to speak with an attorney directly.\n\n"
            f"Please use this link to schedule a consultation: {CALENDAR_URL}"
        )

    # ----- Branch 4: Everything else → general legal question routing -----
    else:
        resp.message(
            "That’s something your attorney can go over with you directly.\n"
            f"You can schedule a time that works for you here: {CALENDAR_URL}"
        )

    return Response(str(resp), mimetype="application/xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
  
