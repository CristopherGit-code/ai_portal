import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { Protocol } from "@modelcontextprotocol/sdk/shared/protocol.js";

let client: Client | undefined = undefined
const baseUrl = new URL("http://localhost:6100/mcp");

async function main() {
    try {
        client = new Client({
            name: 'streamable-http-client',
            version: '1.0.0',
        });
        const transport = new StreamableHTTPClientTransport(
            new URL(baseUrl)
        );
        await client.connect(transport);
        console.log("Connected using Streamable HTTP transport");
    } catch (error) {
        // If that fails with a 4xx error, try the older SSE transport
        console.log("Streamable HTTP connection failed, falling back to SSE transport");
        client = new Client({
            name: 'sse-client',
            version: '1.0.0'
        });
        const sseTransport = new SSEClientTransport(baseUrl);
        await client.connect(sseTransport);
        console.log("Connected using SSE transport");
    }
    // SEPARATE THE GRPAH CALL
    const response = await client.callTool({
        name:"main_chain",
        arguments:{
            query:"Could you plan a cinema date for sunday?"
        }
    })
    console.log(response)
}
main()