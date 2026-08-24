import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { MessageSquare, Send, Bot, User, AlertCircle } from 'lucide-react';
import { askQuestion } from '../services/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  evidence?: unknown[];
  reasoning?: string;
}

export default function InvestigationPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);

  const mutation = useMutation({
    mutationFn: (question: string) => askQuestion(question),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          confidence: data.confidence,
          evidence: data.evidence,
          reasoning: data.reasoning,
        },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your question.',
        },
      ]);
    },
  });

  const handleSend = () => {
    if (!input.trim() || mutation.isPending) return;

    const question = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    mutation.mutate(question);
  };

  const suggestions = [
    'What are the main components of this project?',
    'What dependencies does this project use?',
    'What are the security concerns?',
    'What is the testing infrastructure?',
    'How is the code organized?',
    'What are the entry points?',
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-indigo-400" />
          <h2 className="text-lg font-semibold text-white">AI Investigation</h2>
        </div>
        <p className="mt-1 text-sm text-gray-500">
          Ask questions about the analyzed repository. Answers use the knowledge
          graph and evidence system.
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center">
            <Bot className="h-16 w-16 text-gray-700" />
            <h3 className="mt-4 text-lg font-semibold text-gray-400">
              Ask Anything
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Ask questions about the codebase structure, dependencies, security,
              and architecture.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  className="btn-secondary text-xs"
                  onClick={() => {
                    setInput(s);
                    setMessages((prev) => [...prev, { role: 'user', content: s }]);
                    mutation.mutate(s);
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-6">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600/20">
                  <Bot className="h-4 w-4 text-indigo-400" />
                </div>
              )}
              <div
                className={`max-w-2xl rounded-xl p-4 ${
                  msg.role === 'user'
                    ? 'bg-indigo-600/20 text-indigo-100'
                    : 'card'
                }`}
              >
                <p className="text-sm">{msg.content}</p>

                {msg.confidence !== undefined && (
                  <div className="mt-3 flex items-center gap-2">
                    <span className="text-xs text-gray-500">Confidence:</span>
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-800">
                      <div
                        className={`h-full rounded-full ${
                          msg.confidence >= 0.7
                            ? 'bg-green-500'
                            : msg.confidence >= 0.4
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${msg.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">
                      {(msg.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

                {msg.reasoning && (
                  <p className="mt-2 text-xs text-gray-600 italic">
                    {msg.reasoning}
                  </p>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-700">
                  <User className="h-4 w-4 text-gray-300" />
                </div>
              )}
            </div>
          ))}

          {mutation.isPending && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600/20">
                <Bot className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="card">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.3s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.15s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 px-6 py-4">
        <div className="flex gap-3">
          <input
            type="text"
            className="input flex-1"
            placeholder="Ask a question about the repository..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button
            className="btn-primary flex items-center gap-2"
            onClick={handleSend}
            disabled={!input.trim() || mutation.isPending}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 flex items-center gap-1 text-xs text-gray-600">
          <AlertCircle className="h-3 w-3" />
          Answers are generated by AI analysis. Verify critical conclusions with
          source code.
        </div>
      </div>
    </div>
  );
}
