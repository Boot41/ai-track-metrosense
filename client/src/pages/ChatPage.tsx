import { useState } from "react";
import { Box, CircularProgress, Drawer } from "@mui/material";
import MessageList from "@/components/chat/MessageList";
import InputBar from "@/components/input/InputBar";
import ChatSidebar from "@/components/layout/ChatSidebar";
import Header from "@/components/layout/Header";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const {
    agentStatus,
    createNewChat,
    input,
    isHistoryLoading,
    isSending,
    loadHistorySession,
    messages,
    mode,
    prompts,
    selectedHistorySessionId,
    sessionId,
    sessions,
    setInput,
    sendMessage,
  } = useChat();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <Box sx={{ height: "100vh", display: "flex", overflow: "hidden" }}>
      <Box sx={{ display: { xs: "none", md: "flex" }, flexShrink: 0 }}>
        <ChatSidebar
          sessions={sessions}
          selectedSessionId={selectedHistorySessionId}
          onCreateNew={createNewChat}
          onSelectSession={(selected) => {
            void loadHistorySession(selected);
          }}
        />
      </Box>

      <Drawer
        open={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        sx={{ display: { xs: "block", md: "none" } }}
      >
        <ChatSidebar
          sessions={sessions}
          selectedSessionId={selectedHistorySessionId}
          onCreateNew={() => {
            createNewChat();
            setMobileSidebarOpen(false);
          }}
          onSelectSession={(selected) => {
            void loadHistorySession(selected);
            setMobileSidebarOpen(false);
          }}
        />
      </Drawer>

      <Box
        sx={{
          height: "100vh",
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          flex: 1,
          overflow: "hidden",
        }}
      >
        <Header
          agentStatus={agentStatus}
          sessionId={sessionId}
          onOpenSidebar={() => setMobileSidebarOpen(true)}
        />
        {isHistoryLoading ? (
          <Box sx={{ flex: 1, minHeight: 0, display: "grid", placeItems: "center" }}>
            <CircularProgress />
          </Box>
        ) : (
          <MessageList isSending={isSending} messages={messages} readOnlyMode={mode === "history_readonly"} />
        )}
        <InputBar
          input={input}
          isSending={isSending}
          readOnlyMode={mode === "history_readonly"}
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
    </Box>
  );
}
