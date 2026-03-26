require("dotenv").config();
const VoiceServer = require("@fonoster/voice").default;
const handleIncomingCall = require("./handlers/incomingCall");

const voiceServer = new VoiceServer();

voiceServer.listen(async (req, voice) => {
  console.log(`[VoiceServer] Incoming call — session=${req.sessionRef}`);
  console.log(`[VoiceServer] API backend at ${process.env.API_SERVER_URL}`);
  await handleIncomingCall(req, voice);
});
