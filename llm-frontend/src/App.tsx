import { useRef, useState, useEffect } from 'react';
import './App.css'

interface Message {
  role: 'user' | 'assistant';
  content: string;
}



function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const retryCountRef = useRef(0);


  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);
  

  // Auto-scroll to bottom when new messages arrive, here messageendref is an empty div that points to the end of message list
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);



  const MAX_RETRIES = 3;

  const openEventSource = (url: string) => {
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;
  
    eventSource.onmessage = (event) => {
      // Completion
      if (event.data === "[DONE]") {
        retryCountRef.current = 0;
        eventSource.close();
        setIsLoading(false);
        return;
      }
  
      // Backend error message
      if (event.data.startsWith("[ERROR]")) {
        eventSource.close();
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: 'Sorry, an error occurred. Please try again.'
          };
          return updated;
        });
        setIsLoading(false);
        retryCountRef.current = 0;
        return;
      }
  
      // ✅ Normal streaming token
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        updated[updated.length - 1] = {
          ...last,
          content: last.content + event.data
        };
        return updated;
      });
    };
  
    eventSource.onerror = () => {
      if (!isLoading) return;
  
      eventSource.close();
  
      if (retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current += 1;
        console.warn(`Retrying... (${retryCountRef.current})`);
  
        setTimeout(() => {
          openEventSource(url);
        }, 1000 * retryCountRef.current);
      } else {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: 'Connection failed after multiple attempts. Please try again.'
          };
          return updated;
        });
  
        setIsLoading(false);
        retryCountRef.current = 0;
      }
    };
  };
  


const startChat = () => {
  if (!prompt.trim() || isLoading) return;

  const userMessage: Message = { role: 'user', content: prompt };
  setMessages(prev => [...prev, userMessage]);
  setPrompt("");
  setIsLoading(true);

  retryCountRef.current = 0;

  if (eventSourceRef.current) {
    eventSourceRef.current.close();
  }

  setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

  const url = `http://localhost:8000/chat?prompt=${encodeURIComponent(userMessage.content)}`;
  openEventSource(url);
};


  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      startChat();
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>🤖 AI Chatbot</h1>
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <p>👋 Welcome! Start a conversation by typing a message below.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div 
              key={index} 
              className={`message ${message.role}`}
            >
              <div className="message-content">
                {message.content || (message.role === 'assistant' && isLoading ? (
                  <span className="typing-indicator">
                    <span></span><span></span><span></span>
                  </span>
                ) : '')}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="input-wrapper">
          <input
            ref={inputRef}
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={isLoading}
            className="chat-input"
          />
          <button 
            onClick={startChat}
            disabled={isLoading || !prompt.trim()}
            className="send-button"
          >
            {isLoading ? '⏳' : '➤'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default App