/** @odoo-module **/
/**
 * SubscriptIQ AI Finance Copilot Client Component
 * Handles user query submissions, tool action previews, and dual authorization prompts.
 */

export class SubscriptIQCopilotClient {
    constructor(rpc) {
        this.rpc = rpc;
    }

    async ask(query) {
        if (!query || !query.trim()) {
            return { error: "Query cannot be empty." };
        }

        try {
            const response = await this.rpc("/subscriptiq/copilot/ask", { query: query.trim() });
            return response;
        } catch (error) {
            console.error("SubscriptIQ Copilot RPC Error:", error);
            return {
                answer: "[SubscriptIQ: AI network timeout or connectivity error. Falling back to local deterministic rules.]",
                error: error.message
            };
        }
    }
}
