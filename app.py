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

# ---------- SIMPLE IN-MEMORY STATE FOR MULTI-STEP FLOWS ----------
# Maps from_number -> {"flow": "accident", "step": 1 or 2, "answers": {...}}
conversation_state = {}

# ---------- PHRASE LISTS ----------

# 1) Therapy attendance risk (haven’t been going)
THERAPY_CONCERN_PHRASES = [
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
    "missed a few",
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
    "ran over",
    "run over",
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
    "uber accident",
    "lyft accident",
    "ride share accident",
    "rideshare accident",
    "electrical injuyr",
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

# 4) General legal questions about case timing / value / status
LEGAL_QUESTION_PHRASES = [
    "what happens when my case is over",
    "what happens when my case is finished",
    "what happens when my case is done",
    "what happens when my case ends",
    "what happens when the case is over",
    "when my case is over",
    "when my case is finished",
    "when my case is done",
    "is it too late to file",
    "too late to file a claim",
    "too late to file a lawsuit",
    "is it too late to sue",
    "do i still have time to file",
    "how much money can i get",
    "how much is my case worth",
    "how much is my claim worth",
    "how fast will i get paid",
    "how long will my case take",
    "how long does a case take",
    "how long does a claim take",
    "what happens when my case is resolved",
]

def contains_any(text, phrases):
    t = text.lower()
    return any(p in t for p in phrases)

# ---------- CLASSIFICATION ----------

def classify_message(text):
    """
    Returns one of:
      - 'therapy_concern'
      - 'therapy_positive'
      - 'accident_lead'
      - 'legal_question'
      - 'other'
    """
    if contains_any(text, THERAPY_CONCERN_PHRASES):
        return "therapy_concern"
    if contains_any(text, THERAPY_POSITIVE_PHRASES):
        return "therapy_positive"
    if contains_any(text, ACCIDENT_PHRASES):
        return "accident_lead"
    if contains_any(text, LEGAL_QUESTION_PHRASES):
        return "legal_question"
    return "other"

# ---------- WEBHOOK ----------

@app.route("/sms", methods=["POST"])
def sms_webhook():
    incoming_text = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "")

    resp = MessagingResponse()

    # Basic safety check
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_NUMBER and CALENDAR_URL):
        resp.message(
            "Our firm is temporarily unable to process messages. "
            "Please call our office directly."
        )
        return Response(str(resp), mimetype="application/xml")

    # ---- FIRST: HANDLE ANY IN-PROGRESS ACCIDENT FLOW ----
    state = conversation_state.get(from_number)
    if state and state.get("flow") == "accident":
        step = state.get("step")

        # STEP 1: answer to "Were you physically injured? YES/NO"
        if step == 1:
            answer = incoming_text.strip().lower()
            state["answers"]["injured"] = answer
            state["step"] = 2

            resp.message(
                "Thank you. Do you already have a lawyer for this incident? "
                "Please reply YES or NO."
            )
            return Response(str(resp), mimetype="application/xml")

        # STEP 2: answer to "Do you already have a lawyer? YES/NO"
        elif step == 2:
            answer = incoming_text.strip().lower()
            state["answers"]["has_lawyer"] = answer

            # Send alert to firm with full context
            if ALERT_NUMBER:
                answers = state["answers"]
                alert_msg = (
                    f"NEW ACCIDENT LEAD (follow-up): {from_number} said: \"{state.get('original_text','')}\". "
                    f"Injured: {answers.get('injured','')} | "
                    f"Has lawyer: {answers.get('has_lawyer','')}"
                )
                try:
                    client.messages.create(
                        body=alert_msg,
                        from_=TWILIO_NUMBER,
                        to=ALERT_NUMBER
                    )
                except Exception as e:
                    print("Alert error (accident follow-up):", e)

            # Clear state
            conversation_state.pop(from_number, None)

            # Send scheduling message
            resp.message(
                "Thank you for the information. Our firm will review this.\n"
                f"Please schedule a free consultation here: {CALENDAR_URL}"
            )
            return Response(str(resp), mimetype="application/xml")

    # ---- IF NOT IN AN ACTIVE FLOW, CLASSIFY FRESH MESSAGE ----
    msg_type = classify_message(incoming_text)

    # 1) THERAPY CONCERN: client hasn't been going
    if msg_type == "therapy_concern":
        if ALERT_NUMBER:
            alert_msg = (
                f"THERAPY ATTENDANCE CONCERN: {from_number} said: \"{incoming_text}\". "
                "Consider reaching out."
            )
            try:
                client.messages.create(
                    body=alert_msg,
                    from_=TWILIO_NUMBER,
                    to=ALERT_NUMBER
                )
            except Exception as e:
                print("Alert error (therapy_concern):", e)

        resp.message(
            "Thanks for checking in. Our team will be in touch shortly to make sure you have everything you need."
        )

    # 2) THERAPY POSITIVE: client is attending regularly
    elif msg_type == "therapy_positive":
        resp.message(
            "Great! Thank you for the update. Keep us posted on your progress. "
            f"If you need anything from us, please schedule a meeting using this link: {CALENDAR_URL}"
        )

    # 3) ACCIDENT / CATASTROPHIC INJURY LEAD
    elif msg_type == "accident_lead":
        # Start two-question flow
        conversation_state[from_number] = {
            "flow": "accident",
            "step": 1,
            "answers": {},
            "original_text": incoming_text,
        }

        # Optional: initial alert that an accident lead came in
        if ALERT_NUMBER:
            alert_msg = (
                f"NEW ACCIDENT LEAD (started): {from_number} said: \"{incoming_text}\". "
                "Bot is collecting quick follow-up answers."
            )
            try:
                client.messages.create(
                    body=alert_msg,
                    from_=TWILIO_NUMBER,
                    to=ALERT_NUMBER
                )
            except Exception as e:
                print("Alert error (accident_lead start):", e)

        resp.message(
            "I’m sorry to hear you were hurt. I’ll ask just 2 quick questions so our team can prepare before we talk.\n\n"
            "First: Were you physically injured? Please reply YES or NO."
        )

    # 4) GENERAL LEGAL QUESTIONS (like “What happens when my case is over?”)
    elif msg_type == "legal_question":
        resp.message(
            "That’s something your attorney can go over with you directly.\n"
            f"You can schedule a time that works for you here: {CALENDAR_URL}"
        )

    # 5) FALLBACK: anything else
    else:
        resp.message(
            "Thank you for reaching out. Our team is happy to talk through your situation.\n"
            f"You can schedule a time that works for you here: {CALENDAR_URL}"
        )

    return Response(str(resp), mimetype="application/xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
