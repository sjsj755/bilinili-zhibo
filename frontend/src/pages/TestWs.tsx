import { useEffect, useState } from 'react';

export function TestWs() {
  const [messages, setMessages] = useState<string[]>([]);
  const [status, setStatus] = useState('disconnected');

  useEffect(() => {
    const ws = new WebSocket('/ws');

    ws.onopen = () => {
      setStatus('connected');
      ws.send(JSON.stringify({ type: 'subscribe', roomId: 6136246 }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.log('TestWs received:', msg);
        setMessages((prev) => [...prev.slice(-20), JSON.stringify(msg)]);
      } catch (e) {
        console.error('Parse error:', e);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
    };

    ws.onerror = () => {
      setStatus('error');
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">WebSocket 测试</h1>
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
        status === 'connected' ? 'bg-green-100 text-green-700' :
        status === 'disconnected' ? 'bg-gray-100 text-gray-700' : 'bg-red-100 text-red-700'
      }`}>
        <div className={`w-2 h-2 rounded-full ${
          status === 'connected' ? 'bg-green-500' :
          status === 'disconnected' ? 'bg-gray-400' : 'bg-red-500'
        }`} />
        {status}
      </div>
      <div className="mt-4 bg-gray-100 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm">
        {messages.length === 0 ? (
          <p className="text-gray-500">等待消息...</p>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className="mb-2 text-gray-800">{msg}</div>
          ))
        )}
      </div>
    </div>
  );
}
