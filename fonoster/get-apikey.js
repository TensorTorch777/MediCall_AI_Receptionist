const { Client, ApiKeys } = require("/home/tensortorch26/Desktop/Voice_hosp/hospital-ai-receptionist/voice-server/node_modules/@fonoster/sdk");

async function main() {
  try {
    const client = new Client({
      endpoint: "localhost:50051",
      insecure: true,
    });

    console.log("Logging in as admin...");
    const loginResp = await client.login("admin@fonoster.local", "changeme");
    console.log("Login response:", JSON.stringify(loginResp, null, 2));

    console.log("\nCreating API key...");
    const apiKeys = new ApiKeys(client);
    const key = await apiKeys.createApiKey({ role: "WORKSPACE_ADMIN" });
    console.log("\n=== YOUR FONOSTER API KEYS ===");
    console.log("ACCESS_KEY_ID=" + key.accessKeyId);
    console.log("ACCESS_KEY_SECRET=" + key.accessKeySecret);
    console.log("==============================");
  } catch (err) {
    console.error("Error:", err.message);
    
    // Try listing available methods
    try {
      const client = new Client({ endpoint: "localhost:50051", insecure: true });
      console.log("\nClient methods:", Object.getOwnPropertyNames(Object.getPrototypeOf(client)).filter(m => m !== 'constructor'));
    } catch (e) {
      console.error("SDK inspection failed:", e.message);
    }
  }
}

main();
