import React, { useMemo, useState } from "react";
import "./App.css";

type Role = "user" | "assistant";

type ChatMessage = {
  role: Role;
  content: string;
};

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:3000";

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Hi! Ask me anything." },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const canSend = useMemo(() => {
    return input.trim().length > 0 && !loading;
  }, [input, loading]);

  /* ---------------- Send Chat Message ---------------- */

  async function sendMessage() {
    const text = input.trim();

    if (!text || loading) return;

    setError("");

    const updatedMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: text },
    ];

    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          history: updatedMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data?.error || "Server error");
      }

      const reply =
        data.reply ||
        data.response ||
        data.answer ||
        data.message ||
        "(No reply)";

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply },
      ]);
    } catch (err: any) {
      console.error(err);

      setError(err.message || "Something went wrong");

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  /* ---------------- Upload PDF ---------------- */

  async function uploadPDF() {
    if (!file) {
      alert("Please select a PDF first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/upload-pdf`, {
        method: "POST",
        body: formData,
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data?.error || "Upload failed");
      }

      alert("✅ PDF uploaded successfully!");

      console.log(data);

      setFile(null);
    } catch (err) {
      console.error(err);
      alert("❌ Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      sendMessage();
    }
  }

  function clearChat() {
    setMessages([{ role: "assistant", content: "Hi! Ask me anything." }]);
    setInput("");
    setError("");
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo"></div>

          <div>
            <div className="title">ChatBot</div>
            <div className="subtitle">Cute, fast & helpful</div>
          </div>
        </div>

        <button className="ghostBtn" onClick={clearChat} disabled={loading}>
          Clear
        </button>
      </header>

      <div className="shell">
        <main className="chatArea">
          {messages.map((m, idx) => (
            <div key={idx} className={`row ${m.role}`}>
              <div className="avatar">
                {m.role === "assistant" ? "🤖" : "🧑"}
              </div>

              <div className={`bubble ${m.role}`}>
                <div className="bubbleText">{m.content}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="row assistant">
              <div className="avatar">🤖</div>

              <div className="bubble assistant">
                <div className="typing">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </main>

        <footer className="composer">
          {error && <div className="errorBanner">{error}</div>}

          {/* PDF Upload Section */}

          <div style={{ marginBottom: "10px" }}>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) =>
                setFile(e.target.files ? e.target.files[0] : null)
              }
            />

            <button
              onClick={uploadPDF}
              disabled={!file || uploading}
              style={{ marginLeft: "10px" }}
            >
              {uploading ? "Uploading..." : "Upload PDF"}
            </button>
          </div>

          {/* Chat Input */}

          <div className="composerRow">
            <input
              className="composerInput"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              disabled={loading}
            />

            <button
              className="sendBtn"
              onClick={sendMessage}
              disabled={!canSend}
            >
              Send ➤
            </button>
          </div>

          <div className="hint">
            Tip: Press <b>Enter</b> to send
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;