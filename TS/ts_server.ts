import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

let client: Client | undefined = undefined
const baseUrl = new URL("http://localhost:6100/mcp");

type ContentText = { type: 'text'; text: string };
type ContentImage = { type: 'image'; data: string; mimeType: string };
type ContentOther = { type: string;[key: string]: any };

type ContentItem = ContentText | ContentImage | ContentOther;

type ResponseType = {
    content: ContentItem[];
    structuredContent?: { result: string } | Record<string, any>;
    isError: boolean;
};

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
    const rawPlan = await client.callTool({
        name: "plan_phase",
        arguments: { query: "Could you plan a cinema date for sunday afternoon I'm in california US and I want simple snacks to share?" }
    });

    const plan: ResponseType = {
        content: Array.isArray((rawPlan as any).content)
            ? (rawPlan as any).content as ContentItem[]
            : [],
        structuredContent: (rawPlan as any).structuredContent
            ? { result: ((rawPlan as any).structuredContent as any).result ?? "" }
            : undefined,
        isError: typeof (rawPlan as any).isError === "boolean"
            ? (rawPlan as any).isError
            : false
    };
    const plan_response = (plan.content[0] as ContentText).text

    try {    
        const rawResponse = await client.callTool({
            name: "execute_phase",
            arguments: {
                query: plan_response
            }
        })

        const response: ResponseType = {
            content: Array.isArray((rawResponse as any).content)
                ? (rawResponse as any).content as ContentItem[]
                : [],
            structuredContent: (rawResponse as any).structuredContent
                ? { result: ((rawResponse as any).structuredContent as any).result ?? "" }
                : undefined,
            isError: typeof (rawResponse as any).isError === "boolean"
                ? (rawResponse as any).isError
                : false
        };
        
        const execute_response = (response.structuredContent?.result)

        console.log(execute_response)
    } catch (error) {
        const execute_response = "There was an error in response, try again later"
    }
}
main()