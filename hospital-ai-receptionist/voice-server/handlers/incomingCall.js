const axios = require("axios");
const { GatherSource } = require("@fonoster/voice");

const API = process.env.API_SERVER_URL || "http://localhost:8000";

/**
 * Posts JSON to the FastAPI backend and returns the parsed response.
 */
async function apiPost(path, data) {
  const res = await axios.post(`${API}${path}`, data, {
    timeout: 15_000,
    headers: { "Content-Type": "application/json" },
  });
  return res.data;
}

/**
 * Collects speech input from the caller using Fonoster's gather() verb.
 * Returns the transcribed text, or null on timeout / empty input.
 */
async function collectSpeech(voice, prompt, options = {}) {
  await voice.say(prompt);

  const result = await voice.gather({
    source: GatherSource.SPEECH,
    timeout: 10_000,
    maxSpeechDuration: 30_000,
    ...options,
  });

  return result?.speech || result?.digits || null;
}

/**
 * Gracefully ends the call with a friendly message when something goes wrong.
 */
async function errorAndHangup(voice, message) {
  const fallback =
    message ||
    "I'm sorry, we are experiencing technical difficulties. Please call back shortly.";
  try {
    await voice.say(fallback);
  } catch (_) {
    /* best-effort */
  }
  await voice.hangup();
}

/**
 * Main handler invoked by Fonoster for every incoming call.
 * Implements the full receptionist flow:
 *   answer → greet → identify patient → collect doctor/symptoms → book → confirm → hangup
 */
