import {ConversationRequest} from "./models";

export async function conversationApi(options: ConversationRequest, abortSignal: AbortSignal): Promise<Response> {
    return await fetch("/api/conversation/azure_byod", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            messages: options.messages
        }),
        signal: abortSignal
    });
}


export async function customConversationApi(options: ConversationRequest, abortSignal: AbortSignal, employeeNumber: string | number | undefined): Promise<Response> {
    return await fetch(`/api/conversation/custom/${employeeNumber}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            messages: options.messages,
            conversation_id: options.id
        }),
        signal: abortSignal
    });
}
