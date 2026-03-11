import { Box } from "@mui/material";
import MessageList from "@/components/chat/MessageList";
import InputBar from "@/components/input/InputBar";
import Header from "@/components/layout/Header";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { agentStatus, input, isSending, messages, prompts, sessionId, setInput, sendMessage } = useChat();

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header agentStatus={agentStatus} sessionId={sessionId} />
      <MessageList isSending={isSending} messages={messages} />
      <InputBar
        input={input}
        isSending={isSending}
        prompts={prompts}
        showPrompts={messages.length === 0}
        onChange={setInput}
        onSend={() => void sendMessage()}
        onSelectPrompt={(prompt) => {
          setInput(prompt);
          void sendMessage(prompt);
        }}
      />
    </Box>
  );
}