async function handleIncomingCall(req, voice) {
  const callId = req.sessionRef || "unknown";
  console.log(`[Call ${callId}] Incoming call received`);

  try {
    // ── Step 1: Answer the call ──────────────────────────────────────
    await voice.answer();
    console.log(`[Call ${callId}] Call answered`);

    // ── Step 2: Greet ────────────────────────────────────────────────
    await voice.say(
      "Welcome to City Hospital. I am Aria, your AI assistant. " +
        "I can help you book an appointment today."
    );

    // ── Step 3: Ask for patient name ─────────────────────────────────
    const patientName = await collectSpeech(
      voice,
      "May I have your full name, please?"
    );
    if (!patientName) {
      return await errorAndHangup(
        voice,
        "I wasn't able to hear your name. Please try calling again."
      );
    }
    console.log(`[Call ${callId}] Patient name: ${patientName}`);

    // ── Step 4: Look up or register patient ──────────────────────────
    let patient;
    try {
      const lookup = await apiPost("/conversation/lookup", {
        name: patientName,
        call_id: callId,
      });

      if (lookup.found) {
        patient = lookup;
        await voice.say(
          `Welcome back, ${patient.full_name}! ` +
            `I have your phone number as ${patient.phone} and email as ${patient.email}. ` +
            `Is that correct?`
        );

        const confirmation = await collectSpeech(
          voice,
          "Please say yes to confirm, or no to update your details."
        );

        if (confirmation && confirmation.toLowerCase().includes("no")) {
          const phone = await collectSpeech(
            voice,
            "Please say your updated phone number."
          );
          const email = await collectSpeech(
            voice,
            "And your updated email address?"
          );
          if (phone || email) {
            try {
              await apiPost("/conversation/update", {
                patient_id: patient.patient_id,
                phone: phone || patient.phone,
                email: email || patient.email,
              });
              await voice.say("Your details have been updated. Thank you!");
            } catch (err) {
              console.error(`[Call ${callId}] Update failed:`, err.message);
              await voice.say(
                "I couldn't update your details right now, but let's continue with the booking."
              );
            }
          }
        }
      } else {
        // New patient — register
        await voice.say(
          "It looks like this is your first visit. Let me get you registered."
        );

        const phone = await collectSpeech(
          voice,
          "What is your phone number?"
        );
        if (!phone) {
          return await errorAndHangup(
            voice,
            "I wasn't able to capture your phone number. Please call back and try again."
          );
        }

        const email = await collectSpeech(
          voice,
          "And what is your email address?"
        );
        if (!email) {
          return await errorAndHangup(
            voice,
            "I wasn't able to capture your email. Please call back and try again."
          );
        }

        const reg = await apiPost("/conversation/register", {
          full_name: patientName,
          phone,
          email,
        });

        if (!reg.success) {
          return await errorAndHangup(
            voice,
            "I'm sorry, I wasn't able to register you at this time. Please try again later."
          );
        }

        patient = {
          patient_id: reg.patient_id,
          full_name: patientName,
          phone,
          email,
        };
        await voice.say("You have been successfully registered. Thank you!");
      }
    } catch (err) {
      console.error(`[Call ${callId}] Lookup/register error:`, err.message);
      return await errorAndHangup(
        voice,
        "I'm sorry, our system is temporarily unavailable. Please call back in a few minutes."
      );
    }

    // ── Step 5: Ask for preferred doctor ─────────────────────────────
    const doctorName = await collectSpeech(
      voice,
      "Which doctor would you like to see? You may say a name or a specialty."
    );
    if (!doctorName) {
      return await errorAndHangup(
        voice,
        "I wasn't able to hear the doctor name. Please call back to try again."
      );
    }
    console.log(`[Call ${callId}] Doctor: ${doctorName}`);

    // ── Step 6: Ask for symptoms ─────────────────────────────────────
    const symptoms = await collectSpeech(
      voice,
      "Could you briefly describe your symptoms or the reason for your visit?"
    );
    if (!symptoms) {
      return await errorAndHangup(
        voice,
        "I wasn't able to hear your symptoms. Please call back and try again."
      );
    }
    console.log(`[Call ${callId}] Symptoms: ${symptoms}`);

    // Follow-up if symptoms are very short (likely unclear)
    let fullSymptoms = symptoms;
    if (symptoms.split(" ").length < 3) {
      const followUp = await collectSpeech(
        voice,
        "Could you tell me a bit more about what you're experiencing?"
      );
      if (followUp) {
        fullSymptoms = `${symptoms}. ${followUp}`;
      }
    }

    // ── Step 7: Ask for preferred date/time ──────────────────────────
    const dateTimeRaw = await collectSpeech(
      voice,
      "When would you like your appointment? Please say something like " +
        "tomorrow at 10 AM, or next Monday at 2 PM."
    );
    if (!dateTimeRaw) {
      return await errorAndHangup(
        voice,
        "I wasn't able to capture your preferred time. Please call back to try again."
      );
    }
    console.log(`[Call ${callId}] Requested datetime: ${dateTimeRaw}`);

    // ── Step 8: Book the appointment via FastAPI ─────────────────────
    let booking;
    try {
      booking = await apiPost("/conversation/book", {
        patient_id: patient.patient_id,
        patient_name: patient.full_name,
        doctor_name: doctorName,
        symptoms: fullSymptoms,
        appointment_datetime: dateTimeRaw,
      });

      if (!booking.success) {
        return await errorAndHangup(
          voice,
          "I'm sorry, I wasn't able to book your appointment. Please try again later."
        );
      }
    } catch (err) {
      console.error(`[Call ${callId}] Booking error:`, err.message);
      return await errorAndHangup(
        voice,
        "Our booking system is currently down. Please call back shortly."
      );
    }

    // ── Step 9: Confirm details back to patient ──────────────────────
    await voice.say(
      `Your appointment has been booked successfully. ` +
        `Here are your details: ` +
        `Doctor: ${doctorName}. ` +
        `Symptoms noted: ${fullSymptoms}. ` +
        `Appointment time: ${booking.appointment_datetime || dateTimeRaw}. ` +
        `Your appointment ID is ${booking.appointment_id}. ` +
        `You will receive a reminder call and email one hour before your appointment. ` +
        `Thank you for choosing City Hospital. Have a wonderful day!`
    );

    // ── Step 10: Hang up ─────────────────────────────────────────────
    await voice.hangup();
    console.log(`[Call ${callId}] Call completed successfully`);
  } catch (err) {
    console.error(`[Call ${callId}] Unhandled error:`, err);
    await errorAndHangup(voice);
  }
}

module.exports = handleIncomingCall;
